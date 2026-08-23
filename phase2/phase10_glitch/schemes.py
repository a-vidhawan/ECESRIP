#!/usr/bin/env python3
"""
Top-level wrappers for the three ways of committing a neuron's output.

All three drive the SAME network and the SAME colouring. They differ only in what
sits between the combinational output s_next[i] and the state bit it feeds back
into, which is exactly where a glitch either does or does not get captured.

  transport  s_settle[i] <= #(d_i) s_next[i]
             What the current design does. A non-blocking assignment with an
             intra-assignment delay is TRANSPORT delay: every event on s_next is
             queued and delivered d_i later, including a 2 ns spike. The delay
             orders the commits but filters nothing, so a glitch that appears at
             the SOP output is faithfully latched into the state.

  inertial   assign #(tau) s_flt[i] = s_next[i];  assign #(d_i) s_del[i] = ...
             A continuous assignment with a delay is INERTIAL: a pulse narrower
             than the delay is cancelled before it ever propagates. Physically
             this is a slow buffer -- a gate whose output cannot slew fast
             enough to reproduce a narrow spike. One wire per neuron.

  ncl        dual-rail datapath, Muller C-element completion detection,
             NULL/DATA handshake, one colour class committed per handshake.
             Nothing is filtered because nothing glitches: the datapath is
             monotone, so no internal node ever falls during an evaluation.
"""


def emit_transport(N, delays, path, lut="lut_sr"):
    L = [f"""`timescale 1ns/1ps
module hopfield_top (input wire init_en, input wire [{N-1}:0] init_val,
                     output wire [{N-1}:0] s, output wire stable);
  logic [{N-1}:0] s_settle; initial s_settle = '0;
  wire  [{N-1}:0] s_next;
  assign s = init_en ? init_val : s_settle;
  {lut} lut (.s(s), .s_next(s_next));
  assign stable = (s === s_next);
  always @(s_next or init_en or init_val) begin
    if (init_en) s_settle <= #0 init_val;
    else begin"""]
    L += [f"      s_settle[{i}] <= #({d}) s_next[{i}];" for i, d in enumerate(delays)]
    L += ["    end", "  end", "endmodule"]
    open(path, "w").write("\n".join(L))


def emit_inertial(N, delays, tau, path, lut="lut_sr"):
    """Glitch filter of width tau, then the scheduling delay -- both inertial.

    Note there is no state element at all now: the feedback path is a pure
    delay line, which is what the circuit physically is. The commit ordering
    comes from the delay values exactly as before.
    """
    L = [f"""`timescale 1ns/1ps
module hopfield_top (input wire init_en, input wire [{N-1}:0] init_val,
                     output wire [{N-1}:0] s, output wire stable);
  wire [{N-1}:0] s_next, s_flt, s_del;
  {lut} lut (.s(s), .s_next(s_next));
  assign s = init_en ? init_val : s_del;
  assign stable = (s === s_next);
  // Hold the delay line AT init_val while init_en is high. Without this the
  // loop free-runs during the reset drain and the network has already taken a
  // full parallel update by the time the vector is released -- which is both
  // wrong and a different scheme from the one being compared against.
  wire [{N-1}:0] d_in = init_en ? init_val : s_next;"""]
    # tau first: reject anything narrower than the filter, THEN schedule.
    # Splitting the two makes the pulse-rejection width an independent knob
    # rather than an accident of which colour a neuron happens to be in.
    for i, d in enumerate(delays):
        L.append(f"  assign #({tau}) s_flt[{i}] = d_in[{i}];")
        L.append(f"  assign #({d}) s_del[{i}] = s_flt[{i}];")
    L.append("endmodule")
    open(path, "w").write("\n".join(L))


def emit_ncl(N, classes, path, commit_delay=2, colour=True):
    """Dual-rail NCL with a four-phase NULL/DATA handshake.

    The state is captured while the wavefront is DATA but only written back
    during NULL. That ordering is not cosmetic: the rails are driven from the
    state, so writing the state mid-DATA makes a rail fall, which breaks the
    monotonicity the whole scheme rests on and reintroduces exactly the glitches
    it exists to prevent. Getting this wrong is silent -- the circuit still
    settles, it just settles somewhere else.

    `colour=False` commits every neuron on each handshake instead of one colour
    class at a time. That variant exists to answer a specific question: does
    delay-insensitive logic make the colouring unnecessary? It should not --
    C-elements stop a node from acting on unstable INPUTS, and say nothing about
    two coupled nodes acting on the same stale state -- and running it is
    cheaper than arguing about it.
    """
    groups = [sorted(sum(classes, []))] if not colour else classes
    body = []
    for c, idx in enumerate(groups):
        body.append(f"          {c}: begin")
        body += [f"            s_settle[{i}] <= cap[{i}];" for i in idx]
        body.append("          end")
    L = [f"""`timescale 1ns/1ps
module hopfield_top (input wire init_en, input wire [{N-1}:0] init_val,
                     output wire [{N-1}:0] s, output wire stable);
  localparam int NG = {len(groups)};
  logic [{N-1}:0] s_settle; initial s_settle = '0;
  logic [{N-1}:0] cap;      initial cap = '0;
  logic data_en;  initial data_en  = 1'b0;
  logic stable_r; initial stable_r = 1'b0;
  wire  [{N-1}:0] f_t, f_f;
  wire  complete;
  assign s = init_en ? init_val : s_settle;
  // the NCL register: DATA presents the state on the rails, NULL clears both.
  // Clearing both is what makes the next evaluation monotone.
  wire [{N-1}:0] r_t = data_en ?  s : '0;
  wire [{N-1}:0] r_f = data_en ? ~s : '0;
  lut_dr lut (.r_t(r_t), .r_f(r_f), .f_t(f_t), .f_f(f_f), .complete(complete));
  assign stable = stable_r;

  logic [{N-1}:0] prev;
  integer cc;
  always @(posedge init_en) begin
    disable RUN;
    data_en = 1'b0; stable_r = 1'b0; s_settle = init_val;
  end
  always @(negedge init_en) begin : RUN
    stable_r = 1'b0;
    forever begin
      prev = s_settle;
      for (cc = 0; cc < NG; cc = cc + 1) begin
        data_en = 1'b1;
        @(posedge complete);        // completion detection, not a timer
        cap = f_t;                  // snapshot while the wavefront is valid
        data_en = 1'b0;
        @(negedge complete);        // wait for NULL to drain everywhere
        #({commit_delay});
        case (cc)"""]
    L += body
    L += [f"""          default: ;
        endcase
        #({commit_delay});
      end
      if (prev === s_settle) stable_r = 1'b1;
    end
  end
endmodule"""]
    open(path, "w").write("\n".join(L))

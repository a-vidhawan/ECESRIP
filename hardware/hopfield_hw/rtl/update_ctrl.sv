// =============================================================================
// update_ctrl.sv
// =============================================================================
// Control FSM for the Hopfield network update engine.
//
// Supports two modes selected by i_mode:
//   SYNC  (0) — all neurons updated in one clock cycle (synchronous rule)
//   ASYNC (1) — one neuron updated per cycle, round-robin order
//
// State machine
// -------------
//
//   IDLE ──(i_start)──► COMPUTE ──(done)──► CHECK_FP ──(fixed point)──► DONE
//                            ▲                  │ (not FP, < max_iter)
//                            └──────────────────┘
//
// Fixed-point detection
// ---------------------
// In SYNC mode: after each full update, compare new state with old state.
// If equal, assert o_fixed_point and go to DONE.
//
// In ASYNC mode: after a full round-robin pass (N neuron updates), compare
// the state before and after the pass.  If unchanged, fixed point reached.
//
// Hazard notes
// ------------
// All control signals are registered.  The combinational neuron-logic block
// (from sv_export.py) feeds into the neuron_bank register, so its glitches
// are masked by the clock edge.  This is the primary hazard-mitigation
// strategy for the datapath.
//
// Additionally, the neuron logic itself is generated with a hazard-free SOP
// cover (see logic_minimize.py / hazard_analysis.md) as a belt-and-suspenders
// measure for any path where the output is used asynchronously.
//
// Ports
// -----
//   clk           : system clock
//   rst_n         : async active-low reset
//   i_start       : pulse to begin convergence from current state
//   i_mode        : 0 = SYNC, 1 = ASYNC (round-robin)
//   i_max_iter    : maximum number of update rounds before declaring non-convergence
//   o_load        : connect to neuron_bank.i_load
//   o_fixed_point : asserted when network reached a fixed point
//   o_done        : asserted for one cycle when operation complete
//   o_iter_count  : number of update rounds executed
//   o_async_idx   : (ASYNC mode) index of the neuron being updated this cycle
//   o_async_mask  : one-hot mask for o_async_idx (used to mux d_next)
// =============================================================================

`timescale 1ns/1ps

module update_ctrl
#(
    parameter int N         = 8,
    parameter int MAX_ITER  = 1000
)
(
    input  logic                        clk,
    input  logic                        rst_n,

    // Control interface
    input  logic                        i_start,
    input  logic                        i_mode,         // 0=SYNC 1=ASYNC
    input  logic [$clog2(MAX_ITER)-1:0] i_max_iter,

    // State interface (read back from neuron_bank)
    input  logic [N-1:0]                i_state_cur,    // current registered state
    input  logic [N-1:0]                i_state_next,   // combinational next state

    // Outputs
    output logic                        o_load,
    output logic                        o_fixed_point,
    output logic                        o_done,
    output logic [$clog2(MAX_ITER)-1:0] o_iter_count,
    output logic [$clog2(N)-1:0]        o_async_idx,
    output logic [N-1:0]                o_async_mask
);

    // -------------------------------------------------------------------------
    // State encoding
    // -------------------------------------------------------------------------
    typedef enum logic [2:0] {
        S_IDLE    = 3'd0,
        S_COMPUTE = 3'd1,   // one round of updates
        S_CHECK   = 3'd2,   // compare old vs new state
        S_DONE    = 3'd3
    } state_t;

    state_t state_r, state_next;

    // -------------------------------------------------------------------------
    // Registers
    // -------------------------------------------------------------------------
    logic [$clog2(MAX_ITER)-1:0] iter_r;
    logic [$clog2(N)-1:0]        async_idx_r;
    logic [N-1:0]                 snapshot_r;   // state at start of round (FP check)

    // -------------------------------------------------------------------------
    // Next-state logic (combinational)
    // -------------------------------------------------------------------------
    always_comb begin
        state_next = state_r;
        case (state_r)
            S_IDLE:
                if (i_start) state_next = S_COMPUTE;
            S_COMPUTE: begin
                if (!i_mode) begin
                    // SYNC: one cycle per full update
                    state_next = S_CHECK;
                end else begin
                    // ASYNC: N cycles per round (one neuron per cycle)
                    if (async_idx_r == N[$clog2(N)-1:0] - 1'b1)
                        state_next = S_CHECK;
                end
            end
            S_CHECK: begin
                if (i_state_cur == snapshot_r || iter_r >= i_max_iter)
                    state_next = S_DONE;
                else
                    state_next = S_COMPUTE;
            end
            S_DONE:
                state_next = S_IDLE;
            default:
                state_next = S_IDLE;
        endcase
    end

    // -------------------------------------------------------------------------
    // Sequential state register
    // -------------------------------------------------------------------------
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state_r     <= S_IDLE;
            iter_r      <= '0;
            async_idx_r <= '0;
            snapshot_r  <= '0;
        end else begin
            state_r <= state_next;

            case (state_r)
                S_IDLE: begin
                    iter_r      <= '0;
                    async_idx_r <= '0;
                    if (i_start)
                        snapshot_r <= i_state_cur;  // capture starting state
                end

                S_COMPUTE: begin
                    if (i_mode) begin
                        // Advance round-robin index
                        if (async_idx_r == N[$clog2(N)-1:0] - 1'b1)
                            async_idx_r <= '0;
                        else
                            async_idx_r <= async_idx_r + 1'b1;
                    end
                end

                S_CHECK: begin
                    iter_r     <= iter_r + 1'b1;
                    snapshot_r <= i_state_cur;   // snapshot for next round
                end

                default: ; // nothing
            endcase
        end
    end

    // -------------------------------------------------------------------------
    // Output logic (registered to avoid glitches on control signals)
    // -------------------------------------------------------------------------
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            o_load        <= 1'b0;
            o_fixed_point <= 1'b0;
            o_done        <= 1'b0;
            o_iter_count  <= '0;
            o_async_idx   <= '0;
            o_async_mask  <= '0;
        end else begin
            // Defaults
            o_load        <= 1'b0;
            o_done        <= 1'b0;

            case (state_r)
                S_COMPUTE: begin
                    if (!i_mode) begin
                        // SYNC: assert load for one cycle
                        o_load       <= 1'b1;
                        o_async_mask <= {N{1'b1}};  // all neurons
                    end else begin
                        // ASYNC: load only the selected neuron's bit
                        o_load       <= 1'b1;
                        o_async_idx  <= async_idx_r;
                        o_async_mask <= N'(1) << async_idx_r;
                    end
                end

                S_CHECK: begin
                    o_fixed_point <= (i_state_cur == snapshot_r);
                    o_iter_count  <= iter_r;
                end

                S_DONE: begin
                    o_done <= 1'b1;
                end

                default: ;
            endcase
        end
    end

endmodule

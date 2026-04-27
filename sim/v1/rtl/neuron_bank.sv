// =============================================================================
// neuron_bank.sv
// =============================================================================
// Neuron state register bank.
//
// Stores the N-bit binary state word.
//   bit[j] = 1  ↔  neuron j is in the +1 (active) bipolar state
//   bit[j] = 0  ↔  neuron j is in the -1 (inactive) bipolar state
//
// On a LOAD strobe the bank captures the next-state word computed by the
// combinational neuron-logic modules.  The current state is always available
// on q_state.
//
// Synchronous design — all outputs registered on the rising clock edge.
// No combinational paths between inputs and outputs (no hazards possible).
//
// Ports
// -----
//   clk        : system clock (rising-edge active)
//   rst_n      : synchronous active-low reset → all neurons → 1 (active)
//   i_load     : load strobe: capture d_next on next rising edge
//   d_next     : next state word produced by neuron update logic
//   q_state    : current state word (registered)
// =============================================================================

`timescale 1ns/1ps

module neuron_bank
#(
    parameter int N = 8   ///< Number of neurons
)
(
    input  logic          clk,
    input  logic          rst_n,
    input  logic          i_load,
    input  logic [N-1:0]  d_next,
    output logic [N-1:0]  q_state
);

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            // Reset to all-ones (all neurons active — common Hopfield convention)
            q_state <= {N{1'b1}};
        end else if (i_load) begin
            q_state <= d_next;
        end
        // else: hold current state
    end

endmodule

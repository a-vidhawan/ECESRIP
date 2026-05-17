// =============================================================================
// weight_rom.sv
// =============================================================================
// Parameterized, read-only weight storage for the Hopfield network.
//
// The weight matrix W is (N × N) with zero diagonal, symmetric.
// Each off-diagonal entry W[i][j] is a signed integer of WIDTH bits.
//
// Weights are stored in a flattened array: index = i*N + j.
//
// Initialization
// --------------
// The ROM contents are loaded from a text file at simulation time using
// $readmemh (hex) or $readmemb (binary), selected by the INIT_FILE parameter.
// For synthesis the file is embedded via a Vivado IP core or
// the init_file attribute (Quartus / Vivado both support this flow).
//
// Ports
// -----
//   clk       : system clock
//   i_row     : row index of the weight to read (neuron index i, 0..N-1)
//   i_col     : column index (neuron index j, 0..N-1)
//   o_weight  : signed weight W[i][j], available one cycle after valid request
//   i_valid   : input valid strobe
//   o_valid   : output valid (registered, one cycle latency)
//
// Hazard notes
// ------------
// This is a synchronous read-only memory — no combinational paths from
// address to data, so no static or dynamic hazards arise here.
// All outputs are registered.
// =============================================================================

`timescale 1ns/1ps

module weight_rom
#(
    parameter int          N         = 8,    ///< Number of neurons
    parameter int          WIDTH     = 16,   ///< Bits per weight (signed)
    parameter string       INIT_FILE = ""    ///< Path to hex init file (optional)
)
(
    input  logic                         clk,
    input  logic                         rst_n,
    input  logic [$clog2(N)-1:0]        i_row,
    input  logic [$clog2(N)-1:0]        i_col,
    input  logic                         i_valid,
    output logic signed [WIDTH-1:0]     o_weight,
    output logic                         o_valid
);

    // -------------------------------------------------------------------------
    // Internal ROM array: N*N entries of WIDTH bits
    // Diagonal entries are always 0 by convention; they can be stored as 0
    // or masked at read time.
    // -------------------------------------------------------------------------
    localparam int DEPTH = N * N;

    logic signed [WIDTH-1:0] mem [0:DEPTH-1];

    // -------------------------------------------------------------------------
    // Initialisation
    // -------------------------------------------------------------------------
    initial begin
        // Zero all entries first (handles diagonal + uninitialized slots)
        for (int k = 0; k < DEPTH; k++) mem[k] = '0;

        // Load from file if provided
        if (INIT_FILE != "") begin
            $readmemh(INIT_FILE, mem);
        end
    end

    // -------------------------------------------------------------------------
    // Synchronous read with one-cycle latency
    // -------------------------------------------------------------------------
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            o_weight <= '0;
            o_valid  <= 1'b0;
        end else begin
            o_valid <= i_valid;
            if (i_valid) begin
                // Enforce zero diagonal
                if (i_row == i_col)
                    o_weight <= '0;
                else
                    o_weight <= mem[i_row * N + i_col];
            end
        end
    end

endmodule

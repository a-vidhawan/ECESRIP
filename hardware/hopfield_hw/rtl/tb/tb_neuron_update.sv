// =============================================================================
// tb_neuron_update.sv
// =============================================================================
// Unit testbench for the generated neuron_logic_bank module.
//
// Strategy
// --------
// This testbench is INDEPENDENT of the Python pipeline output.  It uses a
// reference model (threshold comparator in SV) to check the generated logic:
//
//   For every input vector b_in ∈ {0,1}^N:
//     expected[i] = (Σ_j W[i][j]*(2*b_in[j]-1) >= 0) ? 1 : 0
//     actual[i]   = neuron_logic_bank.b_out[i]
//
// Parameters
// ----------
//   N         — neurons (must match generated file)
//   W_WIDTH   — bits per weight
//   INIT_FILE — hex weight file (same as used during Python pipeline)
//
// HOW TO RUN
// ----------
// After running `python pipeline.py --N 8 ...`:
//
//   ModelSim:
//     vlog -sv hopfield_top.sv neuron_bank.sv update_ctrl.sv weight_rom.sv \
//              ../build_8/rtl/neuron_logic_generated.sv \
//              tb_neuron_update.sv
//     vsim -do "vsim work.tb_neuron_update; run -all"
//
//   Verilator (with generated file):
//     verilator --binary --trace -sv \
//       ../build_8/rtl/neuron_logic_generated.sv \
//       tb_neuron_update.sv
// =============================================================================

`timescale 1ns/1ps

module tb_neuron_update;

    // -------------------------------------------------------------------------
    // Parameters — change to match your pipeline run
    // -------------------------------------------------------------------------
    localparam int    N         = 8;
    localparam int    W_WIDTH   = 16;
    localparam string INIT_FILE = "";   // set if cross-checking against ROM

    // -------------------------------------------------------------------------
    // DUT: generated neuron_logic_bank
    // (Comment this out if neuron_logic_generated.sv has not been generated yet)
    // -------------------------------------------------------------------------
    logic [N-1:0] b_in;
    logic [N-1:0] b_out_dut;

    neuron_logic_bank #(.N(N)) dut (
        .b_in  (b_in),
        .b_out (b_out_dut)
    );

    // -------------------------------------------------------------------------
    // Reference model: signed accumulator
    // -------------------------------------------------------------------------
    logic signed [W_WIDTH + $clog2(N):0] h [0:N-1];
    logic [N-1:0] b_out_ref;

    // Weight registers (loaded by testbench)
    logic signed [W_WIDTH-1:0] W_ref [0:N-1][0:N-1];

    always_comb begin
        for (int i = 0; i < N; i++) begin
            h[i] = '0;
            for (int j = 0; j < N; j++) begin
                if (i != j)
                    h[i] = h[i] + W_ref[i][j] * (2 * $signed({1'b0, b_in[j]}) - 1);
            end
            b_out_ref[i] = (h[i] >= 0) ? 1'b1 : 1'b0;
        end
    end

    // -------------------------------------------------------------------------
    // Test: exhaustive enumeration
    // -------------------------------------------------------------------------
    int pass_cnt, fail_cnt;

    initial begin
        pass_cnt = 0; fail_cnt = 0;
        $display("=== Neuron Update Unit Test  N=%0d ===", N);

        // Load a simple weight matrix: W[i][j] = 1 for i≠j (scale implicit)
        for (int ii = 0; ii < N; ii++)
            for (int jj = 0; jj < N; jj++)
                W_ref[ii][jj] = (ii != jj) ? W_WIDTH'(1) : '0;

        // Also force the same weights into DUT's W_reg if using Option A top
        // (skip if using generated logic)

        $display("Running exhaustive check over all 2^%0d = %0d input vectors …",
                 N, 1 << N);

        for (int m = 0; m < (1 << N); m++) begin
            b_in = N'(m);
            #1;   // allow combinational settling

            if (b_out_dut !== b_out_ref) begin
                $error("MISMATCH at b_in=%0b: dut=%0b ref=%0b",
                       b_in, b_out_dut, b_out_ref);
                fail_cnt++;
            end else begin
                pass_cnt++;
            end
        end

        $display("Results: %0d PASS  %0d FAIL", pass_cnt, fail_cnt);
        if (fail_cnt == 0)
            $display("=== All %0d input combinations VERIFIED ===", 1 << N);
        else
            $display("=== FAILURES DETECTED — check generated logic ===");

        $finish;
    end

endmodule

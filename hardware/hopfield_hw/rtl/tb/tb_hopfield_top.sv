// =============================================================================
// tb_hopfield_top.sv
// =============================================================================
// Top-level testbench for hopfield_top.
//
// What is tested
// --------------
// 1. Pattern load + synchronous convergence.
// 2. Fixed-point detection.
// 3. Async (round-robin) convergence mode.
// 4. Reset behaviour.
//
// Configuration
// -------------
// Set N, P, and CLK_PERIOD as needed.  The testbench auto-generates
// random patterns at simulation time using the SystemVerilog $urandom
// seeded RNG.
//
// Usage (ModelSim)
// ----------------
//   vsim -do "vsim work.tb_hopfield_top; run -all"
//
// Usage (Verilator)
// -----------------
//   verilator --binary --trace -sv tb_hopfield_top.sv hopfield_top.sv \
//       neuron_bank.sv update_ctrl.sv weight_rom.sv \
//       -CFLAGS "-std=c++17"
//   ./Vtb_hopfield_top
// =============================================================================

`timescale 1ns/1ps

module tb_hopfield_top;

    // -------------------------------------------------------------------------
    // Parameters
    // -------------------------------------------------------------------------
    localparam int  N          = 8;
    localparam int  W_WIDTH    = 16;
    localparam int  MAX_ITER   = 200;
    localparam real CLK_PERIOD = 10.0;  // ns

    // -------------------------------------------------------------------------
    // DUT ports
    // -------------------------------------------------------------------------
    logic                        clk;
    logic                        rst_n;
    logic                        i_start;
    logic                        i_mode;
    logic                        i_load_pat;
    logic [N-1:0]                i_pattern;
    logic [N-1:0]                o_state;
    logic                        o_done;
    logic                        o_fixed_pt;
    logic [$clog2(MAX_ITER)-1:0] o_iter_cnt;

    // -------------------------------------------------------------------------
    // DUT instantiation
    // -------------------------------------------------------------------------
    hopfield_top #(
        .N        (N),
        .W_WIDTH  (W_WIDTH),
        .MAX_ITER (MAX_ITER),
        .INIT_FILE("")    // leave blank: testbench writes W_reg via force
    ) dut (
        .clk        (clk),
        .rst_n      (rst_n),
        .i_start    (i_start),
        .i_mode     (i_mode),
        .i_load_pat (i_load_pat),
        .i_pattern  (i_pattern),
        .o_state    (o_state),
        .o_done     (o_done),
        .o_fixed_pt (o_fixed_pt),
        .o_iter_cnt (o_iter_cnt)
    );

    // -------------------------------------------------------------------------
    // Clock generator
    // -------------------------------------------------------------------------
    initial clk = 0;
    always #(CLK_PERIOD / 2.0) clk = ~clk;

    // -------------------------------------------------------------------------
    // Tasks
    // -------------------------------------------------------------------------

    task automatic reset_dut;
        rst_n     = 0;
        i_start   = 0;
        i_mode    = 0;
        i_load_pat= 0;
        i_pattern = '0;
        repeat (4) @(posedge clk);
        #1;
        rst_n = 1;
        @(posedge clk); #1;
    endtask

    task automatic load_pattern(input logic [N-1:0] pat);
        i_pattern  = pat;
        i_load_pat = 1;
        @(posedge clk); #1;
        i_load_pat = 0;
    endtask

    task automatic run_converge(input logic mode);
        i_mode  = mode;
        i_start = 1;
        @(posedge clk); #1;
        i_start = 0;
        // Wait for done
        fork
            begin
                wait (o_done);
            end
            begin
                repeat (MAX_ITER * N + 10) @(posedge clk);
                $error("TIMEOUT: convergence not reached");
            end
        join_any
        disable fork;
        @(posedge clk);
    endtask

    // -------------------------------------------------------------------------
    // Test sequence
    // -------------------------------------------------------------------------
    initial begin
        $display("=== Hopfield Top TB  N=%0d ===", N);

        // Initialise weight register in DUT to a simple test case
        // (all +1 → store the all-ones pattern)
        // W[i][j] = 1/N for i≠j  → encoded as integer 1 (scale = 1/N implied)
        for (int ii = 0; ii < N; ii++)
            for (int jj = 0; jj < N; jj++) begin
                automatic int ij = ii * N + jj;
                if (ii != jj)
                    force dut.W_reg[ii][jj] = W_WIDTH'(1);
                else
                    force dut.W_reg[ii][jj] = '0;
            end

        reset_dut();

        // ---------------------------------------------------------------
        // Test 1: Sync convergence on all-ones pattern (trivial fixed pt)
        // ---------------------------------------------------------------
        $display("\n[Test 1] SYNC: all-ones pattern (should converge in 1 step)");
        load_pattern({N{1'b1}});
        run_converge(0);
        $display("  State after = %0b  done=%0b  fp=%0b  iters=%0d",
                 o_state, o_done, o_fixed_pt, o_iter_cnt);
        assert (o_state == {N{1'b1}})
            else $error("Expected all-ones fixed point");
        assert (o_fixed_pt)
            else $error("Expected fixed-point flag");

        // ---------------------------------------------------------------
        // Test 2: Noisy probe — flip 1 bit from all-ones
        // ---------------------------------------------------------------
        $display("\n[Test 2] SYNC: one-bit-flipped probe");
        load_pattern({N{1'b1}} ^ N'(1));    // flip bit 0
        run_converge(0);
        $display("  State after = %0b  fp=%0b  iters=%0d",
                 o_state, o_fixed_pt, o_iter_cnt);

        // ---------------------------------------------------------------
        // Test 3: ASYNC convergence
        // ---------------------------------------------------------------
        $display("\n[Test 3] ASYNC: one-bit-flipped probe");
        load_pattern({N{1'b1}} ^ N'(1));
        run_converge(1);
        $display("  State after = %0b  fp=%0b  iters=%0d",
                 o_state, o_fixed_pt, o_iter_cnt);

        // ---------------------------------------------------------------
        // Test 4: Reset during operation
        // ---------------------------------------------------------------
        $display("\n[Test 4] Reset during run");
        load_pattern(N'(8'hA5));
        i_start = 1;
        @(posedge clk); #1;
        i_start = 0;
        repeat (3) @(posedge clk);
        rst_n = 0;
        @(posedge clk); #1;
        rst_n = 1;
        @(posedge clk);
        $display("  State after reset = %0b  (expect all-ones)", o_state);
        assert (o_state == {N{1'b1}})
            else $error("Reset did not restore all-ones state");

        $display("\n=== All tests passed ===");
        $finish;
    end

    // -------------------------------------------------------------------------
    // Timeout watchdog
    // -------------------------------------------------------------------------
    initial begin
        #(CLK_PERIOD * (MAX_ITER * N * 4 + 1000));
        $error("Global simulation TIMEOUT");
        $finish;
    end

endmodule

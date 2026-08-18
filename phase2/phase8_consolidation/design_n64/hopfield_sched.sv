// Graph-coloured clockless schedule
`timescale 1ns/1ps
module hopfield_clockless #(parameter int N = 64) (
    input  wire          init_en,
    input  wire [N-1:0]  init_val,
    output wire [N-1:0]  s,
    output wire [N-1:0]  s_next,
    output wire          stable
);
    logic [N-1:0] s_settle;
    initial s_settle = '0;
    assign s = init_en ? init_val : s_settle;
    hopfield_lut #(.N(N)) lut (.s(s), .s_next(s_next));
    assign stable = (&(s|~s)) & (&(s_next|~s_next)) & (s === s_next);

    always @(init_en or init_val) begin
        if (init_en) s_settle <= #0 init_val;
    end

    always @(s_next or init_en or init_val) begin
        if (init_en) begin
            s_settle <= #0 init_val;
        end else begin
            s_settle[0] <= #(1) s_next[0];
            s_settle[1] <= #(1) s_next[1];
            s_settle[2] <= #(1) s_next[2];
            s_settle[3] <= #(1) s_next[3];
            s_settle[4] <= #(1) s_next[4];
            s_settle[5] <= #(1) s_next[5];
            s_settle[6] <= #(1) s_next[6];
            s_settle[7] <= #(1) s_next[7];
            s_settle[8] <= #(1) s_next[8];
            s_settle[9] <= #(1) s_next[9];
            s_settle[10] <= #(1) s_next[10];
            s_settle[11] <= #(1) s_next[11];
            s_settle[12] <= #(1) s_next[12];
            s_settle[13] <= #(1) s_next[13];
            s_settle[14] <= #(1) s_next[14];
            s_settle[15] <= #(1) s_next[15];
            s_settle[16] <= #(1) s_next[16];
            s_settle[17] <= #(1) s_next[17];
            s_settle[18] <= #(1) s_next[18];
            s_settle[19] <= #(1) s_next[19];
            s_settle[20] <= #(1) s_next[20];
            s_settle[21] <= #(1) s_next[21];
            s_settle[22] <= #(1) s_next[22];
            s_settle[23] <= #(1) s_next[23];
            s_settle[24] <= #(1) s_next[24];
            s_settle[25] <= #(1) s_next[25];
            s_settle[26] <= #(2) s_next[26];
            s_settle[27] <= #(5) s_next[27];
            s_settle[28] <= #(1) s_next[28];
            s_settle[29] <= #(5) s_next[29];
            s_settle[30] <= #(4) s_next[30];
            s_settle[31] <= #(2) s_next[31];
            s_settle[32] <= #(2) s_next[32];
            s_settle[33] <= #(4) s_next[33];
            s_settle[34] <= #(3) s_next[34];
            s_settle[35] <= #(3) s_next[35];
            s_settle[36] <= #(4) s_next[36];
            s_settle[37] <= #(4) s_next[37];
            s_settle[38] <= #(3) s_next[38];
            s_settle[39] <= #(3) s_next[39];
            s_settle[40] <= #(3) s_next[40];
            s_settle[41] <= #(3) s_next[41];
            s_settle[42] <= #(2) s_next[42];
            s_settle[43] <= #(3) s_next[43];
            s_settle[44] <= #(2) s_next[44];
            s_settle[45] <= #(3) s_next[45];
            s_settle[46] <= #(2) s_next[46];
            s_settle[47] <= #(4) s_next[47];
            s_settle[48] <= #(2) s_next[48];
            s_settle[49] <= #(2) s_next[49];
            s_settle[50] <= #(3) s_next[50];
            s_settle[51] <= #(2) s_next[51];
            s_settle[52] <= #(2) s_next[52];
            s_settle[53] <= #(3) s_next[53];
            s_settle[54] <= #(3) s_next[54];
            s_settle[55] <= #(2) s_next[55];
            s_settle[56] <= #(3) s_next[56];
            s_settle[57] <= #(4) s_next[57];
            s_settle[58] <= #(2) s_next[58];
            s_settle[59] <= #(2) s_next[59];
            s_settle[60] <= #(4) s_next[60];
            s_settle[61] <= #(5) s_next[61];
            s_settle[62] <= #(2) s_next[62];
            s_settle[63] <= #(3) s_next[63];
        end
    end
endmodule
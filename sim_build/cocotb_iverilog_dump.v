module cocotb_iverilog_dump();
initial begin
    $dumpfile("/Users/hank/Documents/School/6.s965/lab08/sim_build/top.fst");
    $dumpvars(0, top);
end
endmodule

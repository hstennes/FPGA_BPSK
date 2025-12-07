`timescale 1ns/1ps
module costas_wrapper #
(
    parameter integer C_S00_AXIS_TDATA_WIDTH    = 32,
    parameter integer C_M00_AXIS_TDATA_WIDTH    = 32
)
(
    // Ports of Axi Slave Bus Interface S00_AXIS
    input   wire                          s00_axis_aclk,
    input   wire                          s00_axis_aresetn,
    input   wire                          s00_axis_tlast,
    input   wire                          s00_axis_tvalid,
    input   wire [C_S00_AXIS_TDATA_WIDTH-1 : 0] s00_axis_tdata,
    input   wire [(C_S00_AXIS_TDATA_WIDTH/8)-1: 0] s00_axis_tstrb,
    output  wire                          s00_axis_tready,

    // Ports of Axi Master Bus Interface M00_AXIS
    input   wire                          m00_axis_aclk,
    input   wire                          m00_axis_aresetn,
    input   wire                          m00_axis_tready,
    output  wire                          m00_axis_tvalid,
    output  wire                          m00_axis_tlast,
    output  wire [C_M00_AXIS_TDATA_WIDTH-1 : 0] m00_axis_tdata,
    output  wire [(C_M00_AXIS_TDATA_WIDTH/8)-1: 0] m00_axis_tstrb
);

    // Instantiate SystemVerilog module
    costas #(
        .C_S00_AXIS_TDATA_WIDTH(C_S00_AXIS_TDATA_WIDTH),
        .C_M00_AXIS_TDATA_WIDTH(C_M00_AXIS_TDATA_WIDTH)
    ) costas_inst (
        .s00_axis_aclk(s00_axis_aclk),
        .s00_axis_aresetn(s00_axis_aresetn),
        .s00_axis_tlast(s00_axis_tlast),
        .s00_axis_tvalid(s00_axis_tvalid),
        .s00_axis_tdata(s00_axis_tdata),
        .s00_axis_tstrb(s00_axis_tstrb),
        .s00_axis_tready(s00_axis_tready),

        .m00_axis_aclk(m00_axis_aclk),
        .m00_axis_aresetn(m00_axis_aresetn),
        .m00_axis_tready(m00_axis_tready),
        .m00_axis_tvalid(m00_axis_tvalid),
        .m00_axis_tlast(m00_axis_tlast),
        .m00_axis_tdata(m00_axis_tdata),
        .m00_axis_tstrb(m00_axis_tstrb)
    );

endmodule
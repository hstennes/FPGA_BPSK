`default_nettype none
`timescale 1 ns / 1 ps

module bpsk_decoder_debug #
	(
        parameter integer SQUITTER_LENGTH = 128,
		parameter integer C_S00_AXIS_TDATA_WIDTH	= 32,
		parameter integer C_M00_AXIS_TDATA_WIDTH	= SQUITTER_LENGTH,
        parameter integer C_M01_AXIS_TDATA_WIDTH = 32,
        parameter integer NUM_COEFFS_LOWPASS = 75,
        parameter integer NUM_COEFFS_PREAMBLE_DETECTOR = 512
	)
	(

		// Ports of Axi Slave Bus Interface S00_AXIS
        // Streams in I/Q data (I and Q are each 16 bit signed, packed into 32 bit stream).
		input wire  s00_axis_aclk, s00_axis_aresetn,
		input wire  s00_axis_tlast, s00_axis_tvalid,
		input wire [C_S00_AXIS_TDATA_WIDTH-1 : 0] s00_axis_tdata,
		input wire [(C_S00_AXIS_TDATA_WIDTH/8)-1: 0] s00_axis_tstrb,
		output logic  s00_axis_tready,

		// Ports of Axi Master Bus Interface M00_AXIS
        // Outputs 112-bit ADS-B squitters. Ignores downstream ready signal
        // because the next thing is a FIFO that should always be ready (also
        // we don't care about losing a squitter occasionally).
		input wire  m00_axis_aclk, m00_axis_aresetn,
		input wire  m00_axis_tready,
		output logic  m00_axis_tvalid, m00_axis_tlast,
		output logic [C_M00_AXIS_TDATA_WIDTH-1 : 0] m00_axis_tdata,
		output logic [(C_M00_AXIS_TDATA_WIDTH/8)-1: 0] m00_axis_tstrb,

        input wire  m01_axis_aclk, m01_axis_aresetn,
		input wire  m01_axis_tready,
		output logic  m01_axis_tvalid, m01_axis_tlast,
		output logic [C_M01_AXIS_TDATA_WIDTH-1 : 0] m01_axis_tdata,
		output logic [(C_M01_AXIS_TDATA_WIDTH/8)-1: 0] m01_axis_tstrb,

        // FIR coefficients for the matched filter that detects the preamble.
        input wire signed [NUM_COEFFS_PREAMBLE_DETECTOR-1:0][7:0] preamble_coeffs,
        // FIR coefficients for the lowpass filter that is applied to the ADC data.
        input wire signed [NUM_COEFFS_LOWPASS-1:0][7:0] lowpass_coeffs,
        // Threshold used to decide whether a local maximum of the matched filter output is large enough to trigger the decoder state machine.
        input wire [C_S00_AXIS_TDATA_WIDTH-1:0] preamble_detector_threshold,
        // Threshold used to decide whether magnitude is a zero bit or a one bit.
        input wire [C_S00_AXIS_TDATA_WIDTH-1:0] decoder_threshold,
        // Thresholded magnitude data for debugging the decoder with the ILA.
        output wire thresholded_data_debug
	);

    logic signed [15:0] adc_data_real;
    assign adc_data_real = s00_axis_tdata[15:0];

    logic matched_filter_tready;
    logic matched_filter_tvalid;
    logic matched_filter_tlast;
    logic [C_S00_AXIS_TDATA_WIDTH-1:0] matched_filter_tdata;
    logic [(C_S00_AXIS_TDATA_WIDTH/8)-1:0] matched_filter_tstrb;
    axis_fir #(.NUM_COEFFS(NUM_COEFFS_PREAMBLE_DETECTOR)) preamble_detection_fir_filter (
        .s00_axis_aclk(s00_axis_aclk),
        .s00_axis_aresetn(s00_axis_aresetn),
        .s00_axis_tlast(s00_axis_tlast),
        .s00_axis_tvalid(s00_axis_tvalid),
        .s00_axis_tdata({{16{adc_data_real[15]}}, adc_data_real}),
        .s00_axis_tstrb(s00_axis_tstrb),
        .s00_axis_tready(),
        .coeffs(preamble_coeffs),
        .m00_axis_tready(matched_filter_tready),
        .m00_axis_tvalid(matched_filter_tvalid),
        .m00_axis_tlast(matched_filter_tlast),
        .m00_axis_tdata(matched_filter_tdata),
        .m00_axis_tstrb(matched_filter_tstrb)
    );

    assign m01_axis_tready = matched_filter_tready;
    assign m01_axis_tvalid = matched_filter_tvalid;
    assign m01_axis_tlast = matched_filter_tlast;
    assign m01_axis_tdata = matched_filter_tdata;
    assign m01_axis_tstrb = matched_filter_tstrb;

    // Bottom bit is the trigger, top bit is polarity. If top bit is 0, then positive = 1 and negative = 0. If top bit is 1, invert.
    logic[1:0] trigger;
    preamble_detector my_preamble_detector(
        .s00_axis_aclk(s00_axis_aclk),
        .s00_axis_aresetn(s00_axis_aresetn),
        .s00_axis_tlast(matched_filter_tlast),
        .s00_axis_tvalid(matched_filter_tvalid),
        .s00_axis_tdata(matched_filter_tdata),
        .s00_axis_tstrb(matched_filter_tstrb),
        .s00_axis_tready(matched_filter_tready),
        .trigger(trigger),
        .preamble_detector_threshold(preamble_detector_threshold)
    );

    sample_decoder my_sample_decoder(
        .s00_axis_aclk(s00_axis_aclk),
        .s00_axis_aresetn(s00_axis_aresetn),
        .s00_axis_tlast(s00_axis_tlast),
        .s00_axis_tvalid(s00_axis_tvalid),
        .s00_axis_tdata(adc_data_real),
        .s00_axis_tstrb(s00_axis_tstrb),
        .trigger(trigger),
        .decoder_threshold(decoder_threshold),
        .m00_axis_tdata(m00_axis_tdata),
        .m00_axis_tvalid(m00_axis_tvalid),
        .m00_axis_tlast(m00_axis_tlast),
        .m00_axis_tstrb(m00_axis_tstrb),
        .thresholded_data_debug(thresholded_data_debug)
    );

endmodule

`default_nettype none
`timescale 1 ns / 1 ps

module sample_decoder #
	(
		parameter integer C_S00_AXIS_TDATA_WIDTH	= 16,
        parameter integer PACKET_LENGTH = 128,
		parameter integer C_M00_AXIS_TDATA_WIDTH = PACKET_LENGTH
	)
	(
		// Ports of Axi Slave Bus Interface S00_AXIS
		input wire  s00_axis_aclk, s00_axis_aresetn,
		input wire  s00_axis_tlast, s00_axis_tvalid,
		input wire [C_S00_AXIS_TDATA_WIDTH-1 : 0] s00_axis_tdata, // Magnitude data from the CORDIC.
		input wire [(C_S00_AXIS_TDATA_WIDTH/8)-1: 0] s00_axis_tstrb,
		output logic  s00_axis_tready,

		// Ports of Axi Master Bus Interface M00_AXIS
		output logic  m00_axis_tvalid, m00_axis_tlast,
		output logic [C_M00_AXIS_TDATA_WIDTH-1 : 0] m00_axis_tdata, // Outputs 112-bit ADS-B squitters. Ignore downstream ready because we have a FIFO downstream.
		output logic [(C_M00_AXIS_TDATA_WIDTH/8)-1: 0] m00_axis_tstrb,

        input wire [1:0] trigger,
        input wire [C_S00_AXIS_TDATA_WIDTH-1:0] decoder_threshold, // Threshold used to decide if magnitude is a 0-bit or 1-bit.
        
        output wire thresholded_data_debug // Helpful for debugging with the ILA.
	);

    assign s00_axis_tready = 1'b1;
    assign m00_axis_tstrb = 16'b1111_1111_1111_1111;
    assign m00_axis_tlast = 1'b1;

    logic polarity;

    localparam integer SAMPLES_PER_SYMBOL = 32; 
    logic [$clog2(PACKET_LENGTH) - 1:0] bit_counter; 
    logic [$clog2(SAMPLES_PER_SYMBOL) - 1:0] sample_counter;
    logic decoded_bit;
    assign decoded_bit = ~s00_axis_tdata[C_S00_AXIS_TDATA_WIDTH-1] ^ polarity;
    enum {IDLE, RECORDING} state; 

    logic first_physical_bit;

    always_ff @(posedge s00_axis_aclk) begin
        if (~s00_axis_aresetn) begin
            state <= IDLE;
            sample_counter <= 0;
            bit_counter <= 0;
        end
        else begin
            case (state)
                IDLE: begin
                    m00_axis_tvalid <= 0;
                    if(trigger[0]) begin
                        polarity <= trigger[1];
                        sample_counter <= 3;
                        bit_counter <= 0;
                        state <= RECORDING;
                        m00_axis_tdata <= 0;
                    end
                end
                RECORDING: begin
                    if(s00_axis_tvalid) begin
                        if((bit_counter == 0 && sample_counter == SAMPLES_PER_SYMBOL / 2) || sample_counter == SAMPLES_PER_SYMBOL - 1) begin
                            m00_axis_tdata <= (m00_axis_tdata << 1) + decoded_bit;
                            if(bit_counter == PACKET_LENGTH - 1) begin
                                state <= IDLE;
                                m00_axis_tvalid <= 1;
                            end else begin
                                sample_counter <= 0;
                                bit_counter <= bit_counter + 1;
                            end
                        end else begin
                            sample_counter <= sample_counter + 1;
                        end
                    end
                end
            endcase
        end
    end
endmodule

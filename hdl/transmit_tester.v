module transmit_tester #
	(
		parameter integer C_M00_AXIS_TDATA_WIDTH = 32
	)
	(
        input wire  m00_axis_aclk, m00_axis_aresetn,
        input wire  m00_axis_tready,
        output wire  m00_axis_tvalid, m00_axis_tlast,
        output wire [C_M00_AXIS_TDATA_WIDTH-1 : 0] m00_axis_tdata,
        output wire [(C_M00_AXIS_TDATA_WIDTH/8)-1: 0] m00_axis_tstrb
	);
 
    //You want to send up TLAST-framed bursts of data that are 2**16 in length
    //update and test this module to make sure that's happening.

    reg [17:0] count;
    reg state;
 
    always @(posedge m00_axis_aclk)begin
        if(!m00_axis_aresetn)begin
            count <= 0;
            state <= 0;
        end else begin
            if(count == 65535) begin
                count <= 0;
                state <= ~state;
            end else begin
                count <= count + 1;
            end
        end
    end

    assign m00_axis_tvalid = 1;
    assign m00_axis_tdata = {16'd0, (state == 0 ? 16'd150 : -16'd150)};

endmodule


//mmcm or pll ip

//
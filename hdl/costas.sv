`timescale 1ns/1ps
module costas #
    (
        parameter integer C_S00_AXIS_TDATA_WIDTH    = 32,
        parameter integer C_M00_AXIS_TDATA_WIDTH    = 32
    )
    (
        // Ports of Axi Slave Bus Interface S00_AXIS
        input  wire                          s00_axis_aclk,
        input  wire                          s00_axis_aresetn,
        input  wire                          s00_axis_tlast,
        input  wire                          s00_axis_tvalid,
        input  wire [C_S00_AXIS_TDATA_WIDTH-1 : 0] s00_axis_tdata,
        input  wire [(C_S00_AXIS_TDATA_WIDTH/8)-1: 0] s00_axis_tstrb,
        output reg                           s00_axis_tready,

        // Ports of Axi Master Bus Interface M00_AXIS
        input  wire                          m00_axis_aclk,
        input  wire                          m00_axis_aresetn,
        input  wire                          m00_axis_tready,
        output reg                           m00_axis_tvalid,
        output reg                           m00_axis_tlast,
        output reg [C_M00_AXIS_TDATA_WIDTH-1 : 0] m00_axis_tdata,
        output reg [(C_M00_AXIS_TDATA_WIDTH/8)-1: 0] m00_axis_tstrb
    );

    localparam integer STAGES = 16;

    reg signed [15:0] CORDIC_ANGLES [0:STAGES];

    initial begin
        CORDIC_ANGLES[0] = 16'd8192;
        CORDIC_ANGLES[1] = 16'd4836;
        CORDIC_ANGLES[2] = 16'd2555;
        CORDIC_ANGLES[3] = 16'd1297;
        CORDIC_ANGLES[4] = 16'd651;
        CORDIC_ANGLES[5] = 16'd326;
        CORDIC_ANGLES[6] = 16'd163;
        CORDIC_ANGLES[7] = 16'd81;
        CORDIC_ANGLES[8] = 16'd41;
        CORDIC_ANGLES[9] = 16'd20;
        CORDIC_ANGLES[10] = 16'd10;
        CORDIC_ANGLES[11] = 16'd5;
        CORDIC_ANGLES[12] = 16'd3;
        CORDIC_ANGLES[13] = 16'd1;
        CORDIC_ANGLES[14] = 16'd1;
        CORDIC_ANGLES[15] = 16'd0;
    end

    logic signed [31:0] freq;
    logic signed [31:0] error;
    logic signed [31:0] beta_error;
    logic signed [15:0] phase;

    logic signed [31:0] new_freq;
    logic signed [15:0] new_phase;

    logic signed [15:0] phase_inc;

    logic signed [31:0] unscaled_new_phase;

    //alpha 8.0
    //beta 0.02, multiply by 20 and divide by 1024

    logic signed [31:0] px [0:STAGES];
    logic signed [31:0] py [0:STAGES];
    logic signed [15:0] pz [0:STAGES];

    logic pvalid [0:STAGES];
    logic plast  [0:STAGES];
    logic [3:0] pstrb  [0:STAGES];

    logic signed [15:0] x0;
    logic signed [15:0] y0;
    assign x0 = s00_axis_tdata[15:0];
    assign y0 = s00_axis_tdata[31:16];

    always @(posedge s00_axis_aclk) begin
        if (!s00_axis_aresetn) begin
            for (integer i=0; i <= STAGES; i=i+1) begin
                px[i] <= 0;
                py[i] <= 0;
                pz[i] <= 0;
                pvalid[i] <= 0;
                plast[i] <= 0;
                pstrb[i] <= 0;
            end

            m00_axis_tvalid <= 0;
            m00_axis_tlast  <= 0;
            m00_axis_tdata  <= 0;
            m00_axis_tstrb  <= 0;
            phase <= 0;
            freq <= 0;
        end else begin

            if (s00_axis_tvalid && s00_axis_tready) begin
                
                if ($signed(-phase) > $signed(16384) || $signed(-phase) < $signed(-16384)) begin
                    px[0] <= $signed(-x0 * $signed(39796));
                    py[0] <= $signed(-y0 * $signed(39796));
                    pz[0] <= -phase + 32768;
                end else begin
                    px[0] <= $signed(x0 * $signed(39796));
                    py[0] <= $signed(y0 * $signed(39796));
                    pz[0] <= -phase;
                end

                pvalid[0] <= 1;
                plast[0]  <= s00_axis_tlast;
                pstrb[0]  <= s00_axis_tstrb;
            end else begin
                pvalid[0] <= 0;
                plast[0]  <= 0;
                pstrb[0]  <= 0;
            end

            for (integer i = 0; i < STAGES; i = i + 1) begin

                if (pz[i] > 0) begin
                    px[i+1] <= $signed(px[i] - $signed(py[i] >>> i));
                    py[i+1] <= $signed(py[i] + $signed(px[i] >>> i));
                    pz[i+1] <= $signed($signed(pz[i]) - $signed(CORDIC_ANGLES[i]));
                end else begin
                    px[i+1] <= $signed(px[i] + $signed(py[i] >>> i));
                    py[i+1] <= $signed(py[i] - $signed(px[i] >>> i));
                    pz[i+1] <= $signed($signed(pz[i]) + $signed(CORDIC_ANGLES[i]));
                end

                pvalid[i+1] <= pvalid[i];
                plast[i+1] <= plast[i];
                pstrb[i+1] <= pstrb[i];
            end

            if(pvalid[STAGES]) begin
                freq <= new_freq;
                phase <= new_phase;
            end
        end
    end

    logic signed [31:0] final_x;
    logic signed [31:0] final_y;

    always_comb begin
        s00_axis_tready = m00_axis_tready;

        final_x = px[STAGES] >>> 16;
        final_y = py[STAGES] >>> 16;
        error = final_x * final_y;

        beta_error = ((error * 20) >>> 10);
        new_freq = (freq + beta_error);
        unscaled_new_phase = new_freq + (error >>> 1);
        phase_inc = ($signed({{6{unscaled_new_phase[31]}}, unscaled_new_phase}) * 11) >>> 10;
        new_phase = phase + phase_inc[15:0];

        m00_axis_tdata = {final_y[15:0], final_x[15:0]};
        m00_axis_tvalid = pvalid[STAGES];
        m00_axis_tstrb = pstrb[STAGES];
        m00_axis_tlast = plast[STAGES];
    end

endmodule

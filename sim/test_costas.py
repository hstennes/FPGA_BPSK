VICOCO = False
MATPLOTLIB = True

import cocotb
import os
import random
import sys
import math
import logging
from pathlib import Path
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb.utils import get_sim_time as gst
if VICOCO:
    from vicoco.vivado_runner import get_runner
else:
    from cocotb.runner import get_runner
from cocotb_bus.bus import Bus
if MATPLOTLIB:
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter
from cocotb_bus.drivers import BusDriver
from cocotb_bus.monitors import Monitor
from cocotb_bus.monitors import BusMonitor
from cocotb_bus.scoreboard import Scoreboard
import numpy as np
from cocotb.triggers import Timer, ClockCycles, RisingEdge, FallingEdge, ReadOnly


GAIN = 1 << 10

# global data recording
dut_iq = []
dut_error = []
dut_freq = []
dut_phase = []

def generate_bpsk_with_freq_offset(
    num_samples: int,
    samples_per_symbol: int = 1,
    freq_offset_hz: float = 50.0,
    fs: float = 1_000_000.0,
    noise_std: float = 0.0,
    seed: int | None = None,
):
    rng = np.random.default_rng(0)

    num_symbols = int(np.ceil(num_samples / samples_per_symbol))
    symbols = rng.choice([-1.0, +1.0], size=num_symbols)

    bpsk_sequence = np.repeat(symbols, samples_per_symbol)
    bpsk_sequence = bpsk_sequence[:num_samples]

    n = np.arange(num_samples) + 300
    phase = 2 * np.pi * freq_offset_hz * n / fs
    freq_rot = np.exp(1j * phase)

    iq = bpsk_sequence.astype(np.complex64) * freq_rot

    if noise_std > 0:
        noise = (rng.standard_normal(num_samples) +
                 1j * rng.standard_normal(num_samples)) * noise_std
        iq += noise.astype(np.complex64)

    return iq.astype(np.complex64)

sample_rate = 19e3

samples = generate_bpsk_with_freq_offset(
    num_samples=500,
    samples_per_symbol=1,
    freq_offset_hz=300,   # simulate a 200 Hz offset
    fs=sample_rate,
    noise_std=0.05
)
 
#cheap way to get the name of current file for runner:
test_file = os.path.basename(__file__).replace(".py","")
            
def format_input(x: int, y: int) -> int:
    x_16 = x & 0xFFFF
    y_16 = y & 0xFFFF
    return (y_16 << 16) | x_16

def format_costas_sample_data(iq: np.complex64):
    x = int(np.clip(iq.real * GAIN, -32768, 32767))
    y = int(np.clip(iq.imag * GAIN, -32768, 32767))

    # convert to 16-bit unsigned containers
    x &= 0xFFFF
    y &= 0xFFFF

    # print(hex(x), hex(y))

    return (y << 16) | x

def twos_to_int(x):
    x &= 0xFFFF
    if x & 0x8000:
        return x - 0x10000    
    else:
        return x
    
def twos_to_int32(x):
    x &= 0xFFFFFFFF          
    if x & 0x80000000:        
        return x - 0x100000000 
    else:
        return x

def decode_costas_data(val: int):
    return complex(twos_to_int(val) / GAIN, twos_to_int(val >> 16) / GAIN)

def parse_input(value: int) -> tuple[int, int]:
    x_16 = value & 0xFFFF
    y_16 = (value >> 16) & 0xFFFF
    x = x_16 - 0x10000 if x_16 & 0x8000 else x_16
    y = y_16 - 0x10000 if y_16 & 0x8000 else y_16
    return x, y

class AXIS_Monitor(BusMonitor):
    """
    monitors axi streaming bus
    """
    transactions = 0 #use this variable to track good ready/valid handshakes
    def __init__(self, dut, name, clk, callback=None):
        self._signals = ['axis_tvalid','axis_tready','axis_tlast','axis_tdata','axis_tstrb']
        BusMonitor.__init__(self, dut, name, clk, callback=callback)
        self.clock = clk
        self.transactions = 0
        self.dut = dut
        self.name = name
    async def _monitor_recv(self):
        """
        Monitor receiver
        """
        rising_edge = RisingEdge(self.clock) # make these coroutines once and reuse
        falling_edge = FallingEdge(self.clock)
        read_only = ReadOnly() #This is
        while True:
            #await rising_edge #can either wait for just edge...
            #or you can also wait for falling edge/read_only (see note in lab)
            await falling_edge #sometimes see in AXI shit
            await read_only  #readonly (the postline)
            valid = self.bus.axis_tvalid.value
            ready = self.bus.axis_tready.value
            last = self.bus.axis_tlast.value
            data = self.bus.axis_tdata.value #.signed_integer

            if valid and ready:

                if self.name == 'm00':
                    # print(self.dut.error.value)
                    print(decode_costas_data(int(data)).imag)
                    if not VICOCO:
                        dut_error.append(twos_to_int32(int(self.dut.error.value)) / (GAIN * GAIN))
                        # dut_error.append(twos_to_int32(int(self.dut.beta_error.value)))
                        dut_freq.append(twos_to_int32(int(self.dut.new_freq.value)) / (GAIN * GAIN))
                        dut_phase.append(int(self.dut.new_phase.value) * 2 * np.pi / (2 ** 16))
                        dut_iq.append(decode_costas_data(int(data)))
                        pass
                self.transactions+=1
                thing = dict(data=data.signed_integer,last=last,
                             name=self.name,count=self.transactions)
                # self.dut._log.info(f"{self.name}: {thing}")
                self._recv(data.signed_integer)


class AXIS_Driver(BusDriver):
    def __init__(self, dut, name, clk, role="M"):
        self._signals = ['axis_tvalid', 'axis_tready', 'axis_tlast', 'axis_tdata','axis_tstrb']
        BusDriver.__init__(self, dut, name, clk)
        self.clock = clk
        self.dut = dut

class S_AXIS_Driver(BusDriver):
    def __init__(self, dut, name, clk):
        AXIS_Driver.__init__(self, dut, name, clk)
        self.bus.axis_tready.value = 0

    async def _driver_send(self, value, sync=True):
        rising_edge = RisingEdge(self.clock) # make these coroutines once and reuse
        falling_edge = FallingEdge(self.clock)
        read_only = ReadOnly() #This is
        if value.get("type") == "pause":
            await falling_edge
            self.bus.axis_tready.value = 0 #set to 0 and be done.
            for i in range(value.get("duration",1)):
                await rising_edge
        else: #read command
            await falling_edge
            self.bus.axis_tready.value = 1
            for i in range(value.get("duration",1)):
                await rising_edge

class M_AXIS_Driver(AXIS_Driver):
    """AXI-Stream Master Driver (source)"""

    def __init__(self, dut, name, clk):
        super().__init__(dut, name, clk)
        self.bus.axis_tdata.value = 0
        self.bus.axis_tstrb.value = 0xF
        self.bus.axis_tlast.value = 0
        self.bus.axis_tvalid.value = 0

    async def _driver_send(self, value, sync=True):
        """Send transactions respecting AXIS handshake (tvalid/tready)."""
        if value.get("type") == "pause":
            await FallingEdge(self.clock)
            self.bus.axis_tvalid.value = 0
            self.bus.axis_tlast.value = 0
            for _ in range(value.get("duration", 1)):
                await RisingEdge(self.clock)
            return

        await FallingEdge(self.clock)
        arr = value["contents"]["data"] if value.get("type") != "write_single" else [value["contents"]["data"]]
        for i, data_word in enumerate(arr):
            self.bus.axis_tdata.value = int(data_word)
            self.bus.axis_tlast.value = 1 if i == len(arr) - 1 else 0
            self.bus.axis_tvalid.value = 1

            # Wait for handshake (tready == 1)
            while True:
                await RisingEdge(self.clock)
                await ReadOnly()
                if self.bus.axis_tready.value:
                    break

        # Deassert tvalid after sending all data
        await FallingEdge(self.clock)
        self.bus.axis_tvalid.value = 0
        self.bus.axis_tlast.value = 0


cordic_angles = [180/3.14159*math.atan(2**(-i)) for i in range(17)]

sig_in = [] #just for convenience
sig_out_exp = [] #contains list of expected outputs (Growing)
sig_out_act = [] #contains list of expected outputs (Growing)
def cordic_model(val):
    sig_in.append(val)
    
    x, y = parse_input(val)
    z = 0
    invert = x < 0
    if invert:
        x = -x
        y = -y
    for i in range(16):
        if y > 0:
            xn = x + 1/(2**i)*y
            yn = y - 1/(2**i)*x
            zn = z - cordic_angles[i]
        else: 
            xn = x - 1/(2**i)*y
            yn = y + 1/(2**i)*x
            zn = z + cordic_angles[i]
        x, y, z = xn, yn, zn
    if invert:
        z = (z + 180) % 360
    sig_out_exp.append((z, x / 1.646))


class CordicScoreboard(Scoreboard):

    def compare(self, got, exp, log, strict_type=True):
        # exp_angle, exp_magnitude = exp
        # got_angle = (360 * (got >> 16) / 2**16) % 360
        # got_magnitude = got & 65535

        # angle_error = abs(exp_angle - got_angle) / exp_angle
        # magnitude_error = abs(exp_magnitude - got_magnitude) / exp_magnitude
        
        # if angle_error > 0.005:
        #     log.error("Received angle different than expected")
        #     assert False
        # if magnitude_error > 0.01:
        #     log.error(f"Expected magnitude {exp_magnitude} but got {got_magnitude}")
        #     assert False
        # dut_iq.append(decode_costas_data(got))
        pass
        

async def reset(clk, reset_n, duration=2, active=0):
    """Drive reset for `duration` cycles."""
    reset_n.value = active  # assert reset
    await ClockCycles(clk, duration)
    reset_n.value = not active  # deassert reset
    await RisingEdge(clk)  # wait one more cycle to stabilize

@cocotb.test()
async def test_a(dut):
    """cocotb test for AXIS jmath"""

    inm = AXIS_Monitor(dut,'s00',dut.s00_axis_aclk,callback=cordic_model)
    outm = AXIS_Monitor(dut,'m00',dut.s00_axis_aclk,callback=lambda x: sig_out_act.append(x))
    ind = M_AXIS_Driver(dut,'s00',dut.s00_axis_aclk) #M driver for S port
    outd = S_AXIS_Driver(dut,'m00',dut.s00_axis_aclk) #S driver for M port

    # Create a scoreboard on the stream_out bus
    scoreboard = CordicScoreboard(dut,fail_immediately=False)
    scoreboard.add_interface(outm, sig_out_exp)
    cocotb.start_soon(Clock(dut.s00_axis_aclk, 10, units="ns").start())
    await reset(dut.s00_axis_aclk, dut.s00_axis_aresetn,2,0)

    #feed the driver on the M Side:

    for i in range(len(samples)):
        ind.append({'type':'write_single', "contents":{"data": format_costas_sample_data(samples[i]),"last":0}})
        ind.append({'type':'pause', "duration": 7})
    
    #feed the driver on the S Side:
    #always be ready to receive data:
    outd.append({'type':'read', "duration":5000})

    await ClockCycles(dut.s00_axis_aclk, 5000)
    #if transaction counts on input and output don't match, raise an issue!

    global dut_iq
    dut_iq = np.array(dut_iq)
    global dut_freq
    dut_freq = np.array(dut_freq)
    global dut_phase
    dut_phase = np.array(dut_phase)
    global dut_error
    dut_error = np.array(dut_error)

    for i in range(5):
        print(f"original {samples[i]:.6f} rot {dut_iq[i]:.6f}, error {dut_error[i]:.6f}, freq {dut_freq[i]:.6f}, phase {dut_phase[i]:.6f}")

    if MATPLOTLIB:
        fig, ((ax_iq, ax_error), (ax_freq, ax_phase)) = plt.subplots(2, 2, figsize=(10, 8))
        ax_iq.set_xlim(-1.5, 1.5)
        ax_iq.set_ylim(-1.5, 1.5)
        ax_iq.set_xlabel("I")
        ax_iq.set_ylabel("Q")
        ax_iq.set_title("IQ Plot")
        # scatter = ax_iq.scatter(dut_iq.real, dut_iq.imag)
        scatter = ax_iq.scatter([], [])

        ax_error.set_title("Error")
        ax_error.set_xlabel("Sample Index")
        ax_error.set_ylabel("err")
        ax_error.plot(np.arange(len(dut_error)), dut_error)

        ax_freq.set_title("Frequency")
        ax_freq.set_xlabel("Sample Index")
        ax_freq.set_ylabel("Hz")
        ax_freq.plot(np.arange(len(dut_freq)), dut_freq)

        ax_phase.set_title("Phase")
        ax_phase.set_xlabel("Sample Index")
        ax_phase.set_ylabel("Phase (radians)")
        ax_phase.plot(np.arange(len(dut_phase)), dut_phase)

        # update animation frame
        def update(frame):
            # update IQ scatter (sliding window)
            window = dut_iq[frame:(frame+1)]
            scatter.set_offsets(np.column_stack((window.real, window.imag)))

            return scatter

        anim = FuncAnimation(fig, update, frames=250, interval=30, blit=False)
        plt.show()


"""the code below should largely remain unchanged in structure, though the specific files and things
specified should get updated for different simulations.
"""
def axis_runner():
    """Simulate the counter using the Python runner."""
    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
    if VICOCO:
        sim = os.getenv("SIM", "vivado")
    else:
        sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [proj_path / "hdl" / "costas.sv", proj_path / "hdl" / "costas_wrapper.v"] #grow/modify this as needed.
    hdl_toplevel = "costas_wrapper"
    build_test_args = ["-Wall"]#,"COCOTB_RESOLVE_X=ZEROS"]
    parameters = {}
    sys.path.append(str(proj_path / "sim"))
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel=hdl_toplevel,
        always=True,
        build_args=build_test_args,
        parameters=parameters,
        timescale = ('1ns','1ps'),
        waves=True
    )
    run_test_args = []
    runner.test(
        hdl_toplevel=hdl_toplevel,
        test_module=test_file,
        test_args=run_test_args,
        waves=True
    )
 
if __name__ == "__main__":
    axis_runner()
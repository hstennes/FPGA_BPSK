import cocotb
import os
import random
import sys
import logging
from pathlib import Path
from cocotb.triggers import Timer
from cocotb.utils import get_sim_time as gst
from cocotb.runner import get_runner
 
#cheap way to get the name of current file for runner:
test_file = os.path.basename(__file__).replace(".py","")
 
async def generate_clock(clock_wire):
	while True: # repeat forever
		clock_wire.value = 0
		await Timer(5,units="ns")
		clock_wire.value = 1
		await Timer(5,units="ns")

@cocotb.test()
async def first_test(dut):
    """ First cocotb test?"""
    # write your test here!
	  # throughout your test, use "assert" statements to test for correct behavior
	  # replace the assertion below with useful statements
    """First cocotb test?"""
    await cocotb.start( generate_clock( dut.m00_axis_aclk ) ) #launches clock
    dut.m00_axis_aresetn.value = 0
    await Timer(1000, "ns")
    dut.m00_axis_aresetn.value = 1
    await Timer(1000000, "ns")
 
"""the code below should largely remain unchanged in structure, though the specific files and things
specified should get updated for different simulations.
"""
def transmit_runner():
    """Simulate the counter using the Python runner."""
    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    sys.path.append(str(proj_path / "sim" / "model"))
    sources = [proj_path / "hdl" / "transmit_tester.v"] #grow/modify this as needed.
    hdl_toplevel = "transmit_tester"
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
    transmit_runner()
""" unit tests fuels.py functions
"""

import os

import pyrolib.fuels as pl
import pytest


def test_simple_case_ff():
    scenario = pl.Scenario(load='FireFluxI')
    fuelmap = pl.FuelMap(scenario=scenario, workdir=f"{os.getcwd()}/examples")

    fuelmap.add_rectangle_patch_fuel(xpos=[50.0, 450.0], ypos=[50.0, 450.0], fuel_index=1)
    fuelmap.add_rectangle_patch_ignition(xpos=[100.0, 105.0], ypos=[245.0, 255.0], ignition_time=10.0)
    fuelmap.add_rectangle_patch_unburnable(xpos=[100.0, 150.0], ypos=[50.0, 150.0])

    fuelmap.add_line_patch_fuel(xpos=[50.0, 450.0], ypos=[50.0, 450.0], fuel_index=1)
    fuelmap.add_line_patch_ignition(xpos=[100.0, 105.0], ypos=[245.0, 255.0], ignition_time=10.0)
    fuelmap.add_line_patch_unburnable(xpos=[100.0, 150.0], ypos=[50.0, 150.0])
    fuelmap.add_line_patch_walking_ignition([200.0, 200.0], [300.0, 350.0], walking_ignition_times=[0.0, 100.0])

    fuelmap.dump_mesonh()
    assert os.path.exists(f"{os.getcwd()}/examples/FuelMap.nc")
    assert os.path.exists(f"{os.getcwd()}/examples/FuelMap.des")

    fuelmap.dump()
    assert os.path.exists(f"{os.getcwd()}/examples/FuelMap2d.nc")
    os.remove(f"{os.getcwd()}/examples/FuelMap.nc")
    os.remove(f"{os.getcwd()}/examples/FuelMap.des")
    os.remove(f"{os.getcwd()}/examples/FuelMap2d.nc")

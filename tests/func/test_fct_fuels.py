""" unit tests fuels.py functions
"""

import os

import pyrolib.fuels as pl
import pytest


def test_simple_case_ff():
    scenario = pl.Scenario(load='FireFluxI')
    fuelmap = pl.FuelMap(scenario=scenario, workdir=f"{os.getcwd()}/examples")
    fuelmap.addRectanglePatch(xpos=[50, 450], ypos=[50, 450], fuelindex=1)
    fuelmap.addRectanglePatch(xpos=[100, 105], ypos=[245, 255], ignitiontime=10)
    fuelmap.addRectanglePatch(xpos=[100, 150], ypos=[50, 150], unburnable=True)
    fuelmap.addLinePatch([200, 200], [300, 350], walkingignitiontimes=[0, 100])

    fuelmap.write(save2dfile=True)
    assert os.path.exists(f"{os.getcwd()}/examples/FuelMap.nc")
    assert os.path.exists(f"{os.getcwd()}/examples/FuelMap.des")
    assert os.path.exists(f"{os.getcwd()}/examples/FuelMap2d.nc")
    os.remove(f"{os.getcwd()}/examples/FuelMap.nc")
    os.remove(f"{os.getcwd()}/examples/FuelMap.des")
    os.remove(f"{os.getcwd()}/examples/FuelMap2d.nc")

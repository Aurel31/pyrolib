""" unit tests fuels.py functions
"""

import os

import pyrolib.fuelmap as pl
import pytest


def test_simple_case_ff():
    my_db = pl.FuelDatabase()
    my_db.load_fuel_database("FireFluxI")
    fuelmap = pl.FuelMap(fuel_db=my_db, workdir=f"{os.getcwd()}/examples/fuel_map")

    fuelmap.add_fuel_rectangle_patch(
        pos1=[50.0, 450.0], pos2=[50.0, 450.0], fuel_key="FireFluxI_tall_grass"
    )
    fuelmap.add_ignition_rectangle_patch(pos1=[100.0, 105.0], pos2=[245.0, 255.0], ignition_time=10.0)
    fuelmap.add_unburnable_rectangle_patch(pos1=[100.0, 150.0], pos2=[50.0, 150.0])

    fuelmap.add_fuel_line_patch(pos1=[50.0, 450.0], pos2=[50.0, 450.0], fuel_key="FireFluxI_tall_grass")
    fuelmap.add_ignition_line_patch(pos1=[100.0, 105.0], pos2=[245.0, 255.0], ignition_time=10.0)
    fuelmap.add_unburnable_line_patch(pos1=[100.0, 150.0], pos2=[50.0, 150.0])
    fuelmap.add_walking_ignition_line_patch(
        [200.0, 200.0], [300.0, 350.0], walking_ignition_times=[0.0, 100.0]
    )

    fuelmap.dump_mesonh()
    assert os.path.exists(f"{os.getcwd()}/examples/fuel_map/FuelMap.nc")
    assert os.path.exists(f"{os.getcwd()}/examples/fuel_map/FuelMap.des")

    fuelmap.dump()
    assert os.path.exists(f"{os.getcwd()}/examples/fuel_map/FuelMap2d.nc")
    os.remove(f"{os.getcwd()}/examples/fuel_map/FuelMap.nc")
    os.remove(f"{os.getcwd()}/examples/fuel_map/FuelMap.des")
    os.remove(f"{os.getcwd()}/examples/fuel_map/FuelMap2d.nc")

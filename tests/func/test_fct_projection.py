""" functional tests: patches positioned in (lon, lat) on a Méso-NH conformal projection
"""

import os
import shutil

import numpy as np
import pytest
from netCDF4 import Dataset

import pyrolib.fuelmap as pl
from pyrolib.fuelmap.utility import convert_lon_lat_to_x_y

WORKDIR = "examples/fuel_map"


@pytest.fixture
def fuel_db():
    my_db = pl.FuelDatabase()
    my_db.load_fuel_database("FireFluxI")
    return my_db


@pytest.fixture
def lambert_workdir(tmp_path):
    """Copy of examples/fuel_map whose initialization file carries a Lambert conformal projection

    Init_file.nc only has LAT0, LON0 and BETA; Méso-NH also writes RPK, LATORI and
    LONORI for a non-cartesian domain. RPK = sin(LAT0) is the Méso-NH default.
    """
    workdir = f"{os.getcwd()}/{WORKDIR}"
    for filename in ("EXSEG1.nam", "Init_file.des", "Init_file.nc"):
        shutil.copy2(f"{workdir}/{filename}", tmp_path / filename)
    with Dataset(tmp_path / "Init_file.nc", "a") as ncfile:
        for name, value in (("RPK", np.sin(np.deg2rad(43.29))), ("LATORI", 43.29), ("LONORI", 0.0)):
            variable = ncfile.createVariable(name, np.float64, ())
            variable[...] = value
    return str(tmp_path)


def test_lon_lat_positions_need_a_projection(fuel_db):
    """The example initialization file is cartesian: (lon, lat) positions cannot be used"""
    fuelmap = pl.FuelMap(fuel_db=fuel_db, workdir=f"{os.getcwd()}/{WORKDIR}")
    assert fuelmap.confproj is None

    with pytest.raises(ValueError, match="Init_file.nc has no conformal projection"):
        fuelmap.add_fuel_rectangle_patch(
            pos1=[0.0, 0.005], pos2=[43.29, 43.294], fuel_key="FireFluxI_tall_grass", is_cartesian=False
        )
    with pytest.raises(ValueError, match="is_cartesian=True"):
        fuelmap.add_ignition_line_patch(
            pos1=[0.0, 0.005], pos2=[43.29, 43.294], ignition_time=10.0, is_cartesian=False
        )


def test_lon_lat_positions_match_converted_x_y(fuel_db, lambert_workdir):
    """Patches given in (lon, lat) land where the same positions converted to (x, y) do"""
    lon = [0.0006, 0.0055]
    lat = [43.2905, 43.2940]

    fuelmap_lonlat = pl.FuelMap(fuel_db=fuel_db, workdir=lambert_workdir)
    assert fuelmap_lonlat.confproj == {
        "beta": 0.0,
        "k": pytest.approx(np.sin(np.deg2rad(43.29))),
        "lat_ori": 43.29,
        "lon_ori": 0.0,
        "lat0": 43.29,
        "lon0": 0.0,
    }
    fuelmap_lonlat.add_fuel_rectangle_patch(
        pos1=lon, pos2=lat, fuel_key="FireFluxI_tall_grass", is_cartesian=False
    )
    fuelmap_lonlat.add_ignition_line_patch(
        pos1=[lon[0], lon[1]], pos2=[lat[0], lat[1]], ignition_time=10.0, is_cartesian=False
    )

    x, y = convert_lon_lat_to_x_y(fuelmap_lonlat.confproj, lat=lat, lon=lon)
    # the chosen corners are well inside the 500 m x 500 m fire domain
    assert 0.0 < x[0] < x[1] < 500.0
    assert 0.0 < y[0] < y[1] < 500.0

    fuelmap_xy = pl.FuelMap(fuel_db=fuel_db, workdir=lambert_workdir)
    fuelmap_xy.add_fuel_rectangle_patch(pos1=x, pos2=y, fuel_key="FireFluxI_tall_grass")
    fuelmap_xy.add_ignition_line_patch(pos1=[x[0], x[1]], pos2=[y[0], y[1]], ignition_time=10.0)

    assert np.count_nonzero(fuelmap_xy.fuelmaparray[0]) > 1
    assert np.count_nonzero(fuelmap_xy.ignitionmaparray == 10.0) > 1
    np.testing.assert_array_equal(fuelmap_lonlat.fuelmaparray, fuelmap_xy.fuelmaparray)
    np.testing.assert_array_equal(fuelmap_lonlat.ignitionmaparray, fuelmap_xy.ignitionmaparray)

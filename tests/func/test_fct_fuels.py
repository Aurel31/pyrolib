""" functional tests: build a fuel map on the examples/fuel_map fixtures and check the written files
"""

import os

import numpy as np
import pytest
from netCDF4 import Dataset

import pyrolib.fuelmap as pl
from pyrolib.fuelmap.fuels import BalbiFuel
from pyrolib.fuelmap.utility import fire_array_3d_to_2d

WORKDIR = "examples/fuel_map"
FILES = ("FuelMap.nc", "FuelMap.des", "FuelMap2d.nc")

# refinement of the fire grid in examples/fuel_map/EXSEG1.nam
NREFINX = 5
NREFINY = 5


@pytest.fixture(scope="module")
def fuelmap_files():
    """Build the FireFlux I test case and dump both netCDF files, removed after the module runs"""
    my_db = pl.FuelDatabase()
    my_db.load_fuel_database("FireFluxI")
    workdir = f"{os.getcwd()}/{WORKDIR}"
    fuelmap = pl.FuelMap(fuel_db=my_db, workdir=workdir)

    fuelmap.add_fuel_rectangle_patch(pos1=[50.0, 450.0], pos2=[50.0, 450.0], fuel_key="FireFluxI_tall_grass")
    fuelmap.add_ignition_rectangle_patch(pos1=[100.0, 105.0], pos2=[245.0, 255.0], ignition_time=10.0)
    fuelmap.add_unburnable_rectangle_patch(pos1=[100.0, 150.0], pos2=[50.0, 150.0])

    fuelmap.add_fuel_line_patch(pos1=[50.0, 450.0], pos2=[50.0, 450.0], fuel_key="FireFluxI_tall_grass")
    fuelmap.add_ignition_line_patch(pos1=[100.0, 105.0], pos2=[245.0, 255.0], ignition_time=10.0)
    fuelmap.add_unburnable_line_patch(pos1=[100.0, 150.0], pos2=[50.0, 150.0])
    fuelmap.add_walking_ignition_line_patch(
        [200.0, 200.0], [300.0, 350.0], walking_ignition_times=[0.0, 100.0]
    )

    fuelmap.dump_mesonh()
    fuelmap.dump()

    yield {"workdir": workdir, "fuel": my_db["FireFluxI_tall_grass"]["BalbiFuel"]}

    for filename in FILES:
        path = f"{workdir}/{filename}"
        if os.path.exists(path):
            os.remove(path)


@pytest.fixture(scope="module")
def mesonh_file(fuelmap_files):
    """FuelMap.nc, the file read by Méso-NH (fire fields packed as (F, Y, X))"""
    with Dataset(f"{fuelmap_files['workdir']}/FuelMap.nc") as ncfile:
        ncfile.set_auto_mask(False)
        yield ncfile


@pytest.fixture(scope="module")
def human_file(fuelmap_files):
    """FuelMap2d.nc, the human-readable file (fire fields as (YFIRE, XFIRE))"""
    with Dataset(f"{fuelmap_files['workdir']}/FuelMap2d.nc") as ncfile:
        ncfile.set_auto_mask(False)
        yield ncfile


def fire_field_names():
    """Names of every fire field variable expected in both files"""
    names = ["Ignition", "WalkingIgnition", "Fuel_type"]
    for propertyobj in vars(BalbiFuel()).values():
        if propertyobj.propertyindex is not None:
            names.append(propertyobj.name)
    return names


def cell_index(coordinates, position):
    """Index of the fire cell whose center is the closest to position"""
    return int(np.argmin(np.abs(coordinates - position)))


def test_simple_case_ff(fuelmap_files):
    for filename in FILES:
        assert os.path.exists(f"{fuelmap_files['workdir']}/{filename}")


def test_des_file_is_copied(fuelmap_files):
    with open(f"{fuelmap_files['workdir']}/Init_file.des") as reference:
        with open(f"{fuelmap_files['workdir']}/FuelMap.des") as copied:
            assert copied.read() == reference.read()


@pytest.mark.parametrize("which", ["mesonh_file", "human_file"])
def test_mesonh_header(which, request):
    """Both files carry the same MesoNH header, version metadata and atmospheric grid"""
    ncfile = request.getfixturevalue(which)

    assert ncfile.Conventions == "CF-1.7 COMODO-1.4"
    assert ncfile.MNH_REAL == "8"
    assert ncfile.MNH_INT == "4"
    assert ncfile.MNH_cleanly_closed == "yes"
    assert ncfile.MNH_REDUCE_DIMENSIONS_IN_FILES == "1"
    assert ncfile.MNH_REDUCE_FLOAT_PRECISION == "0"
    assert ncfile.MNH_COMPRESS_LOSSY == "0"

    # default Méso-NH version of FuelMap() is 6.1.0
    assert ncfile.MNH_VERSION_STR == "6.1.0"
    assert ncfile.MNH_VERSION.dtype == np.int32
    np.testing.assert_array_equal(ncfile.MNH_VERSION, [6, 1, 0])
    assert ncfile.MNH_VERSION_USER == ""

    # legacy fallback read by IO_Mnhversion_get before 6.0.0
    assert ncfile["MNHVERSION"].dtype == np.int32
    np.testing.assert_array_equal(ncfile["MNHVERSION"][:], [6, 1, 0])
    assert ncfile["MASDEV"].dtype == np.int32
    assert ncfile["MASDEV"][...] == 61
    assert ncfile["BUGFIX"].dtype == np.int32
    assert ncfile["BUGFIX"][...] == 0

    assert ncfile["FILETYPE"][:].tobytes().decode() == "BlazeData       "
    assert ncfile["STORAGE_TYPE"][:].tobytes().decode() == "TT              "

    assert ncfile.dimensions["size3"].size == 3
    assert ncfile.dimensions["char16"].size == 16
    assert ncfile.dimensions["X"].size == ncfile["X"].size == 22
    assert ncfile.dimensions["Y"].size == ncfile["Y"].size == 22
    assert ncfile["X"].units == "m"
    assert ncfile["Y"].units == "m"


def test_mesonh_fire_dimensions(mesonh_file):
    assert mesonh_file.dimensions["F"].size == NREFINX * NREFINY
    np.testing.assert_array_equal(mesonh_file["F"][:], np.arange(NREFINX * NREFINY))
    for name in fire_field_names():
        assert mesonh_file[name].dimensions == ("F", "Y", "X")


def test_human_fire_dimensions(human_file):
    nx, ny = human_file.dimensions["X"].size, human_file.dimensions["Y"].size
    assert human_file.dimensions["XFIRE"].size == nx * NREFINX
    assert human_file.dimensions["YFIRE"].size == ny * NREFINY
    # fire cell centers subdivide the atmospheric cells
    assert human_file["XFIRE"][1] - human_file["XFIRE"][0] == pytest.approx(
        (human_file["X"][1] - human_file["X"][0]) / NREFINX
    )
    for name in fire_field_names():
        assert human_file[name].dimensions == ("YFIRE", "XFIRE")


@pytest.mark.parametrize("name", fire_field_names())
def test_fire_fields_match_between_files(name, mesonh_file, human_file):
    """FuelMap2d.nc must show exactly what Méso-NH reads from FuelMap.nc"""
    packed = mesonh_file[name]
    unpacked = human_file[name]

    assert packed.dtype == unpacked.dtype == np.float64
    for attribute in ("standard_name", "long_name", "comment", "units"):
        assert packed.getncattr(attribute) == unpacked.getncattr(attribute)
    assert packed.grid == unpacked.grid == 4

    nx, ny = mesonh_file.dimensions["X"].size, mesonh_file.dimensions["Y"].size
    np.testing.assert_array_equal(fire_array_3d_to_2d(packed[:], nx, ny, NREFINX, NREFINY), unpacked[:])


def test_fuel_field_values(fuelmap_files, human_file):
    fuel = fuelmap_files["fuel"]
    x, y = human_file["XFIRE"][:], human_file["YFIRE"][:]

    # inside the fuel patch, outside every other patch: first fuel used gets index 1
    j, i = cell_index(y, 302.5), cell_index(x, 302.5)
    assert human_file["Fuel_type"][j, i] == 1
    for propertyobj in vars(fuel).values():
        if propertyobj.propertyindex is not None:
            assert human_file[propertyobj.name][j, i] == propertyobj.value
            assert human_file[propertyobj.name].units == propertyobj.unit
            assert human_file[propertyobj.name].comment == propertyobj.description

    # outside every patch: no fuel
    j, i = cell_index(y, 22.5), cell_index(x, 22.5)
    assert human_file["Fuel_type"][j, i] == 0

    # unburnable patch inside the fuel patch: fuel index and every property zeroed
    j, i = cell_index(y, 102.5), cell_index(x, 122.5)
    assert human_file["Fuel_type"][j, i] == 0
    for propertyobj in vars(fuel).values():
        if propertyobj.propertyindex is not None:
            assert human_file[propertyobj.name][j, i] == 0.0


def test_ignition_field_values(human_file):
    x, y = human_file["XFIRE"][:], human_file["YFIRE"][:]
    ignition = human_file["Ignition"][:]

    j, i = cell_index(y, 252.5), cell_index(x, 102.5)
    assert ignition[j, i] == 10.0
    # default: never ignited
    j, i = cell_index(y, 302.5), cell_index(x, 302.5)
    assert ignition[j, i] == 1e6
    assert set(np.unique(ignition)) == {10.0, 1e6}


def test_walking_ignition_field_values(human_file):
    x, y = human_file["XFIRE"][:], human_file["YFIRE"][:]
    walking = human_file["WalkingIgnition"][:]

    # line from (200, 300) to (200, 350) ignited between 0 s and 100 s, -1 elsewhere
    rows, cols = np.nonzero(walking != -1)
    assert rows.size > 1
    assert np.all(np.abs(x[cols] - 200.0) <= x[1] - x[0])
    assert y[rows].min() == pytest.approx(300.0, abs=y[1] - y[0])
    assert y[rows].max() == pytest.approx(350.0, abs=y[1] - y[0])

    # times grow linearly along the line; the interpolation is anchored on cell
    # centers, so both ends can overshoot by up to one cell diagonal
    on_line = walking[rows, cols]
    assert np.all(np.diff(on_line) > 0)
    cell_diagonal_time = 100.0 * np.hypot(x[1] - x[0], y[1] - y[0]) / 50.0
    assert on_line.min() == pytest.approx(0.0, abs=cell_diagonal_time)
    assert on_line.max() == pytest.approx(100.0, abs=cell_diagonal_time)

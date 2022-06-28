""" unit tests fuels.py functions
"""

import pytest

import pyrolib.fuelmap as pl
from pyrolib.fuelmap.fuels import FuelProperty
from pyrolib.fuelmap.utility import convert_lon_lat_to_x_y
from numpy import isclose

"""
Parameter
"""


def test_property_init():
    fuelproperty = FuelProperty("test", 0.0, "-", "none", propertyindex=None)
    assert fuelproperty.name == "test"
    assert fuelproperty.value == 0.0
    assert fuelproperty.unit == "-"
    assert fuelproperty.description == "none"
    assert fuelproperty.propertyindex == None


def test_property_set():
    fuelproperty = FuelProperty("test", 0.0, "-", "none", propertyindex=None)
    fuelproperty.set(1.0)
    assert fuelproperty.value == 1.0


def test_property_show(capsys):
    fuelproperty = FuelProperty("test", 0.0, "-", "none", propertyindex=None)
    print(fuelproperty)
    captured = capsys.readouterr()
    assert captured.out == "Property    test = 0.000e+00 [-     ] as none\n"


def test_property_minimal_dict():
    fuelproperty = FuelProperty("test", 0.0, "-", "none", propertyindex=None)
    mdict = fuelproperty.minimal_dict()
    assert mdict["description"] == "none"
    assert mdict["unit"] == "-"
    assert mdict["value"] == 0.0


"""
Balbi Fuel
"""


@pytest.mark.parametrize(
    "property,default_value,property_index",
    [
        ("rhod", 400, 1),
        ("rhol", 400, 2),
        ("Md", 0.1, 3),
        ("Ml", 1.0, 4),
        ("sd", 5000, 5),
        ("sl", 5000, 6),
        ("sigmad", 0.95, 7),
        ("sigmal", 0.05, 8),
        ("e", 1.0, 9),
        ("Ti", 500, 10),
        ("Ta", 300.0, 11),
        ("DeltaH", 15.43e6, 12),
        ("Deltah", 2.3e6, 13),
        ("tau0", 75590, 14),
        ("stoch", 8.3, 15),
        ("rhoa", 1.2, 16),
        ("cp", 1912, 17),
        ("cpa", 1004, 18),
        ("X0", 0.3, 19),
        ("LAI", 4.0, 20),
        ("r00", 2e-5, 21),
        ("wind", 0.0, None),
        ("slope", 0.0, None),
    ],
)
def test_BalbiFuel_init(property, default_value, property_index):
    fuel = pl.BalbiFuel()
    assert type(getattr(fuel, property)).__name__ == "FuelProperty"
    assert getattr(fuel, property).name == property
    assert getattr(fuel, property).value == default_value
    print(getattr(fuel, property).propertyindex)
    assert getattr(fuel, property).propertyindex == property_index


def test_BalbiFuel_value_change():
    fuel = pl.BalbiFuel(e=2.0)
    assert fuel.e.value == 2.0


def test_BalbiFuel_copy():
    fuel = pl.BalbiFuel()
    fuel2 = pl.BalbiFuel(e=2.0)
    assert fuel.e.value == 1.0
    assert fuel2.e.value == 2.0


def test_BalbiFuel_get_ROS():
    fuel = pl.BalbiFuel()
    assert fuel.getR() == 0.387354022265859


def test_BalbiFuel_get_property_vector():
    # if is ok for BalbiFuel, should be ok for other BaseFuel inherited classes
    fuel = pl.BalbiFuel()
    property_vector = fuel.get_property_vector(0, 22)
    assert property_vector[0] == 0
    assert len(property_vector) == 22


def test_BalbiFuel_minimal_dict_compact():
    mdict = pl.BalbiFuel().minimal_dict(compact=True)
    assert mdict["class"] == "BalbiFuel"
    assert mdict["properties"]["rhod"] == 400


def test_BalbiFuel_minimal_dict_not_compact():
    mdict = pl.BalbiFuel().minimal_dict(compact=False)
    assert mdict["class"] == "BalbiFuel"
    assert mdict["properties"]["rhod"]["value"] == 400


"""FuelDatabase
"""


def test_fuel_db_init():
    my_db = pl.FuelDatabase()
    assert my_db.fuels == {}


def test_fuel_db_dict():
    my_db = pl.FuelDatabase()
    my_fuel = pl.BalbiFuel()
    my_db["test"] = {"BalbiFuel": my_fuel}
    assert my_db["test"]["BalbiFuel"] == my_fuel


@pytest.mark.parametrize("filename", ["FireFluxI", "DefaultSA", "FireFluxI.yml", "DefaultSA.yml"])
def test_fuel_db_load_default(filename):
    my_db = pl.FuelDatabase()
    my_db.load_fuel_database(filename)


@pytest.mark.parametrize(
    "filename,iscompact", [("test", True), ("test", False), ("test.yml", True), ("test.yml", False)]
)
def test_fuel_db_dump(tmpdir, filename, iscompact):
    my_db = pl.FuelDatabase()
    my_db.load_fuel_database("FireFluxI")
    pathreal = tmpdir.ensure("test.yml")
    path = tmpdir.join(filename)
    my_db.dump_database(path.strpath, info="test", compact=iscompact)

    assert pathreal.readlines(cr=1)[0] == "infos: test\n"
    check_str = f"is_compact: {str(iscompact).lower()}\n"
    assert pathreal.readlines(cr=1)[1] == check_str


def test_convert_lon_lat_2_x_y_mercator_no_rotation():
    confproj = {
        "beta": 0.0,
        "k": 0.0,
        "lat_ori": 0.0,
        "lon_ori": 0.0,
        "lat0": 0.0,
        "lon0": 0.0,
    }
    lon_tgt = [0.0, 1.0]
    lat_tgt = [0.0, 1.0]
    xpos, ypos = convert_lon_lat_to_x_y(confproj, lat_tgt, lon_tgt)

    assert isclose(xpos[0], 0)
    assert isclose(xpos[1], 111198.9234485458)
    assert isclose(ypos[0], 0)
    assert isclose(ypos[1], 160434.28079762892)

def test_convert_lon_lat_2_x_y_mercator_rotation():
    confproj = {
        "beta": 1.0,
        "k": 0.0,
        "lat_ori": 0.0,
        "lon_ori": 0.0,
        "lat0": 0.0,
        "lon0": 0.0,
    }
    lon_tgt = [0.0, 1.0]
    lat_tgt = [0.0, 1.0]
    with pytest.raises(NotImplementedError):
        convert_lon_lat_to_x_y(confproj, lat_tgt, lon_tgt)

def test_convert_lon_lat_2_x_y_conformal():
    confproj = {
        "beta": 1.0,
        "k": 1.0,
        "lat_ori": 0.0,
        "lon_ori": 0.0,
        "lat0": 0.0,
        "lon0": 0.0,
    }
    lon_tgt = [0.0, 1.0]
    lat_tgt = [0.0, 1.0]
    with pytest.raises(NotImplementedError):
        convert_lon_lat_to_x_y(confproj, lat_tgt, lon_tgt)
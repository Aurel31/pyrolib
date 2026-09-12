""" unit tests fuels.py functions
"""

import pytest

import pyrolib.fuelmap as pl
from pyrolib.fuelmap.fuels import FuelProperty
from pyrolib.fuelmap.utility import convert_lon_lat_to_x_y
from numpy import isclose
from math import cos, radians

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
    # Reference value from SM_XYHAT_S (MNH mode_gridproj.f90):
    # XRADIUS * COS(XLAT0) * LOG(TAN(pi/4 + lat/2)), with XRADIUS = 6371229 m.
    assert isclose(ypos[1], 111204.56940003937)


def test_convert_lon_lat_2_x_y_mercator_no_rotation_mid_latitude():
    # Origin away from the equator, so a wrong isometric latitude cannot be
    # hidden by an origin offset of the same (wrong) scale.
    confproj = {
        "beta": 0.0,
        "k": 0.0,
        "lat_ori": 43.29,
        "lon_ori": 0.0,
        "lat0": 43.29,
        "lon0": 0.0,
    }
    lon_tgt = [0.0, 0.05]
    lat_tgt = [43.29, 43.35]
    xpos, ypos = convert_lon_lat_to_x_y(confproj, lat_tgt, lon_tgt)

    assert isclose(xpos[0], 0)
    assert isclose(xpos[1], 4047.0428104878883)
    assert isclose(ypos[0], 0)
    assert isclose(ypos[1], 6675.229672590271)


def test_convert_lon_lat_2_x_y_mercator_is_conformal():
    # Mercator is conformal: at the reference latitude a small displacement in
    # longitude and the same displacement in latitude must map to equal
    # distances. This fails by a factor log2(e) if the isometric latitude is
    # computed with a logarithm of the wrong base.
    lat0 = 43.29
    confproj = {
        "beta": 0.0,
        "k": 0.0,
        "lat_ori": lat0,
        "lon_ori": 0.0,
        "lat0": lat0,
        "lon0": 0.0,
    }
    # rtol accommodates the second-order term of the finite difference,
    # which is of order tan(lat0) * delta / 2.
    delta = 1.0e-3
    xpos, ypos = convert_lon_lat_to_x_y(confproj, [lat0, lat0 + delta], [0.0, delta])

    assert isclose(ypos[1], xpos[1] / cos(radians(lat0)), rtol=1e-4)


# Reference values below come from SM_XYHAT_S (Méso-NH 6.1.0, mode_gridproj.f90)
# compiled in double precision with XRADIUS = 6371229 m, as
# (LAT0, LON0, BETA, RPK, LATORI, LONORI, lat, lon) -> (x, y).
SM_XYHAT_S_REFERENCE = [
    # Mercator with rotation
    ((43.29, 0.0, 15.0, 0.0, 43.29, 0.0), (43.35, 0.05), (5636.8197404476549, 5400.3249814668763)),
    # Lambert conformal from the south pole (0 < RPK < 1), without and with rotation
    ((45.0, 2.0, 0.0, 0.70710678118654752, 44.5, 1.2), (45.3, 2.4), (94738.519948511129, 88723.987104003834)),
    ((45.0, 2.0, 10.0, 0.70710678118654752, 44.5, 1.2), (45.3, 2.4), (108705.98763014999, 70924.899034257055)),
    # Lambert conformal from the north pole (-1 < RPK < 0), without and with rotation
    ((-33.0, 151.0, 0.0, -0.5446390350150271, -33.5, 150.5), (-32.8, 151.6), (102447.29528285678, 77790.251334401960)),
    ((-33.0, 151.0, -5.0, -0.5446390350150271, -33.5, 150.5), (-32.8, 151.6), (95277.585261044604, 86423.106055421606)),
    # polar-stereographic from the south pole (RPK = 1) and from the north pole (RPK = -1)
    ((80.0, -45.0, 0.0, 1.0, 78.0, -50.0), (81.0, -40.0), (202580.30391793877, 332607.01753211052)),
    ((-80.0, 120.0, 0.0, -1.0, -78.0, 115.0), (-81.0, 125.0), (202580.30391793877, -332607.01753211052)),
    # longitude wrapping across the antimeridian, Lambert and Mercator
    ((45.0, 179.0, 0.0, 0.70710678118654752, 44.5, 178.0), (45.3, -179.5), (196633.69065041355, 89556.516492208905)),
    ((45.0, 179.0, 0.0, 0.0, 44.5, 178.0), (45.3, -179.5), (196573.78207777632, 88806.435552757520)),
]


def make_confproj(lat0, lon0, beta, rpk, lat_ori, lon_ori):
    return {"beta": beta, "k": rpk, "lat_ori": lat_ori, "lon_ori": lon_ori, "lat0": lat0, "lon0": lon0}


@pytest.mark.parametrize("projection, point, expected", SM_XYHAT_S_REFERENCE)
def test_convert_lon_lat_2_x_y_matches_sm_xyhat_s(projection, point, expected):
    confproj = make_confproj(*projection)
    lat, lon = point
    xpos, ypos = convert_lon_lat_to_x_y(confproj, [lat], [lon])

    assert isclose(xpos[0], expected[0], rtol=0, atol=1e-6)
    assert isclose(ypos[0], expected[1], rtol=0, atol=1e-6)


@pytest.mark.parametrize("projection", [projection for projection, _, _ in SM_XYHAT_S_REFERENCE])
def test_convert_lon_lat_2_x_y_origin_maps_to_zero(projection):
    # (LONORI, LATORI) is by definition the geographical position of the x = 0, y = 0 point
    confproj = make_confproj(*projection)
    xpos, ypos = convert_lon_lat_to_x_y(confproj, [confproj["lat_ori"]], [confproj["lon_ori"]])

    assert isclose(xpos[0], 0.0, atol=1e-6)
    assert isclose(ypos[0], 0.0, atol=1e-6)


def test_convert_lon_lat_2_x_y_is_vectorized():
    confproj = make_confproj(45.0, 2.0, 10.0, 0.70710678118654752, 44.5, 1.2)
    lat = [44.5, 45.3, 45.3]
    lon = [1.2, 2.4, 1.2]
    xpos, ypos = convert_lon_lat_to_x_y(confproj, lat, lon)

    assert xpos.shape == ypos.shape == (3,)
    for i in range(3):
        x_i, y_i = convert_lon_lat_to_x_y(confproj, [lat[i]], [lon[i]])
        assert xpos[i] == x_i[0]
        assert ypos[i] == y_i[0]


def test_convert_lon_lat_2_x_y_rejects_invalid_rpk():
    confproj = make_confproj(45.0, 2.0, 0.0, 1.5, 44.5, 1.2)
    with pytest.raises(ValueError, match="RPK = 1.5"):
        convert_lon_lat_to_x_y(confproj, [45.0], [2.0])

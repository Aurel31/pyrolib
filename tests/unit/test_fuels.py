""" unit tests fuels.py functions
"""

import pytest

import pyrolib.fuels as pl

"""
Parameter
"""
def test_property_init():
    fuelproperty = pl.FuelProperty("test", 0., "-", "none", propertyindex=None)
    assert fuelproperty.name == "test"
    assert fuelproperty.value == 0.
    assert fuelproperty.unit == "-"
    assert fuelproperty.description == "none"
    assert fuelproperty.propertyindex == None


def test_property_set():
    fuelproperty = pl.FuelProperty("test", 0., "-", "none", propertyindex=None)
    fuelproperty.set(1.)
    assert fuelproperty.value == 1.


def test_property_show(capsys):
    fuelproperty = pl.FuelProperty("test", 0., "-", "none", propertyindex=None)
    fuelproperty.show()
    captured = capsys.readouterr()
    assert captured.out == "Property    test = 0.000e+00 [-     ] as none\n"


def test_property_minimal_dict():
    fuelproperty = pl.FuelProperty("test", 0., "-", "none", propertyindex=None)
    mdict = fuelproperty.minimal_dict()
    assert mdict["description"] == "none"
    assert mdict["unit"] == "-"
    assert mdict["value"] == 0.


"""
Balbi Fuel
"""

@pytest.mark.parametrize("property,default_value,property_index",
    [("rhod", 400, 1),     ("rhol", 400, 2),    ("Md", 0.1, 3),      ("Ml", 1., 4),
    ("sd", 5000, 5),       ("sl", 5000, 6),     ("sigmad", 0.95, 7), ("sigmal", 0.05, 8),
    ("e", 1., 9),          ("Ti", 500, 10),     ("Ta", 300., 11),    ("DeltaH", 15.43e6, 12),
    ("Deltah", 2.3e6, 13), ("tau0", 75590, 14), ("stoch", 8.3, 15),  ("rhoa", 1.2, 16),
    ("cp", 1912, 17),      ("cpa", 1004, 18),   ("X0", 0.3, 19),     ("LAI", 4., 20),
    ("r00", 2e-5, 21),     ("wind", 0., None),  ("slope", 0., None),
    ]
)
def test_BalbiFuel_init(property, default_value, property_index):
    fuel = pl.BalbiFuel()
    assert type(getattr(fuel, property)).__name__ == "FuelProperty"
    assert getattr(fuel, property).name == property
    assert getattr(fuel, property).value == default_value
    print(getattr(fuel, property).propertyindex)
    assert getattr(fuel, property).propertyindex == property_index


def test_BalbiFuel_value_change():
    fuel = pl.BalbiFuel(e=2.)
    assert fuel.e.value == 2.


def test_BalbiFuel_copy():
    fuel = pl.BalbiFuel()
    fuel2 = pl.BalbiFuel(e=2.)
    assert fuel.e.value == 1.
    assert fuel2.e.value == 2.


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


"""
Scenario
"""

def test_scenario_init():
    scenario = pl.Scenario()
    assert scenario.name == "Scenario"
    assert scenario.longname == "Scenario"
    assert scenario.infos == ""

def test_scenario_add_fuels():
    scenario = pl.Scenario()
    fuel1 = pl.BalbiFuel()
    fuel2 = pl.BalbiFuel(e=2.)
    scenario.add_fuels(fuel1, fuel2)
    assert scenario.fuels["BalbiFuel1"] == fuel1
    assert scenario.fuels["BalbiFuel2"] == fuel2

@pytest.mark.parametrize("filename",
    ["FireFluxI", "DefaultSA", "FireFluxI.yml", "DefaultSA.yml"]
)
def test_load_default_scenario(filename):
    pl.Scenario(load=filename)


def test_load_unknown_scenario():
    with pytest.raises(FileNotFoundError):
        pl.Scenario(load="MaxVerstappenWorldTitle")


@pytest.mark.parametrize("filename,iscompact",
    [("test", True), ("test", False), ("test.yml", True), ("test.yml", False)]
)
def test_save_scenario(tmpdir, filename, iscompact):
    S1 = pl.Scenario(load="FireFluxI")
    pathreal = tmpdir.ensure("test.yml")
    path = tmpdir.join(filename)
    S1.save(path.strpath, compact=iscompact)

    assert pathreal.readlines(cr=1)[0] == "Name: FireFlux\n"
    check_str = f"isCompact: {str(iscompact).lower()}\n"
    assert pathreal.readlines(cr=1)[3] == check_str


def test_scenario_getR():
    scenario = pl.Scenario()
    fuel1 = pl.BalbiFuel()
    fuel2 = pl.BalbiFuel(e=2.)
    scenario.add_fuels(fuel1, fuel2)
    ros = scenario.getR()
    assert ros['BalbiFuel1'] == 0.387354022265859
    assert ros['BalbiFuel2'] == 0.774708044531718


def test_scenario_show_verbose_0(capsys):
    scenario = pl.Scenario()
    fuel1 = pl.BalbiFuel()
    scenario.add_fuel(fuel1)
    scenario.show(verbose=0)
    captured = capsys.readouterr()
    assert captured.out == "Fuel index : 1, Fuel class : BalbiFuel\n"


def test_scenario_show_verbose_1(capsys):
    scenario = pl.Scenario()
    fuel1 = pl.BalbiFuel()
    scenario.add_fuel(fuel1)
    scenario.show(verbose=1)
    captured = capsys.readouterr()
    assert captured.out == "Fuel index : 1, Fuel class : BalbiFuel, ROS : 0.39 m/s\n"


def test_show_fuel_classes(capsys):
    default_list = [
        'BalbiFuel',
    ]
    pl.show_fuel_classes()
    captured = capsys.readouterr()
    for fuelclass in default_list:
        assert f"{fuelclass} class is compliant with" in captured.out


def test_show_default_scenario(capsys):
    default_list = [
        'DefaultSA.yml',
        'FireFluxI.yml',
        ]
    pl.show_default_scenario()
    captured = capsys.readouterr()
    for file in captured.out.split('\n')[1:-1]:
        assert f"{file[2:]}.yml" in default_list
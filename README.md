![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/Aurel31/pyrolib?style=for-the-badge)
[![GitHub issues](https://img.shields.io/github/issues/Aurel31/pyrolib?style=for-the-badge)](https://github.com/Aurel31/pyrolib/issues)
[![GitHub license](https://img.shields.io/github/license/Aurel31/pyrolib?style=for-the-badge)](https://github.com/Aurel31/pyrolib/blob/main/LICENSE)

# `pyrolib`


`pyrolib` is a tool library for `Méso-NH/Blaze` model.
`pyrolib` provides python tools for the following purposes:

- Generation of the `FuelMap.nc` file by using a `Méso-NH` namelist and the initialisation file of a `Méso-NH/Blaze` run.
- FireFlux I exeprimental fire data processing.
- Development of numerical methods for the `Blaze fire model`.


## Installation

Install `pyrolib` from PyPI's:

```bash
pip install pyrolib
```

## Usage

`pyrolib` is separated into several sub-libraries for each of the objectives mentioned above, respectively:

- `pyrolib.fuelmap`
- `pyrolib.firefluxpost`
- `pyrolib.blaze`

### Fuel database

`pyrolib` relies on a fuel container object called a `FuelDatabase`.
A `FuelDatabase` is a 2 level nested dictionary-like class. The first level corresponds to an explicit fuel name (like "tall_grass"). This fuel can be described by several methods that are related to a rate of spread model (for example `Rothermel` or `Balbi`). Each description is relatde to a `Fuel class` (`RothermelFuel` or `BalbiFuel`) are constitute the second level of the database.

The
 `FireFluxI` `FuelDatabase` contains for example the following:
```
* FireFluxI
    < tall_grass > available for:
      - BalbiFuel fuel class
```

The list of `FuelDatabase` contained in `pyrolib` can be accessed through the cli `pyrolib-fm list-fuel-databases`.

A user database can be saved in a `.yml` file. See example `examples/fuel_database`.
## How to
### generate the `FuelMap.nc` file

The objective of this part is to easily create a fuel file for a `Méso-NH/Blaze` run.
This file is always named `FuelMap.nc`. It needs to contain a 2D map on the fire grid for the following fields :

- fuel type,
- every fuel property that are compliant with the selected rate of spead parameterization in the `Méso-NH/Blaze` namelist,
- ignition time,
- walking ignition time.

`pyrolib.fuelmap` provides tools for the generation of every `Fuelmap.nc` component.
Some `Méso-NH` files are needed to complete the process. A typical `Méso-NH` run directory should look like

```
run_MNH/
├─ EXSEG1.nam
├─ Init_file.des
├─ Init_file.nc
```

Some `Méso-NH` files are included in the example directory to run examples.

`simplecase.py` example provides basic steps to create a fuel map using `pyrolib` tools.
Some operations can be accelerated with `numba`. `pyrolib` can check if `numba` is installed in your environment. If not, `pyrolib` will show a warning message.
In this example, the `Méso-NH` domain is $(Nx, Ny) = (20, 20)$ with $\Delta_x = \Delta_y = 25$m. The fire mesh is refined with $\Gamma_x = \Gamma_y = 5$.
The goal of this example is to set:
- a rectangle burnable area defined by $50 \leqslant x \leqslant 450$ and $50 \leqslant y \leqslant 450$,
- an ignition patch is set at $t = 10$s with $100 \leqslant x \leqslant 105$ and $245 \leqslant y \leqslant 255$.

As the rate of spread model defined in the `Méso-NH` namelist, the `BalbiFuel` class shall be used to define the fuel properties.

```python
"""simplecase.py

Use an existing fuel database and create a simple fuelmap
"""
from pyrolib.fuelmap import FuelDatabase, FuelMap

# create fuel db
my_db = FuelDatabase()

# load existing database
my_db.load_fuel_database("FireFluxI")

# create a FuelMap
my_fuelmap = FuelMap(fuel_db=my_db)

# add a fuel patch of the tall grass fuel from the FireFluxI database
## to show the available fuel keys of the database, use print(my_db)
my_fuelmap.add_fuel_rectangle_patch(xpos=[50, 450], ypos=[50, 450], fuel_key="FireFluxI_tall_grass")

# add a ignition patch
my_fuelmap.add_ignition_rectangle_patch(xpos=[100, 105], ypos=[245, 255], ignition_time=10)

# dump for mesonh
my_fuelmap.dump_mesonh()
```

After running the script, the directory should contains:
```
example/
├─ EXSEG1.nam
├─ FuelMap.des
├─ FuelMap.nc
├─ FuelMap2d.nc
├─ Init_file.des
├─ Init_file.nc
├─ simplecase.py
```

`FuelMap2d.nc` is an optional file that is easier for human to chack if the generated fuel map respects the requirements.

### Create a fuel object

`pyrolib` contains several fuel objects that represent a fuel description as fuel properties. To show the list of available fuel object, use `show_fuel_classes`. The following example shows several methods to create a `BalbiFuel` object. Properties can be either modified in the constructor or set as default.

```python
import pyrolib.fuels as pl

# print fuel classes available and default property values
pl.show_fuel_classes()

# create default fuel
fuel1 = pl.BalbiFuel()

# create default fuel and changes some properties
fuel2 = pl.BalbiFuel(e=2., Md=0.15)

# copy fuel2 and changes some properties
fuel3 = fuel2.copy(DeltaH=20e7, LAI=2)

# change property value after creation
fuel1.Ml.set(0.9)
```

## `Méso-NH` compliance

The current version of `pyrolib` is compliant with `Méso-NH` from version `5.4.4` to version `5.5.0`.
## Acknowledgements

This library is part of the `ANR FireCaster` project (2017-2021, `ANR-16-CE04-0006, FIRECASTER`).

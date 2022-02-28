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

- `pyrolib.fuels`
- `pyrolib.firefluxpost`
- `pyrolib.blaze`

## How to

### `FuelMap.nc` file generation

The objective of this part is to easily create a fuel file for a `Méso-NH/Blaze` run.
This file is always named `FuelMap.nc`. It needs to contain a 2D map on the fire grid for the following fields :

- fuel type,
- every fuel property that are compliant with the selected rate of spead parameterization in the `Méso-NH/Blaze` namelist,
- ignition time,
- walking ignition time.

`pyrolib.fuels` provides tools for the generation of every `Fuelmap.nc` component.
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
"""
import pyrolib.fuels as pl

# create default Balbi fuel
fuel1 = pl.BalbiFuel()

# create a scenario to store fuel
scenario = pl.Scenario(
    name='test',
    longname='test scenario',
    infos='This is a test scenario',
    )
scenario.add_fuel(fuel1)

# Create FuelMap
fuelmap = pl.FuelMap(scenario=scenario)

# add fuel patch and ignition patch
fuelmap.addRectanglePatch(xpos=[50, 450], ypos=[50, 450], fuelindex=1)
fuelmap.addRectanglePatch(xpos=[100, 105], ypos=[245, 255], ignitiontime=10)

# write FuelMap.nc file and create FuelMap.des
fuelmap.write(save2dfile=True)
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
### Manage scenario

`pyrolib` relies on a fuel container object called a `scenario`.
It can contains several `fuels` type objects, that can be stored in `.yml` files and retrieved from `.yml` files.
If no filepath is given to `save` method, it saves the scenario locally with its own name `scenario.name`.
Several scenrio are already available in the library database.
To show the list of available scenario, use `show_default_scenario` function.

Load a scenario file by using `load` argument with the filename in the constructor.
The filename can be either a local file or a default file present in the `pyrolib` database.

```python
import pyrolib.fuels as pl

# verbose level
# 0: only fuel name
# 1: name + ROS
# 2: name + ROS + every property value
verbose_level = 2

# create some fuels
fuel1 = pl.BalbiFuel()
fuel2 = pl.BalbiFuel(e=2., Md=0.15)

# create a scenario
scenario = pl.Scenario(
    name='scenario',
    longname='testscenario',
    infos='This is a test scenario'
    )

# add fuels to scenario
scenario.add_fuels(fuel1, fuel2)

# show fuels and no wind/no slope ROS contained in the scenario
scenario.show(verbose=verbose_level)

# save scenario in yml file
scenario.save()

# Create a scenario from existing local file (scenario.yml)
new_scenario = pl.Scenario(load='scenario')
new_scenario.show(verbose=verbose_level)

# Show available default scenario
pl.show_default_scenario()

# Create a scenario from a default file
scenario_from_default = pl.Scenario(load='FireFluxI')
scenario_from_default.show(verbose=verbose_level)
```

## `Méso-NH` compliance

The current version of `pyrolib` is compliant with `Méso-NH` from version `5.4.4` to version `5.5.0`.
## Acknowledgements

This library is part of the `ANR FireCaster` project (2017-2021, `ANR-16-CE04-0006, FIRECASTER`).

# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).


## [Unreleased]
### Bug fix
- `convert_lon_lat_to_x_y` used a base-2 logarithm instead of the natural one, so
  patches positioned in lon/lat were placed off by a factor `log2(e)` on the `y`
  axis.

## [0.5.0] 2026 / 08 / 12
**Warning**: the default `Méso-NH` version is now `6.1.0`. Runs targeting `5.6.0`
must pass `MesoNHversion="5.6.0"` explicitly to `FuelMap`.

### Added
- support for `Méso-NH` `6.1.0` (`v610` entry in `Default_MNH_namelist.yml`).
  The `FuelMap.nc` format itself is unchanged: `FIRE_READFUEL` in `Méso-NH` `6.1.0`
  reads the same field names, units and property order.
- `numba` is now declared as an optional extra (`pip install pyrolib[numba]`).

### Changed
- packaging moved from `setup.py`/`setup.cfg` to `pyproject.toml` (PEP 621).
- Python `3.10` to `3.13` are supported; `3.8` and `3.9` are dropped.
- the `numpy < 2.0`, `netCDF4 < 2.0` and `scipy < 2.0` ceilings are lifted;
  `pyrolib` works with `numpy` 2.x.
- documentation build modernised: `myst-parser` replaces the archived
  `recommonmark`, and `.readthedocs.yaml` uses the current `build.os` schema.
- default `Méso-NH` version is `6.1.0`.

### Removed
- `scipy` dependency (it was never imported).
- `bresenham` dependency, inlined into `pyrolib.fuelmap.patch` (MIT, Petr Viktorin).

### Bug fix
- fire mesh size is no longer truncated to whole metres (the array holding it was
  of integer dtype).
- the fire mesh size on the y axis used the x refinement ratio `nrefinx`
  instead of `nrefiny`.
- `FireFluxI` thermocouple failure masking used `and` between two arrays, which
  raised `ValueError: truth value of an array ... is ambiguous`.

## [0.4.1] 2022 / 09 / 21
### Changed
- Default version is 5.6.0
- The following Balze variables are renamed:
  - LSPHI -> FMPHI
  - FIRERW -> FMROS
  - FMR0 -> FMROS0
  - BMAP -> FMBMAP

## [0.4.0] 2022 / 09 / 13
**Warning**: Backward compatibility with MesoNH version < 5.6 is not guaranteed anymore.

### Changed
- change units nomenclature in fuel database
- comply to MesoNH 5.6.0 file conventions
- namelist for Blaze is now called nam_firen

## [0.3.1] 2022 / 09 / 13
### Changed
- import fuelmap instead of fuels for fuel_classes example

## [0.3.0] 2022 / 06 / 28

### Added
- conformal projection utility for Mercator without rotation
- tests for conformal projection utility
### Changed
- attributes of FuelMap.nc updated to be compliant with MesoNH 5.5.0 reader.
## [0.2.3] 2022 / 06 / 21

### Doc
- upload documentation on ReadTheDocs

## [0.2.2] 2022 / 05 / 15

### Bug fix
- key `Fuels` is replaced by `fuels` in `dump fuel database` method for `FuelDatabase`class

## [0.2.1] 2022 / 05 / 09

### Changed
- cli imports changed to improve efficiency

## [0.2.0] 2022 / 05 / 05

### Added
- `FuelDatabase` class to replace the `Scenario` class
- Fuel descriptor is used to access fuel in the database instead of index
- cli for fuelmap (list fuel databases and fuel classes)
- cli for postprocessing (rearrange netcdf file to store fire fields in 2D instead of 3D)
### Changed
- all add_patch functions have been splitted into more explicit functions.
  For example: `addRectanglePatch` has been splitted to `add_fuel_rectangle_patch`, `add_unburnable_rectangle_patch`, and `add_ignition_rectangle_patch`.
- Update examples
- use __str__ instead of show methods for `FuelProperty` and `BaseFuel`.
### Deleted
- `Scenario` class is not used anymore

## [0.1.2] 2022 / 03 / 02

### Added
- Create FuelMap from another directory = specify workdir.
- test for fuelmap generation

### Changed
- Improve quandrant case identifier handling
- use int instead of deprecated np.int
- use black to improuve lint score

## [0.1.1] 2022 / 02 / 28

### Added
- python 3.10

### Changed
- fix url for Pypi

## [0.1.0] 2022 / 02 / 28

### Added
- reorganise `data` directory.
- `show_default_scenario` function to print available scenario files in the `data/scenario` directory.
- `show_fuel_classes` function to print every fuel classes and display fuel properties for each classe.
- `simplecase.py`, `fuel_classes.py`, `scenario.py` examples.
- tests for `show_fuel_classes` and `show_default_scenario`.
- add `Default_MNH_namelist.yml` file to store default values of `Méso-NH` namelist.

## [0.0.1] 2022 / 02 / 28

### Added
- unit tests for fuel management tools
- unit tests for blaze fire model development tools
- function tests for blaze fire model development tools

## [0.0.0] 2022 / 02 / 24

### Added

- Create FuelMap.nc file for Meso-NH/Blaze model for Balbi's rate of spread parameterization
- FireFlux I raw data processing tools
- Blaze fire model python development tools for sub-grid burning area
# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.3.0] To be released

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
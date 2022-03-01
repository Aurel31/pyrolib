# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
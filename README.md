![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/Aurel31/pyrolib?style=for-the-badge)
[![GitHub issues](https://img.shields.io/github/issues/Aurel31/pyrolib?style=for-the-badge)](https://github.com/Aurel31/pyrolib/issues)
[![Documentation Status](https://readthedocs.org/projects/pyrolib/badge/?version=latest)](https://pyrolib.readthedocs.io/en/latest/?badge=latest)
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

## `Méso-NH` compliance

The current version of `pyrolib` is compliant with `Méso-NH` from version `5.4.4` to version `5.5.0`.
## Acknowledgements

This library is part of the `ANR FireCaster` project (2017-2021, `ANR-16-CE04-0006, FIRECASTER`).

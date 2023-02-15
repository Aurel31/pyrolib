# Use cli of `pyrolib`

A Command Line Interface (cli) has been implemented in `pyrolib` in order to have an easy access to some features.
The `pyrolib` cli is splitted in two parts:
- `pyrolib-fm`: fuelmap cli
- `pyrolib-post`: post processing cli

## cli for fuelmap generation

The functions for fuel map generation is grouped in the cli `pyrolib-fm`.
To get some help on the cli, use `pyrolib-fm --help`.

```
> pyrolib-fm --help
Usage: pyrolib-fm [OPTIONS] COMMAND [ARGS]...

  Package pyrolib v0.4.0

  * cli of pyrolib package for fuelmap *

Options:
  --help  Show this message and exit.

Commands:
  list-fuel-classes    List fuel classes available in pyrolib and default...
  list-fuel-databases  List fuel databases available in pyrolib
```

### List fuel classes

```
> pyrolib-fm list-fuel-classes --help
Usage: pyrolib-fm list-fuel-classes [OPTIONS]

  List fuel classes available in pyrolib and default parameters values

Options:
  -s, --short  do not show fuel classes attributs
  --help       Show this message and exit.
```

Example:
```
> pyrolib-fm list-fuel-classes

More information about fuel classes:
* < BalbiFuel > class is compliant with the Balbi's ROS parameterization.
  It is used when < CPROPAG_MODEL = SANTONI2011 > in the Méso-NH namelist.
It contains the following properties with default value:
BalbiFuel properties:
  Property    rhod = 4.000e+02 [kg m-3] as Dead fuel density
  Property    rhol = 4.000e+02 [kg m-3] as Living fuel density
  Property      Md = 1.000e-01 [-     ] as Dead fuel moisture
  Property      Ml = 1.000e+00 [-     ] as Living fuel moisture
  Property      sd = 5.000e+03 [m-1   ] as Dead SAV ratio
  Property      sl = 5.000e+03 [m-1   ] as Living SAV ratio
  Property  sigmad = 9.500e-01 [kg m-2] as Dead fuel load
  Property  sigmal = 5.000e-02 [kg m-2] as Living fuel load
  Property       e = 1.000e+00 [m     ] as Fuel height
  Property      Ti = 5.000e+02 [K     ] as Ignition temperature
  Property      Ta = 3.000e+02 [K     ] as Air temperature
  Property  DeltaH = 1.543e+07 [J kg-1] as Combustion enthalpy
  Property  Deltah = 2.300e+06 [J kg-1] as Water evaporation enthalpy
  Property    tau0 = 7.559e+04 [s m-1 ] as Model constant
  Property   stoch = 8.300e+00 [-     ] as Stochiometry
  Property    rhoa = 1.200e+00 [kg m-3] as Air density
  Property      cp = 1.912e+03 [J K-1 kg-1] as Fuel calorific capacity
  Property     cpa = 1.004e+03 [J K-1 kg-1] as Air calorific capacity
  Property      X0 = 3.000e-01 [-     ] as Fraction of radiant energy
  Property     LAI = 4.000e+00 [-     ] as Leaf area index
  Property     r00 = 2.000e-05 [-     ] as Model constant
  Property    wind = 0.000e+00 [m s-1 ] as Wind at mid-flame
  Property   slope = 0.000e+00 [deg   ] as Slope
```

### List fuel databases

```
> pyrolib-fm list-fuel-databases --help
Usage: pyrolib-fm list-fuel-databases [OPTIONS]

  List fuel databases available in pyrolib

Options:
  -s, --short  print database content
  --help       Show this message and exit.
```

It will list available databse in `pyrolib` package database but also local databases if found in local directory.

Example:
In this example, we have two databases in `pyrolib` package database called **DefaultSA** and **FireFluxI**. Each database contains only one fuel described by one fuel model (BalbiFuel).
We also have a local database called **ensemble_db** that contains eight fuels described by one fuel model (BalbiFuel).

A short description of fuel models is given at the end, it corresponds to the result of the cli `pyrolib-fm list-fuel-classes -s`.
```
> pyrolib-fm list-fuel-databases
----- pyrolib available database -----
  * DefaultSA
    < default > available for:
      - BalbiFuel fuel class

  * FireFluxI
    < tall_grass > available for:
      - BalbiFuel fuel class

------ local available database ------
  * ensemble_db
    < Ensemble_0 > available for:
      - BalbiFuel fuel class
    < Ensemble_1 > available for:
      - BalbiFuel fuel class
    < Ensemble_2 > available for:
      - BalbiFuel fuel class
    < Ensemble_3 > available for:
      - BalbiFuel fuel class
    < Ensemble_4 > available for:
      - BalbiFuel fuel class
    < Ensemble_5 > available for:
      - BalbiFuel fuel class
    < Ensemble_6 > available for:
      - BalbiFuel fuel class
    < Ensemble_7 > available for:
      - BalbiFuel fuel class
    < FireFluxI_tall_grass > available for:
      - BalbiFuel fuel class

--------------------------------------

More information about fuel classes:
* < BalbiFuel > class is compliant with the Balbi's ROS parameterization.
  It is used when < CPROPAG_MODEL = SANTONI2011 > in the Méso-NH namelist.
```

The short version is available with the option `-s`.
```
> pyrolib-fm list-fuel-databases -s
----- pyrolib available database -----
  * DefaultSA
  * FireFluxI
------ local available database ------
  * ensemble_db
--------------------------------------
```

## cli for post processing

The functions for post processing is grouped in the cli `pyrolib-post`.
To get some help on the cli, use `pyrolib-post --help`.

```
> pyrolib-post --help
Usage: pyrolib-post [OPTIONS] COMMAND [ARGS]...

  Package pyrolib v0.4.0

  * cli of pyrolib package for post processing *

Options:
  --help  Show this message and exit.

Commands:
  rearrange-netcdf  Rearrange netcdf with fire fields
```

### Rearrange netcdf

`Meso-NH` will store fire fields (like level-set, rate of spread, heat fluxes) is a 3D format of size ($Nx$, $Ny$, $\Gamma_x * \Gamma_y$) to be compliant with I/O rules. However, they are 2D fields and we want to put them back in a 2D format of size ($Nx * \Gamma_x$, $Ny * \Gamma_y$) in output files.
This cli allows to copy a netcdf files that contains fire fields and rearrange them in 2D format and conserve every other fields inthe output file. If we do not want to use the old file anymore, the option `-r` can be used to remove the old file.
The new file will be named with a suffix `-post.nc`.
A list of files can be given as argument (for example `*.nc`).

```
> pyrolib-post rearrange-netcdf --help
Usage: pyrolib-post rearrange-netcdf [OPTIONS] [FILES]...

  Rearrange netcdf with fire fields

Options:
  -r, --remove  remove original file
  --help        Show this message and exit.
```

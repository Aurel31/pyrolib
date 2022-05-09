""" CLI utilities
"""

import os

import click
import numpy as np
from netCDF4 import Dataset

from pyrolib import __name__ as pyrolib_name
from pyrolib import __version__ as pyrolib_version
from pyrolib.fuelmap.utility import fire_array_3d_to_2d


def add_version(f):
    """
    Add the version of the tool to the help heading.
    :param f: function to decorate
    :return: decorated function
    """
    doc = f.__doc__
    f.__doc__ = (
        "Package " + pyrolib_name + " v" + pyrolib_version + "\n\n" + doc
    )

    return f


@click.group()
@add_version
def main_cli():
    """
    * cli of pyrolib package for post processing *
    """
    pass


@click.command()
@click.argument("files", nargs=-1)
@click.option(
    "-r",
    "--remove",
    is_flag=True,
    default=False,
    help='remove original file'
)
def rearrange_netcdf(files, remove):
    """Rearrange netcdf with fire fields"""
    for file in files:
        if file.endswith(".nc"):
            print(f"> rearrange {file}")
            new_filename = file.replace(".nc", "") + "-post.nc"
            with Dataset(file, "r") as src, Dataset(f"{new_filename}", "w") as dst:
                # copy attributes
                for name in src.ncattrs():
                    dst.setncattr(name, src.getncattr(name))
                # copy dimensions
                for name, dimension in src.dimensions.items():
                    dst.createDimension(
                        name, (len(dimension) if not dimension.isunlimited() else None)
                    )
                # compute fire grid
                grid_u_x = src.variables["ni_u"]
                grid_v_y = src.variables["nj_v"]
                need_fire_grid = False
                ref_fire_field = None
                # search for at least one fire field
                for fire_field in LIST_FIRE_FIELD:
                    if fire_field in src.variables.keys():
                        # match with one fire field
                        need_fire_grid = True
                        ref_fire_field = fire_field

                if need_fire_grid:
                    # get fire grid refinement ratio (parse comment of ref_fire_field)
                    gamma_x = int(
                        src.variables[ref_fire_field]
                        .comment.split("fire grid (")[-1]
                        .split(",")[0]
                    )
                    gamma_y = int(
                        src.variables[ref_fire_field]
                        .comment.split("fire grid (")[-1]
                        .split(",")[1]
                        .replace(")", "")
                    )
                    # fire grid size
                    Lmax = gamma_x * len(grid_u_x)
                    Mmax = gamma_y * len(grid_v_y)
                    # fire grid
                    XFire = np.linspace(
                        grid_u_x[0],
                        grid_u_x[-1] + (grid_u_x[1] - grid_u_x[0]),
                        Lmax,
                        endpoint=False,
                    )
                    XFire += 0.5 * (XFire[1] - XFire[0])
                    YFire = np.linspace(
                        grid_v_y[0],
                        grid_v_y[-1] + (grid_v_y[1] - grid_v_y[0]),
                        Mmax,
                        endpoint=False,
                    )
                    YFire += 0.5 * (YFire[1] - YFire[0])
                    # add fire dimensions
                    dst.createDimension("xfire", Lmax)
                    dst.createDimension("yfire", Mmax)
                    # add fire grid variables
                    nf = dst.createVariable("xfire", np.float64, ("xfire"))
                    nf.long_name = "x-dimension fire grid"
                    nf.standard_name = "x coordinates fire grid"
                    nf.units = "m"
                    nf.axis = "xfire"
                    nf[:] = XFire[:]

                    nf = dst.createVariable("yfire", np.float64, ("yfire"))
                    nf.long_name = "y-dimension fire grid"
                    nf.standard_name = "y coordinates fire grid"
                    nf.units = "m"
                    nf.axis = "yfire"
                    nf[:] = YFire[:]
                # copy all file data except for the excluded
                for name, variable in src.variables.items():
                    # check fill_value
                    fill_value = (
                        variable.getncattr("_FillValue")
                        if "_FillValue" in vars(variable).keys()
                        else None
                    )
                    if name in LIST_FIRE_FIELD:
                        # fire field
                        dst.createVariable(
                            name,
                            variable.datatype,
                            ("time", "yfire", "xfire"),
                            fill_value=fill_value,
                        )
                        # careful with unlimited time dimension
                        dst.variables[name][0, :, :] = fire_array_3d_to_2d(
                            src.variables[name][0, :, :, :],
                            len(grid_u_x),
                            len(grid_v_y),
                            gamma_x,
                            gamma_y,
                        )
                    else:
                        # atm field
                        dst.createVariable(
                            name,
                            variable.datatype,
                            variable.dimensions,
                            fill_value=fill_value,
                        )
                        dst.variables[name][:] = src.variables[name][:]

                    # copy variable attributes all at once via dictionary
                    for key, value in vars(variable).items():
                        if key not in ["_FillValue"]:
                            dst.variables[name].setncattr(key, value)

            # remove source file if needed
            if remove:
                os.remove(file)
                print(f">> {file} removed")
        else:
            print(f"< {file} > unknown file format. Ignored")
            continue


main_cli.add_command(rearrange_netcdf)

LIST_FIRE_FIELD = [
    "LSPHI",
    "BMAP",
    "FMR0",
    "FIRERW",
    "FMASE",
    "FMAWC",
    "FMFLUXHDH",
    "FMFLUXHDW",
    "FMWINDU",
    "FMWINDV",
    "FMGRADRHOX",
    "FMGRADRHOY",
]

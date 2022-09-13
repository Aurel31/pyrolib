""" CLI utilities
"""

import os

import click
import pkg_resources
import yaml

from pyrolib import __name__ as pyrolib_name
from pyrolib import __version__ as pyrolib_version

from .fuelmap.fuels import show_fuel_classes


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
    * cli of pyrolib package for fuelmap *
    """
    pass


@click.command()
@click.option(
    "-s", "--short", is_flag=True, default=True, help="print database content"
)
def list_fuel_databases(short):
    """List fuel databases available in pyrolib"""
    data_dir_content = pkg_resources.resource_listdir("pyrolib", "data/fuel_db")
    data_dir_content.sort()
    print("----- pyrolib available database -----")
    for file in data_dir_content:
        if file.endswith(".yml"):
            print(f"  * {file.replace('.yml','')}")
            if short:
                # print db fuels
                defaultpath = pkg_resources.resource_stream(
                    "pyrolib", "/".join(("data/fuel_db", file))
                )
                with open(defaultpath.name, "r") as ymlfile:
                    alldata = yaml.safe_load(ymlfile)
                for fuel_description in alldata["fuels"].keys():
                    print(f"    < {fuel_description} > available for:")
                    for fuel_class in alldata["fuels"][fuel_description].keys():
                        fuel_class = alldata["fuels"][fuel_description][fuel_class][
                            "class"
                        ]
                        print(f"      - {fuel_class} fuel class")
                print()

    print("------ local available database ------")
    data_dir_content = os.listdir()
    data_dir_content.sort()
    for file in data_dir_content:
        if file.endswith(".yml"):
            # load file
            with open(file, "r") as ymlfile:
                alldata = yaml.safe_load(ymlfile)
            # check if is_compact, infos, and fuels are in keys
            if (
                "is_compact" in alldata.keys()
                and "infos" in alldata.keys()
                and "fuels" in alldata.keys()
            ):
                print(f"  * {file.replace('.yml','')}")
                if short:
                    # print db fuels
                    for fuel_description in alldata["fuels"].keys():
                        print(f"    < {fuel_description} > available for:")
                        for fuel_class in alldata["fuels"][fuel_description].keys():
                            fuel_class = alldata["fuels"][fuel_description][fuel_class][
                                "class"
                            ]
                            print(f"      - {fuel_class} fuel class")
                    print()
    print("--------------------------------------")
    if short:
        show_fuel_classes(show_fuel_properties=False)
    else:
        print()


main_cli.add_command(list_fuel_databases)


@click.command()
@click.option(
    "-s", "--short", is_flag=True, default=False, help="do not show fuel classes attributs"
)
def list_fuel_classes(short):
    """List fuel classes available in pyrolib and default parameters values"""
    show_fuel_classes(show_fuel_properties=not short)


main_cli.add_command(list_fuel_classes)

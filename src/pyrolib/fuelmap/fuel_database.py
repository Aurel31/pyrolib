""" Fuel Database utilities
"""

import os
import sys
import errno

import pkg_resources
import yaml

from .fuels import(
    BalbiFuel,
    show_fuel_classes,
)

def load_fuel_database(filename):
    """load a fuel database in the current fuel database

    The database can be search in the package data/fuel_database or locally

    Args:
        filename (str): name of the database (database.yml)
    """
    # check file name
    if filename.endswith(".yml"):
        fname = filename
        db_name = filename.replace('.yml','')
    else:
        fname = filename + ".yml"
        db_name = filename

    # Check default case
    try:
        defaultpath = pkg_resources.resource_stream("pyrolib", "/".join(("data/fuel_db", fname)))
        defaultexists = os.path.exists(defaultpath.name)
    except:
        defaultexists = False

    # Check local path
    localexists = os.path.exists(fname)

    # Select path
    if defaultexists:
        if localexists:
            print(f"INFO : pyrolib fuel database and local fuel database found with same name <{fname}>\nLocal fuel database loaded")
            FilePath = fname
        else:
            print(f"INFO : pyrolib fuel database <{fname}> loaded")
            FilePath = defaultpath.name
    else:
        if localexists:
            print(f"INFO : Local fuel database <{fname}> loaded")
            FilePath = fname
        else:
            print(f"ERROR : database <{fname}> not found in pyrolib fuel database directory nor local directory")
            FilePath = fname
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), fname)

    # load new fuels
    with open(FilePath, "r") as ymlfile:
        alldata = yaml.safe_load(ymlfile)
        if ("fuels" in alldata.keys() and "is_compact" in alldata.keys()):
            if alldata["is_compact"]:
                # read in compact mode
                for fuel_description in alldata["fuels"].keys():
                    fuel_db_key = f"{db_name}_{fuel_description}"
                    fuel_dict = {}
                    for fuel in alldata["fuels"][fuel_description].keys():
                        # add a new fuel object to the fuel dict
                        fuel_dict[fuel] = getattr(
                            sys.modules[__name__],
                            alldata["fuels"][fuel_description][fuel]["class"]
                            )(
                            **alldata["fuels"][fuel_description][fuel]["properties"]
                        )

                    # add the fuel dict to the current db
                    current_fuel_db[fuel_db_key] = fuel_dict
            else:
                # read in non compact mode
                for fuel_description in alldata["fuels"].keys():
                    fuel_db_key = f"{db_name}_{fuel_description}"
                    fuel_dict = {}
                    for fuel in alldata["fuels"][fuel_description].keys():
                        # need to reconstruct properties dictionnary
                        propertiesdict = {}
                        for prop in alldata["fuels"][fuel_description][fuel]["properties"].keys():
                            propertiesdict[prop] = alldata["fuels"][fuel_description][fuel]["properties"][prop]["Value"]

                        # add a new fuel object to the fuel dict
                        fuel_dict[fuel] = getattr(
                            sys.modules[__name__],
                            alldata["fuels"][fuel_description][fuel]["class"]
                            )(
                            **propertiesdict
                        )

                    # add the fuel dict to the current db
                    current_fuel_db[fuel_db_key] = fuel_dict
        else:
            print("ERROR : cannot find fuels or compacity variable: <is_compact> in file. Reading stopped.")

    print(current_fuel_db)


def dump_current_fuel_database(filename, info, compact=True):
    """save the current fuel database in a yml file.

    Args:
        filename (str): name of the database (database.yml)
        info (str): information about the database
        compact (bool, optional): writting format. Defaults to True.
    """
    pass


def list_avail_fuel_database(show_db_content=True):
    """List every scenario file in data/scenario directory
    """
    data_dir_content = pkg_resources.resource_listdir("pyrolib", "data/fuel_db")
    data_dir_content.sort()
    print("----- pyrolib available database -----")
    for file in data_dir_content:
        if file.endswith(".yml"):
            print(f"  * {file.replace('.yml','')}")
            if show_db_content:
                # print db fuels
                defaultpath = pkg_resources.resource_stream("pyrolib", "/".join(("data/fuel_db", file)))
                with open(defaultpath.name, "r") as ymlfile:
                    alldata = yaml.safe_load(ymlfile)
                for fuel_description in alldata['fuels'].keys():
                    print(f"    < {fuel_description} > available for:")
                    for fuel_class in alldata['fuels'][fuel_description].keys():
                        fuel_class = alldata['fuels'][fuel_description][fuel_class]["class"]
                        print(f"      - {fuel_class} fuel class")
            print("\n")

    print("------ local available database -----")
    data_dir_content = os.listdir()
    data_dir_content.sort()
    for file in data_dir_content:
        if file.endswith(".yml"):
            # load file
            with open(file, "r") as ymlfile:
                    alldata = yaml.safe_load(ymlfile)
            # check if is_compact, infos, and fuels are in keys
            if ("is_compact" in alldata.keys() and
                "infos" in alldata.keys() and
                "fuels" in alldata.keys()
                ):
                print(f"  * {file.replace('.yml','')}")
                if show_db_content:
                    # print db fuels
                    for fuel_description in alldata['fuels'].keys():
                        print(f"    < {fuel_description} > available for:")
                        for fuel_class in alldata['fuels'][fuel_description].keys():
                            fuel_class = alldata['fuels'][fuel_description][fuel_class]["class"]
                            print(f"      - {fuel_class} fuel class")
                print("\n")
    print("-------------------------------------")
    show_fuel_classes(show_fuel_properties=False)


def show_current_fuel_database():
    """
    """
    pass

current_fuel_db = {}
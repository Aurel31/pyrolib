""" Fuel Database utilities
"""

import os
import sys
import errno

import pkg_resources
import yaml

from .fuels import (
    BalbiFuel,
)


class FuelDatabase:
    def __init__(self):
        self.fuels = {}

    def load_fuel_database(self, filename):
        """load a fuel database in the current fuel database

        The database can be search in the package data/fuel_database or locally

        Args:
            filename (str): name of the database (database.yml)
        """
        # check file name
        if filename.endswith(".yml"):
            fname = filename
            db_name = filename.replace(".yml", "")
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
                print(
                    f"INFO : pyrolib fuel database and local fuel database found with same name <{fname}>\nLocal fuel database loaded"
                )
                FilePath = fname
            else:
                print(f"INFO : pyrolib fuel database <{fname}> loaded")
                FilePath = defaultpath.name
        else:
            if localexists:
                print(f"INFO : Local fuel database <{fname}> loaded")
                FilePath = fname
            else:
                print(
                    f"ERROR : database <{fname}> not found in pyrolib fuel database directory nor local directory"
                )
                FilePath = fname
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), fname)

        # load new fuels
        with open(FilePath, "r") as ymlfile:
            alldata = yaml.safe_load(ymlfile)
            if "fuels" in alldata.keys() and "is_compact" in alldata.keys():
                if alldata["is_compact"]:
                    # read in compact mode
                    for fuel_description in alldata["fuels"].keys():
                        fuel_db_key = f"{db_name}_{fuel_description}"
                        fuel_dict = {}
                        for fuel in alldata["fuels"][fuel_description].keys():
                            # add a new fuel object to the fuel dict
                            fuel_dict[fuel] = getattr(
                                sys.modules[__name__], alldata["fuels"][fuel_description][fuel]["class"]
                            )(**alldata["fuels"][fuel_description][fuel]["properties"])

                        # add the fuel dict to the current db
                        self.fuels[fuel_db_key] = fuel_dict
                else:
                    # read in non compact mode
                    for fuel_description in alldata["fuels"].keys():
                        fuel_db_key = f"{db_name}_{fuel_description}"
                        fuel_dict = {}
                        for fuel in alldata["fuels"][fuel_description].keys():
                            # need to reconstruct properties dictionnary
                            propertiesdict = {}
                            for prop in alldata["fuels"][fuel_description][fuel]["properties"].keys():
                                propertiesdict[prop] = alldata["fuels"][fuel_description][fuel][
                                    "properties"
                                ][prop]["Value"]

                            # add a new fuel object to the fuel dict
                            fuel_dict[fuel] = getattr(
                                sys.modules[__name__], alldata["fuels"][fuel_description][fuel]["class"]
                            )(**propertiesdict)

                        # add the fuel dict to the current db
                        self.fuels[fuel_db_key] = fuel_dict
            else:
                print(
                    "ERROR : cannot find fuels or compacity variable: <is_compact> in file. Reading stopped."
                )

    def dump_database(self, filename, info, compact=True):
        """save the current fuel database in a yml file.

        Args:
            filename (str): name of the database (database.yml)
            info (str): information about the database
            compact (bool, optional): writting format. Defaults to True.
        """
        # check file name
        if filename is None:
            filename = self.name
        if filename.endswith(".yml"):
            fname = filename
        else:
            fname = filename + ".yml"

        # create data to store
        dict_to_store = {}
        for fuel_description in self.fuels.keys():
            # iterate on fuel classes
            minimal_dict_of_fuels = {}
            for fuel in self.fuels[fuel_description].keys():
                minimal_dict_of_fuels[type(self.fuels[fuel_description][fuel]).__name__] = self.fuels[
                    fuel_description
                ][fuel].minimal_dict(compact=compact)
            # add to dict to store
            dict_to_store[fuel_description] = minimal_dict_of_fuels
        #
        with open(fname, "w") as ymlfile:
            yaml.dump({"infos": info}, ymlfile)
            yaml.dump({"is_compact": compact}, ymlfile)
            # save minimal dict of each fuel
            yaml.dump({"fuels": dict_to_store}, ymlfile)

    def __str__(self) -> str:
        out = "---------- current database ---------\n"
        for fuel_description in self.fuels.keys():
            out += f"* {fuel_description}\n"
        out += "-------------------------------------"
        return out

    def __getitem__(self, key):
        return self.fuels[key]

    def __setitem__(self, key, value):
        self.fuels[key] = value

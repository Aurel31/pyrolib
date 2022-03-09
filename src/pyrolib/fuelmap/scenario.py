""" Scenario classes
"""

import os
import sys

import pkg_resources
import yaml

from .fuels import(
    BalbiFuel,
)

class Scenario:
    """Scenario class

    A scenario contains several fuel class that can be of different types.
    It should contains every fuel type needed to define a fuel map.

    A dictionnary of fuel class called `fuels` store fuel class objects.
    The key is the fuel class type name (ex: BalbiFuel) with an index.

    .. note::
       The index correspond to the number of fuel class type stored in the scenario.

       example : If the scenario contains 3 `BalbiFuel` classes and 2 `RothermelFuel` classes,
       then the keys in the `fuels` dictionnary will be `BalbiFuel1`, `BalbiFuel2`, `BalbiFuel3`,
       `RothermelFuel1`, and `RothermelFuel2`.

    A `Scenario` class can be saved/loaded as `.yml` file.
    Two configurations of yml files can be used :

    - *compact* : Only the name and the value of each property is stored for each fuel class in the scenario.

    - *not compact* : The name, the description, the unit and the value of each property is stored for erach fuel class in the scenario.

    .. note::
       Some basic scenarii are already in the package.
       The following configurations are available with the package:

       - FireFluxI

       - DefaultSA (Sensitivity Analysis study)

    Parameters
    ----------

    name : str, optional
        Short name of the scenario (default: 'Scenario')
    longname : str, optional
        Long name of the scenario (default: `None`).
        If the `longname` is `None`, then the `name` is used as `longname`.
    infos : str, optional
        Various information on the scenario like a reference (default: '')
    load : str, optional
        name of file to load directly after class initialisation

    Attributes
    ----------

    fuels : dict
        dictionnary of fuel classes in the scenario.

    """

    def __init__(self, name="Scenario", longname=None, infos="", load=None):
        self.name = name
        if longname is None:
            self.longname = self.name
        else:
            self.longname = longname
        self.infos = infos
        self.fuels = {}

        if load is not None:
            self.load(filename=load)

    def add_fuel(self, fuel):
        """Add fuel to `fuels` dictionnary

        Parameters
        ----------

        fuel : FuelClass
            Fuel to add in the scenario
        """
        # check if fuel is in fuels dict
        k = 1
        nameoffuel = f"{type(fuel).__name__}{k}"
        while nameoffuel in self.fuels.keys():
            k += 1
            nameoffuel = f"{type(fuel).__name__}{k}"
        self.fuels[nameoffuel] = fuel

    def add_fuels(self, *fuels):
        """Add several fuels to `fuels` dictionnary

        Parameters
        ----------

        fuels : FuelClass
            List of fuels classes of named arguments.
        """
        for fuel in fuels:
            self.add_fuel(fuel)

    def save(self, filename=None, compact=True):
        """Save scenario fuels in yml file

        Parameters
        ----------

        filename : str, optional
            Name of the yml file (default: `self.name.yml`).
            If the `filename` does not end with '.yml', the extension is added.
        compact : bool, optional
            Use compact format to save yml file (default: True)
        """
        # check file name
        if filename is None:
            filename = self.name
        if filename.endswith(".yml"):
            fname = filename
        else:
            fname = filename + ".yml"

        # create data to store
        minimal_dict_of_fuels = {}
        for fuel in self.fuels.keys():
            minimal_dict_of_fuels[fuel] = self.fuels[fuel].minimal_dict(compact=compact)
        #
        with open(fname, "w") as ymlfile:
            yaml.dump({"Name": self.name}, ymlfile)
            yaml.dump({"LongName": self.longname}, ymlfile)
            yaml.dump({"Infos": self.infos}, ymlfile)
            yaml.dump({"isCompact": compact}, ymlfile)
            # save minimal dict of each fuel
            yaml.dump({"Fuels": minimal_dict_of_fuels}, ymlfile)

    #
    def load(self, filename=None):
        """Load scenario fuels from yml file.

        Parameters
        ----------

        filename : str, optional
            Name of the yml file (default: `self.name.yml`).
            If the `filename` does not end with '.yml', the extension is added.
        """
        # check file name
        if filename is None:
            filename = self.name
        if filename.endswith(".yml"):
            fname = filename
        else:
            fname = filename + ".yml"
        # Check default case
        try:
            # defaultpath = pkg_resources.resource_stream(__name__, "/".join(("data/scenario", fname)))
            defaultpath = pkg_resources.resource_stream("pyrolib", "/".join(("data/scenario", fname)))
            defaultexists = os.path.exists(defaultpath.name)
        except:
            defaultexists = False
        # Check local path
        localexists = os.path.exists(fname)
        # Select path
        if defaultexists:
            if localexists:
                print(f"INFO : Default case and local case found with same name <{fname}>\nLocal case loaded")
                FilePath = fname
            else:
                print(f"INFO : Default case <{fname}> loaded")
                FilePath = defaultpath.name
        else:
            if localexists:
                print(f"INFO : Local case <{fname}> loaded")
                FilePath = fname
            else:
                print(f"ERROR : file <{fname}> not found in Default cases directory nor local directory")
                FilePath = fname
        # delete existing fuelsLocalExists
        self.Fuels = {}

        # load new fuels
        with open(FilePath, "r") as ymlfile:
            alldata = yaml.safe_load(ymlfile)
            if "Name" in alldata.keys():
                self.name = alldata["Name"]
            if "LongName" in alldata.keys():
                self.longname = alldata["LongName"]
            if "Infos" in alldata.keys():
                self.infos = alldata["Infos"]

            # read fuels
            if "Fuels" in alldata.keys():
                if "isCompact" in alldata.keys():
                    if alldata["isCompact"]:
                        for fuel in alldata["Fuels"].keys():
                            self.fuels[fuel] = getattr(sys.modules[__name__], alldata["Fuels"][fuel]["class"])(
                                **alldata["Fuels"][fuel]["properties"]
                            )
                        #
                    else:
                        # need to reconstruct properties dictionnary
                        for fuel in alldata["Fuels"].keys():
                            propertiesdict = {}
                            for prop in alldata["Fuels"][fuel]["properties"].keys():
                                propertiesdict[prop] = alldata["Fuels"][fuel]["properties"][prop]["Value"]
                            #
                            self.fuels[fuel] = getattr(sys.modules[__name__], alldata["Fuels"][fuel]["class"])(
                                **propertiesdict
                            )
                else:
                    print("ERROR : cannot find file compacity variable: <isCompact> in file. Reading stopped.")
            else:
                print("ERROR : cannot find Fuels in file.")

    def getR(self):
        """Get rate of spread for each fuel contained in the scenario

        Returns
        -------

        R : dict
            Dictionary of rate of spread

        """
        ros = {}
        for infuel in self.fuels.keys():
            ros[infuel] = self.fuels[infuel].getR()
        return ros

    #
    def show(self, verbose=0):
        """Show information about scenario.

        verbose : int, optional
            level of verbosity (default: 0)

            - 0 : show fuels index and name
            - 1 : show fuels index, name and no wind no slope rate of spread
            - 2 : show fuels index, name, no wind/slope ROS and every fuel properties
        """
        if verbose == 2:
            # verbose level 2
            # print all properties
            for fuel in self.fuels.keys():
                fuelnb = fuel.replace(type(self.fuels[fuel]).__name__, "")
                fuelclass = fuel.replace(fuelnb, "")
                print(f"Fuel index : {fuelnb}, Fuel class : {fuelclass}, ROS : {self.fuels[fuel].getR():.2f} m/s")
                self.fuels[fuel].print_parameters()
                print("")

        elif verbose == 1:
            # verbose level 1
            # print names and ROS
            for fuel in self.fuels.keys():
                fuelnb = fuel.replace(type(self.fuels[fuel]).__name__, "")
                fuelclass = fuel.replace(fuelnb, "")
                print(f"Fuel index : {fuelnb}, Fuel class : {fuelclass}, ROS : {self.fuels[fuel].getR():.2f} m/s")
        else:
            # verbose level 0 or other
            # only prints names
            for fuel in self.fuels.keys():
                fuelnb = fuel.replace(type(self.fuels[fuel]).__name__, "")
                fuelclass = fuel.replace(fuelnb, "")
                print(f"Fuel index : {fuelnb}, Fuel class : {fuelclass}")


def show_default_scenario():
    """List every scenario file in data/scenario directory"""
    data_dir_content = pkg_resources.resource_listdir("pyrolib", "data/scenario")
    print("The following scenario have been found in the default scenario directory:")
    for file in data_dir_content:
        if file.endswith(".yml"):
            print(f"* {file.replace('.yml','')}")
    print("")

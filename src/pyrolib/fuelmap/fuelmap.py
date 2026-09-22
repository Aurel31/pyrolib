""" FuelMap file building tools
"""

import sys
import os
from math import pow, sqrt
from shutil import copy2

import numpy as np
from importlib.resources import files
import yaml
from netCDF4 import Dataset
import f90nml

from .fuels import (
    _ROSMODEL_FUELCLASS_REGISTER,
    _ROSMODEL_NB_PROPERTIES,
    BalbiFuel,
)
from .patch import (
    DataPatch,
    LinePatch,
    RectanglePatch,
)
from .fuel_database import (
    FuelDatabase,
)
from .utility import (
    fire_array_2d_to_3d,
    fill_fuel_array_from_patch,
    convert_lon_lat_to_x_y,
)


class FuelMap:
    """Class for fuel map construction

    This `FuelMap` class allows to create a fuel map object and save it to netcdf format to be an input for a MesoNH-Blaze simulation.

    In order to build a fuel map the following file tree is needed:

    .. code-block:: text

        my_project/
        ├─ create_my_fuelmap.py
        ├─ EXSEG1.nam
        ├─ inifile_MesoNH.des
        ├─ inifile_MesoNH.nc

    The MesoNH namelist `EXSEG1.nam` is used to retrieved information about fire mesh,
    fire rate of spread parameterization and MesoNH initialization files.
    The initialization file (here `inifile_MesoNH.nc`) is used to get atmopsheric mesh information.
    The MesoNH file `inifile_MesoNH.des` will be duplicated to `FuelMap.des` in order to match MesoNH file reader requirements.

    After having set all patches and data treatments to the `FuelMap.fuelmaparray`,
    the :func:`~pyrolib.fuels.FuelMap.write` method can be called to save the file `FuelMap.nc`.
    After this operation, the project folder should be:

    .. code-block:: text

        my_project/
        ├─ create_my_fuelmap.py
        ├─ EXSEG1.nam
        ├─ FuelMap.des
        ├─ FuelMap.nc
        ├─ FuelMap2d.nc
        ├─ inifile_MesoNH.des
        ├─ inifile_MesoNH.nc

    The file `FuelMap2d.nc` is optionnaly created through the :func:`~pyrolib.fuels.FuelMap.write` method.
    It contains the same information that `FuelMap.nc` but conserves the 2d format of data to be more readable for error checking.
    It is recommended to use this file to check your set up.

    Parameters
    ----------

    fuel_db : pyrolib.FuelDatabase
        fuel database containing fuel data.
    namelistname : str, optional
        MesoNH namelist name (default: 'EXSEG1.nam').
    MesoNHversion : str, optional
            Version of MesoNH needed (>=5.6.0) (default: '6.1.0')


    """

    def __init__(
        self,
        fuel_db: FuelDatabase,
        namelistname: str = "EXSEG1.nam",
        MesoNHversion: str = "6.1.0",
        workdir: str = "",
    ):
        self.fuel_db = fuel_db
        self.namelist = namelistname
        self.mnh_version = MesoNHversion
        self.workdir = workdir

        # Read default values for MNHBLAZE namelist from Default_MNH_namelist.yml
        # Values should be compliant with default_desfmn.f90
        defaultpath = files("pyrolib").joinpath("data/Default_MNH_namelist.yml")
        with defaultpath.open("r") as ymlfile:
            alldata = yaml.safe_load(ymlfile)
        current_version = f"v{self.mnh_version.replace('.', '')}"
        # set default value for namelist variables
        self.mnhinifile = alldata[current_version]["mnhinifile"]
        self.cpropag_model = alldata[current_version]["cpropag_model"]
        self.nrefinx = alldata[current_version]["nrefinx"]
        self.nrefiny = alldata[current_version]["nrefiny"]

        # Default values
        self.xfiremeshsize = np.array([0.0, 0.0])  # Fire mesh size (dxf, dyf)
        self.firemeshsizes = None
        self.xfiremesh = None
        self.yfiremesh = None
        self.nx = 0
        self.ny = 0

        self.__get_info_from_namelist()

        self.nbpropertiesfuel = _ROSMODEL_NB_PROPERTIES[self.cpropag_model]
        self.fuel_index_correspondance = {}
        # allocate fuel data array
        self.fuelmaparray = np.zeros((self.nbpropertiesfuel, self.firemeshsizes[1], self.firemeshsizes[0]))
        self.ignitionmaparray = 1e6 * np.ones((self.firemeshsizes[1], self.firemeshsizes[0]))
        self.walkingignitionmaparray = -1.0 * np.ones_like(self.ignitionmaparray)

    def __get_info_from_namelist(self):
        """Retrieve informations on the MesoNH-Blaze run from namelist and initialization file"""
        if self.workdir == "":
            projectpath = os.getcwd()
        else:
            projectpath = self.workdir
        # Check if Namelist exists
        if not os.path.exists(f"{projectpath:s}/{self.namelist:s}"):
            raise IOError(f"File {self.namelist:s} not found")

        # get MNH init file name
        mnh_nml = f90nml.read(f"{projectpath:s}/{self.namelist:s}")
        # Check parameters in namelist
        if "nam_lunitn" in mnh_nml.keys():
            if "cinifile" in mnh_nml["nam_lunitn"].keys():
                self.mnhinifile = mnh_nml["nam_lunitn"]["cinifile"]
        if "nam_firen" in mnh_nml.keys():
            if "cpropag_model" in mnh_nml["nam_firen"].keys():
                self.cpropag_model = mnh_nml["nam_firen"]["cpropag_model"]
            if "nrefinx" in mnh_nml["nam_firen"].keys():
                self.nrefinx = mnh_nml["nam_firen"]["nrefinx"]
            if "nrefiny" in mnh_nml["nam_firen"].keys():
                self.nrefiny = mnh_nml["nam_firen"]["nrefiny"]

        # Check if INIFILE.des exists
        if not os.path.exists(f"{projectpath:s}/{self.mnhinifile:s}.des"):
            raise IOError(f"File {self.mnhinifile:s}.des not found")
        # Check if INIFILE.nc exists
        if not os.path.exists(f"{projectpath:s}/{self.mnhinifile:s}.nc"):
            raise IOError(f"File {self.mnhinifile:s}.nc not found")

        # Import XHAT and YHAT
        MNHData = Dataset(f"{projectpath:s}/{self.mnhinifile:s}.nc")
        self.xhat = MNHData.variables["XHAT"][:]
        self.yhat = MNHData.variables["YHAT"][:]
        # get sizes
        self.nx = len(self.xhat)
        self.ny = len(self.yhat)

        # get conformal projection parameters
        if (
            "BETA" in MNHData.variables.keys()
            and "RPK" in MNHData.variables.keys()
            and "LATORI" in MNHData.variables.keys()
            and "LONORI" in MNHData.variables.keys()
            and "LAT0" in MNHData.variables.keys()
            and "LON0" in MNHData.variables.keys()
        ):
            self.confproj = {
                "beta": float(MNHData.variables["BETA"][:]),
                "k": float(MNHData.variables["RPK"][:]),
                "lat_ori": float(MNHData.variables["LATORI"][:]),
                "lon_ori": float(MNHData.variables["LONORI"][:]),
                "lat0": float(MNHData.variables["LAT0"][:]),
                "lon0": float(MNHData.variables["LON0"][:]),
            }
        else:
            self.confproj = None

        # close file
        MNHData.close()

        self.xfiremeshsize[0] = float(self.xhat[1] - self.xhat[0]) / float(self.nrefinx)
        self.xfiremeshsize[1] = float(self.yhat[1] - self.yhat[0]) / float(self.nrefiny)
        self.firemeshsizes = [self.nx * self.nrefinx, self.ny * self.nrefiny]
        # Get mesh position of fuel cells
        self.xfiremesh = np.linspace(
            self.xhat[0],
            self.xhat[-1] + (self.xhat[1] - self.xhat[0]),
            self.nx * self.nrefinx,
            endpoint=False,
        )
        self.xfiremesh += 0.5 * (self.xfiremesh[1] - self.xfiremesh[0])

        self.yfiremesh = np.linspace(
            self.yhat[0],
            self.yhat[-1] + (self.yhat[1] - self.yhat[0]),
            self.ny * self.nrefiny,
            endpoint=False,
        )
        self.yfiremesh += 0.5 * (self.yfiremesh[1] - self.yfiremesh[0])

    def __add_rectangle_patch(
        self,
        pos1: tuple,
        pos2: tuple,
        fuel_key: str = None,
        ignition_time: float = None,
        unburnable: bool = None,
        is_cartesian: bool = True,
    ):
        """Add rectangle patch between (pos1[0], pos2[0]) and (pos1[1], pos2[1]).

        This method first sets the mask corresponding to the following scheme,
        then assigns the needed data in the appropriated array.

        Three data filing methods are available (one needs to be chosen):

        - Fuel : assign a fuel type in the masked area through its index.
          The fuel assigned depends on its index and the selected rate of spread parameterization.

        - Ignition : Specify an ignition time for the whole patch.

        - Unburnable : Specify that the patch can not burn (ROS = 0 m s-1 in that area).


        .. code-block:: text

            +--------------------------------------------------+
            │MesoNH domain                                     │
            │                                                  │
            │                                                  │
            │                                       (x1, y1)   │
            │               +----------------------+           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               │xxxxx            xxxxx│           │
            │               │xxxxx Fuel Patch xxxxx│           │
            │               │xxxxx            xxxxx│           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               +----------------------+           │
            │       (x0, y0)                                   │
            │                                                  │
            +--------------------------------------------------+

        Parameters
        -----

        pos1 : tuple
            Position of west and east boundaries of the patch
        pos2 : tuple
            Position of south and north boundaries of the patch
        fuel_key : str, optional
            Key of Fuel in FuelDatabase to place in the patch (default: `None`)
        ignition_time : float, optional
            Ignition time of patch (default: `None`)
        unburnable : bool, optional
            Flag to set patch as a non burnable area (default: `None`)
        is_cartesian : bool, optional
            pos1 and pos2 are given with (x, y) instead of (lon, lat) (default: True)
        """
        # convert lon, lat into x, y if necessary
        if is_cartesian:
            xpos = pos1
            ypos = pos2
        else:
            xpos, ypos = convert_lon_lat_to_x_y(confproj=self.confproj, lat=pos2, lon=pos1)

        # Create mask
        P = RectanglePatch(
            self.fuelmaparray, xpos, ypos, self.xfiremesh, self.yfiremesh, self.xfiremeshsize
        )

        # assign data
        self.__assign_data_to_data_array(P, fuel_key, None, ignition_time, unburnable)

    def add_fuel_rectangle_patch(self, pos1: tuple, pos2: tuple, fuel_key: str, is_cartesian: bool = True):
        """Add rectangle fuel patch between (pos1[0], pos2[0]) and (pos1[1], pos2[1]).

        This method first sets the mask corresponding to the following scheme,
        then assigns the needed data in the appropriated array.

        It assigns a fuel type in the masked area through its index.
        The fuel assigned depends on its index and the selected rate of spread parameterization in the Méso-NH namelist.


        .. code-block:: text

            +--------------------------------------------------+
            │MesoNH domain                                     │
            │                                                  │
            │                                                  │
            │                                       (x1, y1)   │
            │               +----------------------+           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               │xxxxx            xxxxx│           │
            │               │xxxxx Fuel Patch xxxxx│           │
            │               │xxxxx            xxxxx│           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               +----------------------+           │
            │       (x0, y0)                                   │
            │                                                  │
            +--------------------------------------------------+

        Parameters
        -----

        pos1 : tuple
            Position of west and east boundaries of the patch
        pos2 : tuple
            Position of south and north boundaries of the patch
        fuel_key : str
            key of Fuel in fuel database to place in the patch
        is_cartesian : bool, optional
            pos1 and pos2 are given with (x, y) instead of (lon, lat) (default: True)
        """
        self.__add_rectangle_patch(pos1, pos2, fuel_key=fuel_key, is_cartesian=is_cartesian)

    def add_unburnable_rectangle_patch(self, pos1: tuple, pos2: tuple, is_cartesian: bool = True):
        """Add rectangle unburnable patch between (pos1[0], pos2[0]) and (pos1[1], pos2[1]).

        This method first sets the mask corresponding to the following scheme,
        then assigns the needed data in the appropriated array.

        It specifies that the patch can not burn (ROS = 0 m s-1 in that area).


        .. code-block:: text

            +--------------------------------------------------+
            │MesoNH domain                                     │
            │                                                  │
            │                                                  │
            │                                       (x1, y1)   │
            │               +----------------------+           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               │xxxxx            xxxxx│           │
            │               │xxxxx    Patch   xxxxx│           │
            │               │xxxxx            xxxxx│           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               +----------------------+           │
            │       (x0, y0)                                   │
            │                                                  │
            +--------------------------------------------------+

        Parameters
        -----

        pos1 : tuple
            Position of west and east boundaries of the patch
        pos2 : tuple
            Position of south and north boundaries of the patch
        is_cartesian : bool, optional
            pos1 and pos2 are given with (x, y) instead of (lon, lat) (default: True)
        """
        self.__add_rectangle_patch(pos1, pos2, unburnable=True, is_cartesian=is_cartesian)

    def add_ignition_rectangle_patch(
        self, pos1: tuple, pos2: tuple, ignition_time: float, is_cartesian: bool = True
    ):
        """Add rectangle patch between (pos1[0], pos2[0]) and (pos1[1], pos2[1]).

        This method first sets the mask corresponding to the following scheme,
        then assigns the needed data in the appropriated array.

        It specifies an ignition time for the whole patch.


        .. code-block:: text

            +--------------------------------------------------+
            │MesoNH domain                                     │
            │                                                  │
            │                                                  │
            │                                       (x1, y1)   │
            │               +----------------------+           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               │xxxxx            xxxxx│           │
            │               │xxxxx    Patch   xxxxx│           │
            │               │xxxxx            xxxxx│           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               │xxxxxxxxxxxxxxxxxxxxxx│           │
            │               +----------------------+           │
            │       (x0, y0)                                   │
            │                                                  │
            +--------------------------------------------------+

        Parameters
        -----

        pos1 : tuple
            Position of west and east boundaries of the patch
        pos2 : tuple
            Position of south and north boundaries of the patch
        ignition_time : float
            Ignition time of patch
        is_cartesian : bool, optional
            pos1 and pos2 are given with (x, y) instead of (lon, lat) (default: True)
        """
        self.__add_rectangle_patch(pos1, pos2, ignition_time=ignition_time, is_cartesian=is_cartesian)

    def __add_line_patch(
        self,
        pos1: tuple,
        pos2: tuple,
        fuel_key: str = None,
        walking_ignition_times: list = None,
        ignition_time: float = None,
        unburnable: bool = None,
        is_cartesian: bool = True,
    ):
        """Add line patch between (pos1[0], pos2[0]) and (pos1[1], pos2[1]).

        This method first sets the mask corresponding to the following scheme,
        then assigns the needed data in the appropriated array.

        Three data filing methods are available (one needs to be chosen):

        - Fuel : assign a fuel type in the masked area through its index.
          The fuel assigned depends on its index and the selected rate of spread parameterization.

        - Walking Ignition : Specify an ignition time `t_a` for point A (x0, y0)
          and `t_b`  for point B (x1, y1) where `t_b > t_a`.

        - Ignition : Specify an ignition time for the whole patch.

        - Unburnable : Specify that the patch can not burn (ROS = 0 m s-1 in that area).

        The mask is determined by a bresenham algorithm.


        .. code-block:: text

            +--------------------------------------------------+
            │MesoNH domain                                     │
            │                                                  │
            │                                                  │
            │                            -> (x1, y1)           │
            │                          _/                      │
            │                       __/                        │
            │                     _/                           │
            │                   _/                             │
            │                __/                               │
            │     (x0, y0) _/                                  │
            │                                                  │
            +--------------------------------------------------+

        Parameters
        -----

        pos1 : tuple
            Position of west and east boundaries of the patch
        pos2 : tuple
            Position of south and north boundaries of the patch
        fuel_key : str, optional
            Index of Fuel in FuelDatabase to place in the patch (default: `None`)
        walking_ignition_times : list, optional
            Ignition times of points A and B of the ignition line, respectively (default: `None`)
        ignition_time : float, optional
            Ignition time of patch (default: `None`)
        unburnable : bool, optional
            Flag to set patch as a non burnable area (default: `None`)
        is_cartesian : bool, optional
            pos1 and pos2 are given with (x, y) instead of (lon, lat) (default: True)
        """
        if is_cartesian:
            xpos = pos1
            ypos = pos2
        else:
            xpos, ypos = convert_lon_lat_to_x_y(confproj=self.confproj, lat=pos2, lon=pos1)

        # Create mask
        patch = LinePatch(self.fuelmaparray, xpos, ypos, self.xfiremesh, self.yfiremesh, self.xfiremeshsize)

        # # assign data
        self.__assign_data_to_data_array(patch, fuel_key, walking_ignition_times, ignition_time, unburnable)

    def add_fuel_line_patch(self, pos1: tuple, pos2: tuple, fuel_key: str, is_cartesian: bool = True):
        """Add line patch between (pos1[0], pos2[0]) and (pos1[1], pos2[1]).

        This method first sets the mask corresponding to the following scheme,
        then assigns the needed data in the appropriated array.

        It assigns a fuel type in the masked area through its index.
        The fuel assigned depends on its index and the selected rate of spread parameterization.

        The mask is determined by a bresenham algorithm.


        .. code-block:: text

            +--------------------------------------------------+
            │MesoNH domain                                     │
            │                                                  │
            │                                                  │
            │                            -> (x1, y1)           │
            │                          _/                      │
            │                       __/                        │
            │                     _/                           │
            │                   _/                             │
            │                __/                               │
            │     (x0, y0) _/                                  │
            │                                                  │
            +--------------------------------------------------+

        Parameters
        -----

        pos1 : tuple
            Position of west and east boundaries of the patch
        pos2 : tuple
            Position of south and north boundaries of the patch
        fuel_key : str
            Key of Fuel in fuel database to place in the patch
        is_cartesian : bool, optional
            pos1 and pos2 are given with (x, y) instead of (lon, lat) (default: True)
        """
        self.__add_line_patch(pos1, pos2, fuel_key=fuel_key, is_cartesian=is_cartesian)

    def add_walking_ignition_line_patch(
        self, pos1: tuple, pos2: tuple, walking_ignition_times: list, is_cartesian: bool = True
    ):
        """Add line patch between (pos1[0], pos2[0]) and (pos1[1], pos2[1]).

        This method first sets the mask corresponding to the following scheme,
        then assigns the needed data in the appropriated array.

        It specifies an ignition time `t_a` for point A (x0, y0)
          and `t_b`  for point B (x1, y1) where `t_b > t_a`.

        The mask is determined by a bresenham algorithm.


        .. code-block:: text

            +--------------------------------------------------+
            │MesoNH domain                                     │
            │                                                  │
            │                                                  │
            │                            -> (x1, y1)           │
            │                          _/                      │
            │                       __/                        │
            │                     _/                           │
            │                   _/                             │
            │                __/                               │
            │     (x0, y0) _/                                  │
            │                                                  │
            +--------------------------------------------------+

        Parameters
        -----

        pos1 : tuple
            Position of west and east boundaries of the patch
        pos2 : tuple
            Position of south and north boundaries of the patch
        walking_ignition_times : list
            Ignition times of points A and B of the ignition line, respectively
        is_cartesian : bool, optional
            pos1 and pos2 are given with (x, y) instead of (lon, lat) (default: True)
        """
        self.__add_line_patch(
            pos1, pos2, walking_ignition_times=walking_ignition_times, is_cartesian=is_cartesian
        )

    def add_ignition_line_patch(
        self, pos1: tuple, pos2: tuple, ignition_time: float, is_cartesian: bool = True
    ):
        """Add line patch between (pos1[0], pos2[0]) and (pos1[1], pos2[1]).

        This method first sets the mask corresponding to the following scheme,
        then assigns the needed data in the appropriated array.

        It specifies an ignition time for the whole patch.

        The mask is determined by a bresenham algorithm.


        .. code-block:: text

            +--------------------------------------------------+
            │MesoNH domain                                     │
            │                                                  │
            │                                                  │
            │                            -> (x1, y1)           │
            │                          _/                      │
            │                       __/                        │
            │                     _/                           │
            │                   _/                             │
            │                __/                               │
            │     (x0, y0) _/                                  │
            │                                                  │
            +--------------------------------------------------+

        Parameters
        -----

        pos1 : tuple
            Position of west and east boundaries of the patch
        pos2 : tuple
            Position of south and north boundaries of the patch
        ignition_time : float
            Ignition time of patch
        is_cartesian : bool, optional
            pos1 and pos2 are given with (x, y) instead of (lon, lat) (default: True)
        """
        self.__add_line_patch(pos1, pos2, ignition_time=ignition_time, is_cartesian=is_cartesian)

    def add_unburnable_line_patch(self, pos1: tuple, pos2: tuple, is_cartesian: bool = True):
        """Add line patch between (pos1[0], pos2[0]) and (pos1[1], pos2[1]).

        This method first sets the mask corresponding to the following scheme,
        then assigns the needed data in the appropriated array.

        It Specifies that the patch can not burn (ROS = 0 m s-1 in that area).

        The mask is determined by a bresenham algorithm.


        .. code-block:: text

            +--------------------------------------------------+
            │MesoNH domain                                     │
            │                                                  │
            │                                                  │
            │                            -> (x1, y1)           │
            │                          _/                      │
            │                       __/                        │
            │                     _/                           │
            │                   _/                             │
            │                __/                               │
            │     (x0, y0) _/                                  │
            │                                                  │
            +--------------------------------------------------+

        Parameters
        -----

        pos1 : tuple
            Position of west and east boundaries of the patch
        pos2 : tuple
            Position of south and north boundaries of the patch
        is_cartesian : bool, optional
            pos1 and pos2 are given with (x, y) instead of (lon, lat) (default: True)
        """
        self.__add_line_patch(pos1, pos2, unburnable=True, is_cartesian=is_cartesian)

    def __assign_data_to_data_array(
        self,
        patch: DataPatch,
        fuel_key: str = None,
        walkingignitiontimes: tuple = None,
        ignitiontime: float = None,
        unburnable: bool = None,
    ):
        """
        This function assigns data as a function of argument passed

        4 types of data can be allocated in the patch:
            - Fuel properties
                Select a fuel number (it should be contained in the FuelDatabase object loaded in the FuelMap object).
                The corresponding fuel properties of the selected Fuel are assigned in the patch

            - Walking ignition times (only for LinePatch)
                allocate ignition time from point A (x0, y0) at ta to point B (x1, y1) at tb with tb > ta
                The ignition time along the line is linearly interpolated with the distance relative to point A.

            - Ignition time
                Modify the ignition map with the specified time.
                The whole patch will ignite at the same time.

            - Unburnable
                Every fuel property is set to 0 in the patch leading to a no propagation zone.
                Be carreful for futur implementation of new fire spread parameterization to not have 0 division with this process.
        """
        # case 1 : FuelIndex is set
        if isinstance(fuel_key, str):
            if fuel_key in self.fuel_db.fuels.keys():
                # check if needed fuel (corresponding fuel class and number of FuelIndex)
                needed_fuelclass = _ROSMODEL_FUELCLASS_REGISTER[self.cpropag_model]
                if needed_fuelclass in self.fuel_db.fuels[fuel_key].keys():
                    # retrieve fuel index
                    if fuel_key in self.fuel_index_correspondance.keys():
                        fuelindex = self.fuel_index_correspondance[fuel_key]
                    else:
                        maxindex = 0
                        for idx in self.fuel_index_correspondance.values():
                            maxindex = max(maxindex, idx)
                        fuelindex = maxindex + 1
                        self.fuel_index_correspondance[fuel_key] = fuelindex

                    # create property vector for this fuel
                    propvector = self.fuel_db.fuels[fuel_key][needed_fuelclass].get_property_vector(
                        fuelindex, self.nbpropertiesfuel
                    )

                    self.fuelmaparray = fill_fuel_array_from_patch(
                        self.fuelmaparray,
                        patch.datamask,
                        propvector,
                        self.nbpropertiesfuel,
                        self.firemeshsizes[0],
                        self.firemeshsizes[1],
                    )
                else:
                    print(
                        f"Fuel < {fuel_key} > do not exist in database with the needed Fuel Class < {needed_fuelclass} >."
                    )
            else:
                print(f"Fuel < {fuel_key} > not found in the fuel database. Nothing appended")
            return

        # case 2 : walking ignition process
        #          (only for LinePatch)
        if walkingignitiontimes is not None:
            # compute total distance between points A and B
            totaldist = sqrt(pow(patch.xpos[1] - patch.xpos[0], 2) + pow(patch.ypos[1] - patch.ypos[0], 2))
            # get time difference between tb and ta
            ignitiondt = walkingignitiontimes[1] - walkingignitiontimes[0]
            # compute ignition time for each line point
            for ind in patch.line:
                # distance from A
                dist = sqrt(
                    pow(self.xfiremesh[ind[0]] - patch.xpos[0], 2)
                    + pow(self.yfiremesh[ind[1]] - patch.ypos[0], 2)
                )
                # linear interpolation
                self.walkingignitionmaparray[ind[1], ind[0]] = (
                    walkingignitiontimes[0] + dist * ignitiondt / totaldist
                )
            return

        # case 3 : ignition of whole patch is set
        if ignitiontime is not None:
            self.ignitionmaparray[patch.datamask == 1] = ignitiontime
            return

        # case 4 : Unburnable is set
        if unburnable is not None:
            # create property vector of 0
            propvector = np.zeros(self.nbpropertiesfuel)
            self.fuelmaparray = fill_fuel_array_from_patch(
                self.fuelmaparray,
                patch.datamask,
                propvector,
                self.nbpropertiesfuel,
                self.firemeshsizes[0],
                self.firemeshsizes[1],
            )
            return
        print("WARNING: No information given on what to do.")
        print("WARNING:     - fuel_key not defined (expected str)")
        print("WARNING:     - walkingignitiontimes not defined")
        print("WARNING:     - ignitiontime not defined")
        print("WARNING:     - unburnable not defined")

    def dump_mesonh(self, verbose: int = 0):
        """Write Fuel map as netCFD file named FuelMap.nc for Méso-NH

        Fire fields are stored on the ``(F, Y, X)`` grid expected by the Blaze reader
        (see :func:`~pyrolib.fuelmap.utility.fire_array_2d_to_3d`).
        The ``<cinifile>.des`` file is copied to ``FuelMap.des`` alongside.

        Parameters
        ----------

        verbose : int, optional
            verbose level (0: no prints, 1: low verbosity, 2: high verbosity) (default: 0)
        """
        projectpath = self.__get_project_path()

        # copy .des file
        copy2(f"{projectpath:s}/{self.mnhinifile:s}.des", f"{projectpath:s}/FuelMap.des")

        NewFile = self.__create_mesonh_file(
            f"{projectpath:s}/FuelMap.nc", {"F": self.nrefinx * self.nrefiny}, verbose
        )

        # fire grid
        firelevel = NewFile.createVariable("F", np.float64, ("F"))
        firelevel.long_name = "fire-dimension"
        firelevel.standard_name = " "
        firelevel[:] = np.array(np.arange(0, self.nrefinx * self.nrefiny), dtype=np.float64)

        self.__write_fire_fields(
            NewFile,
            ("F", "Y", "X"),
            lambda array: fire_array_2d_to_3d(array, self.nx, self.ny, self.nrefinx, self.nrefiny),
            verbose,
        )

        if verbose >= 1:
            print(">>> Close FuelMap.nc")

        NewFile.close()
        self.__show_fuel_index_correspondance()

    def dump(self, verbose: int = 0):
        """Write 2D Fuel map as netCFD file named FuelMap2d.nc

        Same content as :func:`dump_mesonh` but fire fields are stored on the
        human-readable 2D fire grid ``(YFIRE, XFIRE)``. Méso-NH does not read this file.

        Parameters
        ----------

        verbose : int, optional
            verbose level (0: no prints, 1: low verbosity, 2: high verbosity) (default: 0)
        """
        projectpath = self.__get_project_path()

        NewFile = self.__create_mesonh_file(
            f"{projectpath:s}/FuelMap2d.nc",
            {"XFIRE": self.nx * self.nrefinx, "YFIRE": self.ny * self.nrefiny},
            verbose,
        )

        # fire grid
        firegrid = NewFile.createVariable("XFIRE", np.float64, ("XFIRE"))
        firegrid.long_name = "x-fire-dimension"
        firegrid.standard_name = "x_coordinate"
        firegrid.axis = "X"
        firegrid.unit = "m"
        firegrid[:] = self.xfiremesh

        firegrid = NewFile.createVariable("YFIRE", np.float64, ("YFIRE"))
        firegrid.long_name = "y-fire-dimension"
        firegrid.standard_name = "y_coordinate"
        firegrid.axis = "Y"
        firegrid.unit = "m"
        firegrid[:] = self.yfiremesh

        self.__write_fire_fields(NewFile, ("YFIRE", "XFIRE"), lambda array: array, verbose)

        if verbose >= 1:
            print(">>> Close FuelMap2d.nc")

        NewFile.close()
        self.__show_fuel_index_correspondance()

    def __get_project_path(self) -> str:
        """Return the directory holding the Méso-NH files (``workdir`` or the current directory)"""
        if self.workdir == "":
            return os.getcwd()
        return self.workdir

    def __create_mesonh_file(self, filename: str, fire_dimensions: dict, verbose: int = 0) -> Dataset:
        """Create a netCDF file with the header shared by FuelMap.nc and FuelMap2d.nc

        Writes the global attributes, dimensions, version metadata and atmospheric grid
        following MesoNH output files nomenclature. Fire-grid coordinate variables and
        fire fields are left to the caller.

        Parameters
        ----------

        filename : str
            path of the netCDF file to create
        fire_dimensions : dict
            fire grid dimensions to create, as ``{name: size}``
        verbose : int, optional
            verbose level (0: no prints, 1: low verbosity, 2: high verbosity) (default: 0)

        Returns
        -------

        netCDF4.Dataset
            the open file, in write mode
        """
        if verbose >= 1:
            print(f">>> Create {os.path.basename(filename):s}")

        NewFile = Dataset(filename, "w")

        if verbose >= 2:
            print(">> Store MesoNH file info")

        # need to be compliant with MesoNH output files nomenclature
        NewFile.Conventions = "CF-1.7 COMODO-1.4"
        NewFile.MNH_REAL = "8"
        NewFile.MNH_INT = "4"
        NewFile.MNH_cleanly_closed = "yes"
        NewFile.MNH_REDUCE_DIMENSIONS_IN_FILES = "1"
        # Mandatory for files declaring MesoNH >= 5.7.1: IO_Check_precision_loss_nc4
        # (mode_io_file_nc4.f90) aborts the run when it is absent. "0" means no
        # reduction of float precision, which is what this writer does.
        NewFile.MNH_REDUCE_FLOAT_PRECISION = "0"
        NewFile.MNH_COMPRESS_LOSSY = "0"

        NewFile.createDimension("X", self.nx)
        NewFile.createDimension("Y", self.ny)
        for name, size in fire_dimensions.items():
            NewFile.createDimension(name, size)
        NewFile.createDimension("size3", 3)
        NewFile.createDimension("char16", 16)

        # MesoNH stores integers on 4 bytes (see the MNH_INT attribute above).
        MNHversion = np.array(self.mnh_version.split("."), dtype=np.int32)

        # Since MesoNH 6.0.0 the version is read from these global attributes
        # (IO_mnhversion_attributes_read_nc4). The variables below are the
        # legacy fallback used by older versions.
        NewFile.MNH_VERSION = MNHversion
        NewFile.MNH_VERSION_STR = self.mnh_version
        NewFile.MNH_VERSION_USER = ""

        varia = NewFile.createVariable("MNHVERSION", np.int32, ("size3"), fill_value=-2147483647)
        varia.long_name = "MesoNH version"
        varia.valid_min = np.intc(-2147483646)
        varia.valid_max = np.intc(2147483647)
        varia[:] = MNHversion

        # MASDEV packs major and minor as read back by IO_Mnhversion_get:
        # major * 10 + minor, or major * 100 + minor for minor >= 10.
        varia = NewFile.createVariable("MASDEV", np.int32, ())
        varia.long_name = "MesoNH version (without bugfix)"
        varia[...] = MNHversion[0] * (100 if MNHversion[1] >= 10 else 10) + MNHversion[1]

        varia = NewFile.createVariable("BUGFIX", np.int32, ())
        varia.long_name = "MesoNH bugfix number"
        varia[...] = MNHversion[2]

        varia = NewFile.createVariable("STORAGE_TYPE", "c", ("char16"))
        varia.long_name = "STORAGE_TYPE"
        varia.comment = "Storage type for the information written in the FM files"
        varia[:] = "TT              "

        varia = NewFile.createVariable("FILETYPE", "c", ("char16"))
        varia.long_name = "type of this file"
        varia[:] = "BlazeData       "

        # x grid
        if verbose >= 2:
            print(">> Store grid")

        ni = NewFile.createVariable("X", np.float64, ("X"))
        ni.long_name = "x-dimension of the grid"
        ni.standard_name = "x_coordinate"
        ni.units = "m"
        ni.axis = "X"
        ni[:] = self.xhat

        # y grid
        nj = NewFile.createVariable("Y", np.float64, ("Y"))
        nj.long_name = "y-dimension of the grid"
        nj.standard_name = "y_coordinate"
        nj.units = "m"
        nj.axis = "Y"
        nj[:] = self.yhat

        return NewFile

    def __write_fire_fields(self, ncfile: Dataset, dimensions: tuple, pack, verbose: int = 0):
        """Write the ignition maps, the fuel type map and every fuel property map

        Parameters
        ----------

        ncfile : netCDF4.Dataset
            open file, whose ``dimensions`` already exist
        dimensions : tuple
            dimensions of each fire field variable, e.g. ``("F", "Y", "X")``
        pack : callable
            maps a 2D fire array ``(nyf, nxf)`` to the array stored on ``dimensions``
        verbose : int, optional
            verbose level (0: no prints, 1: low verbosity, 2: high verbosity) (default: 0)
        """

        def write_field(name, array, long_name, comment, units):
            field = ncfile.createVariable(name, np.float64, dimensions)
            field.standard_name = " "
            field.long_name = long_name
            field.comment = comment
            field.units = units
            field.grid = np.intc(4)
            field[...] = pack(array)

        if verbose >= 2:
            print(">> Store ignition map")
        write_field("Ignition", self.ignitionmaparray, "Ignition time", "Ignition map", "s")

        if verbose >= 2:
            print(">> Store walking ignition map")
        write_field(
            "WalkingIgnition",
            self.walkingignitionmaparray,
            "Walking ignition time",
            "WalkingIgnition map",
            "s",
        )

        if verbose >= 2:
            print(">> Store fuel type map")
        write_field("Fuel_type", self.fuelmaparray[0, :, :], "Fuel_type", "Fuel type", "1")

        # one variable per fuel property, at the slot given by its propertyindex
        if verbose >= 2:
            print(">> Store properties maps")
        chosen_fuel_class = getattr(
            sys.modules[__name__], _ROSMODEL_FUELCLASS_REGISTER[self.cpropag_model]
        )()
        for propertyname in vars(chosen_fuel_class):
            propertyobj = getattr(chosen_fuel_class, propertyname)
            if propertyobj.propertyindex is not None:
                write_field(
                    propertyobj.name,
                    self.fuelmaparray[propertyobj.propertyindex, :, :],
                    propertyobj.name,
                    propertyobj.description,
                    propertyobj.unit,
                )

    def __show_fuel_index_correspondance(self):
        """print fuel index correspondance dict"""
        print("---------- fuel index table ----------")
        print(" Index |             Fuel             ")
        for fuel in self.fuel_index_correspondance.keys():
            print(f"  {self.fuel_index_correspondance[fuel]:3d}  | {fuel}")
        print("--------------------------------------")

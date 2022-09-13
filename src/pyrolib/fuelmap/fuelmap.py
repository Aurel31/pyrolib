""" FuelMap file building tools
"""

import sys
import os
from math import pow, sqrt
from shutil import copy2

import numpy as np
import pkg_resources
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
            Version of MesoNH needed (>=5.4.4) (default: '5.5.0')


    """

    def __init__(
        self,
        fuel_db: FuelDatabase,
        namelistname: str = "EXSEG1.nam",
        MesoNHversion: str = "5.5.0",
        workdir: str = "",
    ):
        self.fuel_db = fuel_db
        self.namelist = namelistname
        self.mnh_version = MesoNHversion
        self.workdir = workdir

        # Read default values for MNHBLAZE namelist from Default_MNH_namelist.yml
        # Values should be compliant with default_desfmn.f90
        defaultpath = pkg_resources.resource_stream(
            "pyrolib", "/".join(("data", "Default_MNH_namelist.yml"))
        )
        with open(defaultpath.name, "r") as ymlfile:
            alldata = yaml.safe_load(ymlfile)
        current_version = f"v{self.mnh_version.replace('.', '')}"
        # set default value for namelist variables
        self.mnhinifile = alldata[current_version]["mnhinifile"]
        self.cpropag_model = alldata[current_version]["cpropag_model"]
        self.nrefinx = alldata[current_version]["nrefinx"]
        self.nrefiny = alldata[current_version]["nrefiny"]

        # Default values
        self.xfiremeshsize = np.array([0, 0])  # Fire mesh size (dxf, dyf)
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
        if "nam_fire" in mnh_nml.keys():
            if "cpropag_model" in mnh_nml["nam_fire"].keys():
                self.cpropag_model = mnh_nml["nam_fire"]["cpropag_model"]
            if "nrefinx" in mnh_nml["nam_fire"].keys():
                self.nrefinx = mnh_nml["nam_fire"]["nrefinx"]
            if "nrefiny" in mnh_nml["nam_fire"].keys():
                self.nrefiny = mnh_nml["nam_fire"]["nrefiny"]

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
        self.xfiremeshsize[1] = float(self.yhat[1] - self.yhat[0]) / float(self.nrefinx)
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


        .. aafig::
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


        .. aafig::
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


        .. aafig::
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


        .. aafig::
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


        .. aafig::
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


        .. aafig::
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


        .. aafig::
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


        .. aafig::
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


        .. aafig::
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

        Parameters
        ----------

        verbose : int, optional
            verbose level (0: no prints, 1: low verbosity, 2: high verbosity) (default: 0)
        """
        if self.workdir == "":
            projectpath = os.getcwd()
        else:
            projectpath = self.workdir

        # copy .des file
        copy2(f"{projectpath:s}/{self.mnhinifile:s}.des", f"{projectpath:s}/FuelMap.des")

        # Create new netcdf file to store fuel data
        if verbose >= 1:
            print(f">>> Create FuelMap.nc")

        NewFile = Dataset(f"{projectpath:s}/FuelMap.nc", "w")

        if verbose >= 2:
            print(f">> Store MesoNH file info")

        # need to be compliant with MesoNH output files nomenclature
        NewFile.Conventions = "CF-1.7 COMODO-1.4"
        NewFile.MNH_REAL = "8"
        NewFile.MNH_INT = "4"
        NewFile.MNH_cleanly_closed = "yes"
        NewFile.MNH_REDUCE_DIMENSIONS_IN_FILES = "1"

        NewFile.createDimension("X", self.nx)
        NewFile.createDimension("Y", self.ny)
        NewFile.createDimension("F", self.nrefinx * self.nrefiny)
        NewFile.createDimension("size3", 3)
        NewFile.createDimension("char16", 16)

        MNHversion = np.array(self.mnh_version.split("."), dtype=int)
        varia = NewFile.createVariable("MNHVERSION", int, ("size3"), fill_value=-2147483647)
        varia.long_name = "MesoNH version"
        varia.valid_min = np.intc(-2147483646)
        varia.valid_max = np.intc(2147483647)
        varia[:] = MNHversion

        varia = NewFile.createVariable("MASDEV", int, ())
        varia.long_name = "MesoNH version (without bugfix)"
        varia = MNHversion[0]

        varia = NewFile.createVariable("BUGFIX", int, ())
        varia.long_name = "MesoNH bugfix number"
        varia = MNHversion[1]

        varia = NewFile.createVariable("STORAGE_TYPE", "c", ("char16"))
        varia.long_name = "STORAGE_TYPE"
        varia.comment = "Storage type for the information written in the FM files"
        varia[:] = "TT              "

        varia = NewFile.createVariable("FILETYPE", "c", ("char16"))
        varia.long_name = "type of this file"
        varia[:] = "BlazeData       "

        # x grid
        if verbose >= 2:
            print(f">> Store grid")

        ni = NewFile.createVariable("X", np.float64, ("X"))
        ni.comment = "x-dimension"
        ni.grid = np.intc(0)
        ni.standard_name = "x coordinates"
        ni.units = "m"
        ni.axis = "X"
        ni[:] = self.xhat

        # y grid
        nj = NewFile.createVariable("Y", np.float64, ("Y"))
        nj.comment = "y-dimension"
        nj.grid = np.intc(0)
        nj.standard_name = "y coordinates"
        nj.units = "m"
        nj.axis = "Y"
        nj[:] = self.yhat

        # fire grid
        firelevel = NewFile.createVariable("F", np.float64, ("F"))
        firelevel.comment = "fire-dimension"
        firelevel.grid = np.intc(0)
        firelevel.standard_name = "Fire dimension"
        firelevel.axis = "F"
        firelevel[:] = np.array(np.arange(0, self.nrefinx * self.nrefiny), dtype=np.float64)

        # ignition map
        if verbose >= 2:
            print(f">> Store ignition map")

        IgnitionNC = NewFile.createVariable("Ignition", np.float64, ("F", "Y", "X"))
        IgnitionNC.comment = "Ignition map"
        IgnitionNC.grid = np.intc(4)
        IgnitionNC.standard_name = "Ignition"
        IgnitionNC.long_name = "Ignition time"
        IgnitionNC.units = "s"
        IgnitionNC[:, :, :] = fire_array_2d_to_3d(
            self.ignitionmaparray, self.nx, self.ny, self.nrefinx, self.nrefiny
        )

        # walking ignition map
        if verbose >= 2:
            print(f">> Store walking ignition map")
        IgnitionNC = NewFile.createVariable("WalkingIgnition", np.float64, ("F", "Y", "X"))
        IgnitionNC.comment = "WalkingIgnition map"
        IgnitionNC.grid = np.intc(4)
        IgnitionNC.standard_name = "WalkingIgnition"
        IgnitionNC.long_name = "Walking ignition time"
        IgnitionNC.units = "s"
        IgnitionNC[:, :, :] = fire_array_2d_to_3d(
            self.walkingignitionmaparray, self.nx, self.ny, self.nrefinx, self.nrefiny
        )

        # fuel type map
        if verbose >= 2:
            print(f">> Store fuel type map")
        FuelMap = NewFile.createVariable("Fuel01", np.float64, ("F", "Y", "X"))
        FuelMap.standard_name = "Fuel01"
        FuelMap.long_name = "Fuel type"
        FuelMap.comment = "Fuel type"
        FuelMap.units = "-"
        FuelMap.grid = np.intc(4)
        FuelMap[:, :, :] = fire_array_2d_to_3d(
            self.fuelmaparray[0, :, :], self.nx, self.ny, self.nrefinx, self.nrefiny
        )

        # Write each fuel as 3d table
        if verbose >= 2:
            print(f">> Store properties maps")
        chosen_fuel_class = getattr(
            sys.modules[__name__], _ROSMODEL_FUELCLASS_REGISTER[self.cpropag_model]
        )()
        for propertyname in vars(chosen_fuel_class):
            propertyobj = getattr(chosen_fuel_class, propertyname)
            if propertyobj.propertyindex is not None:
                fuelname = f"Fuel{propertyobj.propertyindex + 1:02d}"
                FuelMap = NewFile.createVariable(fuelname, np.float64, ("F", "Y", "X"))
                FuelMap.standard_name = fuelname
                FuelMap.long_name = propertyobj.name
                FuelMap.comment = propertyobj.description
                FuelMap.units = propertyobj.unit
                FuelMap.grid = np.intc(4)
                FuelMap[:, :, :] = fire_array_2d_to_3d(
                    self.fuelmaparray[propertyobj.propertyindex, :, :],
                    self.nx,
                    self.ny,
                    self.nrefinx,
                    self.nrefiny,
                )

        if verbose >= 1:
            print(f">>> Close FuelMap.nc")

        NewFile.close()
        self.__show_fuel_index_correspondance()

    def dump(self, verbose: int = 0):
        """Write 2D Fuel map as netCFD file named FuelMap2d.nc

        Parameters
        ----------

        verbose : int, optional
            verbose level (0: no prints, 1: low verbosity, 2: high verbosity) (default: 0)
        """
        if self.workdir == "":
            projectpath = os.getcwd()
        else:
            projectpath = self.workdir

        if verbose >= 1:
            print(f">>> Create FuelMap2d.nc")

        NewFile = Dataset(f"{projectpath:s}/FuelMap2d.nc", "w")

        if verbose >= 2:
            print(f">> Store MesoNH file info")

        # need to be compliant with MesoNH output files nomenclature
        NewFile.Conventions = "CF-1.7 COMODO-1.4"
        NewFile.MNH_REAL = "8"
        NewFile.MNH_INT = "4"
        NewFile.MNH_cleanly_closed = "yes"
        NewFile.MNH_REDUCE_DIMENSIONS_IN_FILES = "1"

        NewFile.createDimension("X", self.nx)
        NewFile.createDimension("Y", self.ny)
        NewFile.createDimension("XFIRE", self.nx * self.nrefinx)
        NewFile.createDimension("YFIRE", self.ny * self.nrefiny)
        NewFile.createDimension("size3", 3)
        NewFile.createDimension("char16", 16)

        MNHversion = np.array(self.mnh_version.split("."), dtype=int)
        varia = NewFile.createVariable("MNHVERSION", int, ("size3"), fill_value=-2147483647)
        varia.long_name = "MesoNH version"
        varia.valid_min = np.intc(-2147483646)
        varia.valid_max = np.intc(2147483647)
        varia[:] = MNHversion

        varia = NewFile.createVariable("MASDEV", int, ())
        varia.long_name = "MesoNH version (without bugfix)"
        varia = MNHversion[0]

        varia = NewFile.createVariable("BUGFIX", int, ())
        varia.long_name = "MesoNH bugfix number"
        varia = MNHversion[1]

        varia = NewFile.createVariable("STORAGE_TYPE", "c", ("char16"))
        varia.long_name = "STORAGE_TYPE"
        varia.comment = "Storage type for the information written in the FM files"
        varia[:] = "TT              "

        varia = NewFile.createVariable("FILETYPE", "c", ("char16"))
        varia.long_name = "type of this file"
        varia[:] = "BlazeData       "

        # x grid
        if verbose >= 2:
            print(f">> Store grid")

        ni = NewFile.createVariable("X", np.float64, ("X"))
        ni.comment = "x-dimension"
        ni.grid = np.intc(0)
        ni.standard_name = "x coordinates"
        ni.units = "m"
        ni.axis = "X"
        ni[:] = self.xhat

        # y grid
        nj = NewFile.createVariable("Y", np.float64, ("Y"))
        nj.comment = "y-dimension"
        nj.grid = np.intc(0)
        nj.standard_name = "y coordinates"
        nj.units = "m"
        nj.axis = "Y"
        nj[:] = self.yhat

        # fire grid
        firegrid = NewFile.createVariable("XFIRE", np.float64, ("XFIRE"))
        firegrid.comment = "x-fire-dimension"
        firegrid.grid = np.intc(0)
        firegrid.standard_name = "x Fire dimension"
        firegrid.axis = "X"
        firegrid.unit = "m"
        firegrid[:] = self.xfiremesh

        firegrid = NewFile.createVariable("YFIRE", np.float64, ("YFIRE"))
        firegrid.comment = "y-fire-dimension"
        firegrid.grid = np.intc(0)
        firegrid.standard_name = "y Fire dimension"
        firegrid.axis = "Y"
        firegrid.unit = "m"
        firegrid[:] = self.yfiremesh

        # ignition map
        if verbose >= 2:
            print(f">> Store ignition map")

        IgnitionNC = NewFile.createVariable("Ignition", np.float64, ("YFIRE", "XFIRE"))
        IgnitionNC.comment = "Ignition map"
        IgnitionNC.grid = np.intc(4)
        IgnitionNC.standard_name = "Ignition"
        IgnitionNC.long_name = "Ignition time"
        IgnitionNC.units = "s"
        IgnitionNC[:, :] = self.ignitionmaparray

        # walking ignition map
        if verbose >= 2:
            print(f">> Store walking ignition map")
        IgnitionNC = NewFile.createVariable("WalkingIgnition", np.float64, ("YFIRE", "XFIRE"))
        IgnitionNC.comment = "WalkingIgnition map"
        IgnitionNC.grid = np.intc(4)
        IgnitionNC.standard_name = "WalkingIgnition"
        IgnitionNC.long_name = "Walking ignition time"
        IgnitionNC.units = "s"
        IgnitionNC[:, :] = self.walkingignitionmaparray

        # fuel type map
        if verbose >= 2:
            print(f">> Store fuel type map")
        FuelMap = NewFile.createVariable("Fuel01", np.float64, ("YFIRE", "XFIRE"))
        FuelMap.standard_name = "Fuel01"
        FuelMap.long_name = "Fuel type"
        FuelMap.comment = "Fuel type"
        FuelMap.grid = np.intc(4)
        FuelMap.units = "-"
        FuelMap[:, :] = self.fuelmaparray[0, :, :]

        # Write each fuel as 3d table
        if verbose >= 2:
            print(f">> Store properties maps")
        chosen_fuel_class = getattr(
            sys.modules[__name__], _ROSMODEL_FUELCLASS_REGISTER[self.cpropag_model]
        )()
        for propertyname in vars(chosen_fuel_class):
            propertyobj = getattr(chosen_fuel_class, propertyname)
            if propertyobj.propertyindex is not None:
                fuelname = f"Fuel{propertyobj.propertyindex + 1:02d}"
                FuelMap = NewFile.createVariable(fuelname, np.float64, ("YFIRE", "XFIRE"))
                FuelMap.standard_name = fuelname
                FuelMap.long_name = propertyobj.name
                FuelMap.comment = propertyobj.description
                FuelMap.units = propertyobj.unit
                FuelMap.grid = np.intc(4)
                FuelMap[:, :] = self.fuelmaparray[propertyobj.propertyindex, :, :]

        if verbose >= 1:
            print(f">>> Close FuelMap2d.nc")

        NewFile.close()
        self.__show_fuel_index_correspondance()

    def __show_fuel_index_correspondance(self):
        """print fuel index correspondance dict"""
        print("---------- fuel index table ----------")
        print(" Index |             Fuel             ")
        for fuel in self.fuel_index_correspondance.keys():
            print(f"  {self.fuel_index_correspondance[fuel]:3d}  | {fuel}")
        print("--------------------------------------")

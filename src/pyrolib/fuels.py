# -*- coding: utf-8 -*-
""" FuelMap file building tools
"""

import os
import sys
from abc import ABC, abstractmethod
from math import atan, ceil, cos, floor, pow, radians, sin, sqrt
from shutil import copy2

import numpy as np
import pkg_resources
import yaml
from bresenham import bresenham
from netCDF4 import Dataset

try:
    from numba import njit
    has_numba = True
except ImportError:
    has_numba = False
    print('WARNING: Fail to find numba, loop acceleration will be not activated')
    pass


class FuelProperty():
    """ Represents a property for a fuel.

    Store property name, description and value.

    Attributes
    ----------

    name : str
        Short name of the property.
    value : float
        Value of the property.
    unit : str
        Unit of the property in SI (International System of Units).
    description : str
        Short description of the property.
    propertyindex : int, optional
        Index of the property in fuel type class to be correctly read in MesoNH, default is `None`.
        If the `propertyindex` is `None`, the property will not be stored in `FuelMap` file.

        .. note::
           It needs to be compliant with the current version of Blaze.
    """
    def __init__(self, name, value, unit, description, propertyindex=None):
        self.name = name
        self.unit = unit
        self.value = value
        self.description = description
        self.propertyindex = propertyindex

    def set(self, value):
        """ Set value of the property

        Parameters
        ----------

        value : float
            new value of the property
        """
        self.value = float(value)

    def show(self):
        """ Print formatted property information.
        The following format is used:
        Property `name` = `value` [`Unit`] as `description`
        """
        print(f'Property {self.name:>7s} = {self.value:5.3e} [{self.unit:<6s}] as {self.description:s}')

    def minimal_dict(self):
        """ | Construct the minimal dictionnary of the class.
        |  The minimal dictionnay contains the value, the unit and the descrition of the class.

        Returns
        -------
        out : dict
            dictionnary of `value`, `unit` and `description`
        """
        return {'description': self.description, 'unit': self.unit, 'value': self.value}


class BaseFuel(ABC):
    """ Asbtract class for fuel classes.

    A fuel class contains every fuel property of a given fuel type.
    These properties can depend on the rate of spread parameterization used.
    Therefore, the properties are locally defined for each fuel class type (Balbi, Rothermel, ...).
    The rate of spread corresponding the the physical properties and numerical parameters
    of the model can be directly computed in the class by :func:`~pyrolib.fuels.BaseFuel.getR`.
    This method is redefined for each fuel class type.
    """
    @abstractmethod
    def getR(self):
        """ Compute rate of spread for current fuel.

        Raises:
            NotImplementedError: if not defined in the inherited fuel class.
        """
        raise NotImplementedError

    @abstractmethod
    def copy(self):
        """ | Copy current fuel class.
        | It is possible to change any property of the new fuel class.

        Raises:
            NotImplementedError: if not defined in the inherited fuel class.
        """
        raise NotImplementedError

    def _modify_parameter_value(self, **opts):
        """ Modify value as positional argument

        Other Parameters
        ----------------

        **opts :
            any valid fuel property of the considered fuel class
        """
        # get fuel class attributes
        FuelProperties = vars(self)

        # modify accordingly to the opts dict
        for paramtochange in opts.keys():
            # check in the parameter is in attributes
            if paramtochange in FuelProperties.keys():
                FuelProperties[paramtochange].set(opts[paramtochange])

    def print_parameters(self):
        """ Show every property of the fuel.

        List every property of the fuel class and display according to the format of the
        :func:`~pyrolib.fuels.FuelProperty.show` method in the
        :class:`~pyrolib.fuels.FuelProperty` class.
        """
        for param in vars(self).values():
            param.show()

    def copy_from_sequence(self, sequence, index):
        """ | Copy fuel with changes from given sequence containing properties ensemble.
        | `sequence` is `pandas.DataFrame` array with each column corresponding to a property value.
        | The column name shall be the property `name`.

        Parameters
        ----------

        sequence : pandas.DataFrame
            | Sequence of properties to modify in the new fuel class.
            | Each column must correspond to a property of the fuel class.
        index : int
            Index in `sequence` to use.

        Returns
        -------

        NewFuel : same `FuelClass` as `self`
            New `FuelClass` with modified properties according to `sequence`.
        """
        # Create dictionary of parameters
        DictofParam = {}
        for col in sequence.columns:
            DictofParam[col] = sequence.at[index,col]

        return self.copy(**DictofParam)

    def minimal_dict(self, compact: bool):
        """ Construct the minimal dictionnary of the class.

        The minimal dictionnay contains the class name (key: class) and
        the dictionnary of minimal dictionnaries of each :class:`~pyrolib.fuels.FuelProperty` attributes (key: properties).
        If `compact` is `True` then the dictionnary of :class:`~pyrolib.fuels.FuelProperty` attributes `value` are stored instead
        of minimal dicctionnaries.

        Parameters
        ----------

        compact : bool
            If `True`, return

        Returns
        -------

        out : dict
            class name and minimal dictionnaries of class :class:`~pyrolib.fuels.FuelProperty` attributes.
        """
        # initialize properties dictionnary
        propertiesdict = {}

        # get fuel class attributes
        FuelProperties = vars(self)

        # fill minimal dictionnary of the fuel by minimal dictionnary of each property
        if compact:
            for param in FuelProperties.keys():
                propertiesdict[param] = FuelProperties[param].value
        else:
            for param in FuelProperties.keys():
                propertiesdict[param] = FuelProperties[param].minimal_dict()

        minimaldict = {'class': type(self).__name__, 'properties': propertiesdict}
        return minimaldict

    def get_property_vector(self, fuelindex, nbofproperties):
        """ Construct the array of fuel properties value.

        The first index is the fuel index in the scenario, the following content is the value of each fuel property.
        Corresponding index in the array is the `propertyindex` of the :class:`~pyrolib.fuels.FuelProperty`.

        Parameters
        ----------

        fuelindex : int
            Index of fuel to store
        nbofproperties : int
            number

        Returns
        -------

        out : numpy.ndarray
            array of [fuel index, *properties_value]
        """
        PropertyVector = np.zeros(nbofproperties)
        # fuel number in scenario
        PropertyVector[0] = fuelindex
        for parameter in vars(self).values():
            if parameter.propertyindex is not None:
                PropertyVector[parameter.propertyindex] = parameter.value

        return PropertyVector


class BalbiFuel(BaseFuel):
    """ Class of fuel for Balbi rate of spread model [1]_.

    New fuel class is set with default value.
    Any fuel property can be passed explicitely to the constructor to set a different vaklue than the default one.

    Other Parameters
    ----------------

    rhod : float, optional
        Dead fuel density (default: 400 kg m-3)
    rhol : float, optional
        Living fuel density (default: 400 kg m-3)
    Md : float, optional
        Dead fuel moisture (default: 0.1 -)
    Ml : float, optional
        Living fuel moisture (default: 1.0 -)
    sd : float, optional
        Dead SAV ratio (default: 5000 m-1)
    sl : float, optional
        Living SAV ratio (default: 5000 m-1)
    e : float, optional
        Fuel height (default: 1.0 m)
    sigmad : float, optional
        Dead fuel load (default: 0.95 kg m-2)
    sigmal : float, optional
        Living fuel load (default: 0.05 kg m-2)
    Ti : float, optional
        Ignition temperature (default: 500 K)
    Ta : float, optional
        Air temperature (default: 300 K)
    DeltaH : float, optional
        Combustion enthalpy (default: 15.43 MJ kg-1)
    cp : float, optional
        Fuel calorific capacity (default: 1912 J K-1 kg-1)
    Deltah : float, optional
        Water evaporation enthalpy (default: 2.3 MJ kg-1)
    tau0 : float, optional
        Model constant (default: 75590 s m-1)
    rhoa : float, optional
        Air density (default: 1.2 kg m-3)
    X0 : float, optional
        Fraction of radiant energy (default: 0.3 -)
    r00 : float, optional
        Model constant (default: 2.5e-5 -)
    LAI : float, optional
        Leaf Area Index (default: 4 -)
    cpa : float, optional
        Air calorific capacity (default: 1004 J K-1 kg-1)
    stoch : float, optional
        Stochiometry (default: 8.3 -)
    wind : float, optional
        Wind at mid-flame (default 0 m s-1)
    slope : float, optional
        Slope (default: 0 deg)

    References
    ----------
    .. [1] Santoni, P. A., Filippi, J. B., Balbi, J. H., & Bosseur, F. (2011).
           Wildland fire behaviour case studies and fuel models for landscape-scale fire modeling.
           Journal of Combustion, 2011.
           https://doi.org/10.1155/2011/613424

    Examples
    --------

    >>> import pyrolib.fuels as pyf
    >>> # create a new fuel class with default value.
    >>> F1 = pyf.BalbiFuel()
    >>> # create a new fuel class with default value
    >>> # except for `e` and `Md` where a new value is set.
    >>> F2 = pyf.BalbiFuel(e=2, Md=0.1)
    """
    def __init__(self, **opts):
        self.rhod   = FuelProperty(name='rhod',    value=400,      unit='kg m-3',       description='Dead fuel density',            propertyindex=1)
        self.rhol   = FuelProperty(name='rhol',    value=400,      unit='kg m-3',       description='Living fuel density',          propertyindex=2)
        self.Md     = FuelProperty(name='Md',      value=0.1,      unit='-',            description='Dead fuel moisture',           propertyindex=3)
        self.Ml     = FuelProperty(name='Ml',      value=1.,       unit='-',            description='Living fuel moisture',         propertyindex=4)
        self.sd     = FuelProperty(name='sd',      value=5000,     unit='m-1',          description='Dead SAV ratio',               propertyindex=5)
        self.sl     = FuelProperty(name='sl',      value=5000,     unit='m-1',          description='Living SAV ratio',             propertyindex=6)
        self.sigmad = FuelProperty(name='sigmad',  value=0.95,     unit='kg m-2',       description='Dead fuel load',               propertyindex=7)
        self.sigmal = FuelProperty(name='sigmal',  value=0.05,     unit='kg m-2',       description='Living fuel load',             propertyindex=8)
        self.e      = FuelProperty(name='e',       value=1.,       unit='m',            description='Fuel height',                  propertyindex=9)
        self.Ti     = FuelProperty(name='Ti',      value=500,      unit='K',            description='Ignition temperature',         propertyindex=10)
        self.Ta     = FuelProperty(name='Ta',      value=300.,     unit='K',            description='Air temperature',              propertyindex=11)
        self.DeltaH = FuelProperty(name='DeltaH',  value=15.43e6,  unit='J kg-1',       description='Combustion enthalpy',          propertyindex=12)
        self.Deltah = FuelProperty(name='Deltah',  value=2.3e6,    unit='J kg-1',       description='Water evaporation enthalpy',   propertyindex=13)
        self.tau0   = FuelProperty(name='tau0',    value=75590,    unit='s m-1',        description='Model constant',               propertyindex=14)
        self.stoch  = FuelProperty(name='stoch',   value=8.3,      unit='-',            description='Stochiometry',                 propertyindex=15)
        self.rhoa   = FuelProperty(name='rhoa',    value=1.2,      unit='kg m-3',       description='Air density',                  propertyindex=16)
        self.cp     = FuelProperty(name='cp',      value=1912,     unit='J K-1 kg-1',   description='Fuel calorific capacity',      propertyindex=17)
        self.cpa    = FuelProperty(name='cpa',     value=1004,     unit='J K-1 kg-1',   description='Air calorific capacity',       propertyindex=18)
        self.X0     = FuelProperty(name='X0',      value=0.3,      unit='-',            description='Fraction of radiant energy',   propertyindex=19)
        self.LAI    = FuelProperty(name='LAI',     value=4.,       unit='-',            description='Leaf area index',              propertyindex=20)
        self.r00    = FuelProperty(name='r00',     value=2e-5,     unit='-',            description='Model constant',               propertyindex=21)
        self.wind   = FuelProperty(name='wind',    value=0.,       unit='m/s',          description='Wind at mid-flame'                             )
        self.slope  = FuelProperty(name='slope',   value=0.,       unit='deg',          description='Slope'                                         )

        # Modify from default
        self._modify_parameter_value(**opts)

    def copy(self, **opts):
        """ Copy fuel class to a new fuel class object.

        Other Parameters
        ----------------

        **opts : optional
            Any valid property can be passed to change its value for the new object

        Return
        ------

        NewFuel as BalbiFuel

        Examples
        --------

        >>> import pyrolib.fuels as pyf
        >>> # create a new fuel class with default value.
        >>> F1 = pyf.BalbiFuel()
        >>> # copy the fuel class with default value
        >>> # except for `e` and `Md` where a new value is set.
        >>> F2 = F1.copy(e=2, Md=0.1)
        """
        # get dictionary of variable for self and store values in dictionary
        DictOfObjects = vars(self)
        DictOfVars = {}
        for key in DictOfObjects.keys():
            DictOfVars[key] = DictOfObjects[key].value
        # pass dictionary as positional args in constructor for copy
        NewFuel = BalbiFuel(**DictOfVars)
        # modify newfuel parameters with opts positional args
        NewFuel._modify_parameter_value(**opts)
        #
        return NewFuel
    #
    def getR(self):
        """ Compute rate of spread according to Balbi's parameterization ([1]_, [2]_).

        Return
        ------

        R : float
            rate of spread for current fuel properties.

        References
        ----------

        .. [2] Costes, A., Rochoux, M. C., Lac, C., & Masson, V. (2021).
               Subgrid-scale fire front reconstruction for ensemble coupled atmosphere-fire simulations of the FireFlux I experiment.
               Fire Safety Journal, 126, 103475.
               https://doi.org/10.1016/j.firesaf.2021.103475
        """
        # Stefan-Boltzmann constant (from MesoNH computation)
        B = 5.6705085385054376e-08
        Betad = self.sigmad.value / (self.e.value * self.rhod.value)
        Betal = self.sigmal.value / (self.e.value * self.rhol.value)
        Sd = self.sd.value * self.e.value * Betad
        Sl = self.sl.value * self.e.value * Betal
        nu = min(Sd / self.LAI.value, 1.)
        a = self.Deltah.value / (self.cp.value * (self.Ti.value - self.Ta.value))
        # Flame thickness speed factor
        r0 = self.sd.value * self.r00.value
        A0 = (self.X0.value * self.DeltaH.value) / (4.*self.cp.value * (self.Ti.value - self.Ta.value))
        xsi = (self.Ml.value - self.Md.value) * (Sl/Sd) * (self.Deltah.value / self.DeltaH.value)
        # Radiant factor
        A = nu * A0  * (1.-xsi) / (1. + a * self.Md.value)
        # nominal radiant temperature
        T = self.Ta.value + (self.DeltaH.value * (1 - self.X0.value) * (1.-xsi) / (self.cpa.value * (1. + self.stoch.value)))
        R00 = B * pow(T,4) / (self.cp.value * (self.Ti.value - self.Ta.value))
        V00 = 2. * self.LAI.value * (1. + self.stoch.value) * T * self.rhod.value / (self.rhoa.value * self.Ta.value * self.tau0.value)
        v0 = nu * V00
        gamma = radians(self.slope.value) + atan(self.wind.value / v0)
        # no wind no slope ROS
        R0 = self.e.value * R00 / (self.sigmad.value * (1. + a*self.Md.value)) * pow(Sd / (Sd+Sl), 2)
        # test flame angle
        if gamma <= 0.:
            R = R0
        else:
            geomFactor = r0 * (1. + sin(gamma) - cos(gamma)) / cos(gamma)
            Rt = R0 + A * geomFactor - r0 / cos(gamma)
            #
            R = 0.5 * (Rt + sqrt(Rt*Rt + 4.*r0*R0/cos(gamma)))
            #
        #
        return R


class Scenario():
    """ Scenario class

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
    def __init__(self, name='Scenario', longname=None, infos='', load=None):
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
        """ Add fuel to `fuels` dictionnary

        Parameters
        ----------

        fuel : FuelClass
            Fuel to add in the scenario
        """
        # check if fuel is in fuels dict
        k = 1
        nameoffuel = f'{type(fuel).__name__}{k}'
        while nameoffuel in self.fuels.keys():
            k += 1
            nameoffuel = f'{type(fuel).__name__}{k}'
        self.fuels[nameoffuel] = fuel

    def add_fuels(self, *fuels):
        """ Add several fuels to `fuels` dictionnary

        Parameters
        ----------

        fuels : FuelClass
            List of fuels classes of named arguments.
        """
        for fuel in fuels:
            self.add_fuel(fuel)

    def save(self, filename=None, compact=True):
        """ Save scenario fuels in yml file

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
        if filename.endswith('.yml'):
            fname = filename
        else:
            fname = filename + '.yml'

        # create data to store
        minimal_dict_of_fuels = {}
        for fuel in self.fuels.keys():
            minimal_dict_of_fuels[fuel] = self.fuels[fuel].minimal_dict(compact=compact)
        #
        with open(fname, 'w') as ymlfile:
            yaml.dump({'Name':self.name}, ymlfile)
            yaml.dump({'LongName': self.longname}, ymlfile)
            yaml.dump({'Infos': self.infos}, ymlfile)
            yaml.dump({'isCompact': compact}, ymlfile)
            # save minimal dict of each fuel
            yaml.dump({'Fuels': minimal_dict_of_fuels}, ymlfile)
    #
    def load(self, filename=None):
        """ Load scenario fuels from yml file.

        Parameters
        ----------

        filename : str, optional
            Name of the yml file (default: `self.name.yml`).
            If the `filename` does not end with '.yml', the extension is added.
        """
        # check file name
        if filename is None:
            filename = self.name
        if filename.endswith('.yml'):
            fname = filename
        else:
            fname = filename + '.yml'
        # Check default case
        try:
            defaultpath = pkg_resources.resource_stream(__name__, '/'.join(('data/scenario', fname)))
            defaultexists = os.path.exists(defaultpath.name)
        except:
            defaultexists = False
        # Check local path
        localexists = os.path.exists(fname)
        # Select path
        if defaultexists:
            if localexists:
                print(f'INFO : Default case and local case found with same name <{fname}>\nLocal case loaded')
                FilePath = fname
            else:
                print(f'INFO : Default case <{fname}> loaded')
                FilePath = defaultpath.name
        else:
            if localexists:
                print(f'INFO : Local case <{fname}> loaded')
                FilePath = fname
            else:
                print(f'ERROR : file <{fname}> not found in Default cases directory nor local directory')
                FilePath = fname
        # delete existing fuelsLocalExists
        self.Fuels = {}

        # load new fuels
        with open(FilePath, 'r') as ymlfile:
            alldata = yaml.safe_load(ymlfile)
            if 'Name' in alldata.keys():
                self.name = alldata['Name']
            if 'LongName' in alldata.keys():
                self.longname = alldata['LongName']
            if 'Infos' in alldata.keys():
                self.infos = alldata['Infos']

            # read fuels
            if 'Fuels' in alldata.keys():
                if 'isCompact' in alldata.keys():
                    if alldata['isCompact']:
                        for fuel in alldata['Fuels'].keys():
                            self.fuels[fuel] = getattr(sys.modules[__name__], alldata['Fuels'][fuel]['class'])(**alldata['Fuels'][fuel]['properties'])
                        #
                    else:
                        # need to reconstruct properties dictionnary
                        for fuel in alldata['Fuels'].keys():
                            propertiesdict = {}
                            for prop in alldata['Fuels'][fuel]['properties'].keys():
                                propertiesdict[prop] = alldata['Fuels'][fuel]['properties'][prop]['Value']
                            #
                            self.fuels[fuel] = getattr(sys.modules[__name__], alldata['Fuels'][fuel]['class'])(**propertiesdict)
                else:
                    print('ERROR : cannot find file compacity variable: <isCompact> in file. Reading stopped.')
            else:
                print('ERROR : cannot find Fuels in file.')

    def getR(self):
        """ Get rate of spread for each fuel contained in the scenario

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
        """ Show information about scenario.

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
                fuelnb = fuel.replace(type(self.fuels[fuel]).__name__, '')
                fuelclass = fuel.replace(fuelnb, '')
                print(f'Fuel index : {fuelnb}, Fuel class : {fuelclass}, ROS : {self.fuels[fuel].getR():.2f} m/s')
                self.fuels[fuel].print_parameters()
                print('')

        elif verbose == 1:
            # verbose level 1
            # print names and ROS
            for fuel in self.fuels.keys():
                fuelnb = fuel.replace(type(self.fuels[fuel]).__name__, '')
                fuelclass = fuel.replace(fuelnb, '')
                print(f'Fuel index : {fuelnb}, Fuel class : {fuelclass}, ROS : {self.fuels[fuel].getR():.2f} m/s')
        else:
            # verbose level 0 or other
            # only prints names
            for fuel in self.fuels.keys():
                fuelnb = fuel.replace(type(self.fuels[fuel]).__name__, '')
                fuelclass = fuel.replace(fuelnb, '')
                print(f'Fuel index : {fuelnb}, Fuel class : {fuelclass}')


class DataPatch(ABC):
    """ Asbtract class for data patch to build fuel map

    Parameters
    ----------

    fuelmaparray : numpy.ndarray
        Array of acual fuel data (fuel_dim, nyf, nxf)
    """
    def __init__(self, fuelmaparray):
        # Number of fire cells
        self.nxf = np.size(fuelmaparray, 2)
        self.nyf = np.size(fuelmaparray, 1)
        # Mask for data patch
        self.datamask = np.zeros_like((self.nyf, self.nxf))

    @abstractmethod
    def getmask(self):
        raise NotImplementedError


class RectanglePatch(DataPatch):
    """ Class of a rectangle patch of data for fuel map construction

    Parameters
    ----------

    fuelmaparray : numpy.ndarray
        Array of acual fuel data (fuel_dim, nyf, nxf)
    xpos : tuple
        Position on x axis of rectangle corners (x0, x1)
    ypos : tuple
        Position on y axis of rectangle corners (y0, y1)
    xfiremesh : numpy.ndarray
        Fire mesh on x direction (nxf)
    yfiremesh : numpy.ndarray
        Fire mesh on y direction (nyf)
    XFIREMESHSIZE : numpy.ndarray
        Array of fire mesh sizes : [dxf, dyf]
    """
    def __init__(self, fuelmaparray, xpos, ypos, xfiremesh, yfiremesh, XFIREMESHSIZE):
        super().__init__(fuelmaparray)
        self.xpos = xpos
        self.ypos = ypos

        self.datamask = np.zeros((self.nyf, self.nxf))
        self.getmask(xfiremesh, yfiremesh, XFIREMESHSIZE)

    def getmask(self, xfiremesh, yfiremesh, XFIREMESHSIZE):
        """ Compute mask for rectangle patch

        Parameters
        ----------

        xfiremesh : numpy.ndarray
            Fire mesh on x direction (nxf)
        yfiremesh : numpy.ndarray
            Fire mesh on y direction (nyf)
        XFIREMESHSIZE : numpy.ndarray
            Array of fire mesh sizes : [dxf, dyf]
        """
        for i in range(self.nxf):
            for j in range(self.nyf):
                # get x limit
                    if xfiremesh[i] +.5*XFIREMESHSIZE[0] > self.xpos[0] and\
                       xfiremesh[i] -.5*XFIREMESHSIZE[0] < self.xpos[1]:
                        # get y limit
                        if yfiremesh[j] + .5*XFIREMESHSIZE[1] > self.ypos[0] and\
                           yfiremesh[j] - .5*XFIREMESHSIZE[1] < self.ypos[1]:
                            self.datamask[j,i] = 1


class LinePatch(DataPatch):
    """ Class of a rectangle patch of data for fuel map construction

    Parameters
    ----------

    fuelmaparray : numpy.ndarray
        Array of acual fuel data (fuel_dim, nyf, nxf)
    xpos : tuple
        Position on x axis of boundary points (x0, x1)
    ypos : tuple
        Position on y axis of boundary points (y0, y1)
    xfiremesh : numpy.ndarray
        Fire mesh on x direction (nxf)
    yfiremesh : numpy.ndarray
        Fire mesh on y direction (nyf)
    XFIREMESHSIZE : numpy.ndarray
        Array of fire mesh sizes : [dxf, dyf]
    """
    def __init__(self, FuelMapArray, xpos, ypos, xfiremesh, yfiremesh, XFIREMESHSIZE):
        super().__init__(FuelMapArray)
        self.xpos = xpos
        self.ypos = ypos
        self.line = None

        self.datamask = np.zeros((self.nyf, self.nxf))
        self.getmask(xfiremesh, yfiremesh, XFIREMESHSIZE)

    def getmask(self, xfiremesh, yfiremesh, XFIREMESHSIZE):
        """ Compute mask for rectangle patch

        Use breseham algorithm to find all point on fire grid between points A (x0, y0) and B (x1, y1).

        Parameters
        ----------

        xfiremesh : numpy.ndarray
            Fire mesh on x direction (nxf)
        yfiremesh : numpy.ndarray
            Fire mesh on y direction (nyf)
        XFIREMESHSIZE : numpy.ndarray
            Array of fire mesh sizes : [dxf, dyf]
        """
        # Set base index for position of (x0, y0) and (x1, y1)
        # ie                              i0, j0       i1, j1
        i0 = 0
        j0 = 0
        i1 = 0
        j1 = 0
        # find indexes
        for i in range(self.nxf):
            for j in range(self.nyf):
                # find (x0, y0)
                if xfiremesh[i] - .5*XFIREMESHSIZE[0] <= self.xpos[0] and \
                   xfiremesh[i] + .5*XFIREMESHSIZE[0] >  self.xpos[0] and \
                   yfiremesh[j] - .5*XFIREMESHSIZE[1] <= self.ypos[0] and \
                   yfiremesh[j] + .5*XFIREMESHSIZE[1] >  self.ypos[0]:
                    i0 = i
                    j0 = j

                # find (x1, y1)
                if xfiremesh[i] - .5*XFIREMESHSIZE[0] <= self.xpos[1] and \
                   xfiremesh[i] + .5*XFIREMESHSIZE[0] >  self.xpos[1] and \
                   yfiremesh[j] - .5*XFIREMESHSIZE[1] <= self.ypos[1] and \
                   yfiremesh[j] + .5*XFIREMESHSIZE[1] >  self.ypos[1]:
                    i1 = i
                    j1 = j

        # Use bresenham algorithm to get all points between (x0, y0) and (x1, y1)
        self.line = list(bresenham(i0, j0, i1, j1))
        # mask only these points
        for ind in self.line:
            self.datamask[ind[1], ind[0]] = 1


class FuelMap():
    """ Class for fuel map construction

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

    scenario : pyrolib.fuels.Scenario
        Scenario containing fuel data.
    namelistname : str, optional
        MesoNH namelist name (default: 'EXSEG1.nam').
    MesoNHversion : str, optional
            Version of MesoNH needed (>=5.4.4) (default: '5.5.0')


    """
    def __init__(self, scenario: Scenario, namelistname='EXSEG1.nam', MesoNHversion: str = '5.5.0'):
        self.scenario = scenario
        self.namelist = namelistname
        self.mnh_version = MesoNHversion

        # Read default values for MNHBLAZE namelist from Default_MNH_namelist.yml
        # Values should be compliant with default_desfmn.f90
        defaultpath = pkg_resources.resource_stream(__name__, '/'.join(('data', 'Default_MNH_namelist.yml')))
        with open(defaultpath.name, 'r') as ymlfile:
            alldata = yaml.safe_load(ymlfile)
        current_version = f"v{self.mnh_version.replace('.', '')}"

        self.MNHinifile = alldata[current_version]['MNHinifile']
        self.cpropag_model = alldata[current_version]['cpropag_model']
        self.nrefinx = alldata[current_version]['nrefinx']
        self.nrefiny = alldata[current_version]['nrefiny']

        # Default values
        self.xfiremeshsize = np.array([0, 0])   # Fire mesh size (dxf, dyf)
        self.firemeshsizes = None
        self.xfiremesh = None
        self.yfiremesh = None
        self.nx = 0
        self.ny = 0

        self.__get_info_from_namelist()

        self.nbpropertiesfuel = _ROSMODEL_NB_PROPERTIES[self.cpropag_model]
        # allocate fuel data array
        self.fuelmaparray               = np.zeros((self.nbpropertiesfuel, self.firemeshsizes[1], self.firemeshsizes[0]))
        self.ignitionmaparray           = 1e6 * np.zeros((self.firemeshsizes[1], self.firemeshsizes[0]))
        self.walkingignitionmaparray    = -1. * np.ones_like(self.ignitionmaparray)

    def __get_info_from_namelist(self):
        """ Retrieve informations on the MesoNH-Blaze run from namelist and initialization file
        """
        projectpath = os.getcwd()
        # Check if Namelist exists
        if not os.path.exists(f'{projectpath:s}/{self.namelist:s}'):
            raise IOError(f'File {self.namelist:s} not found')

        # get MNH init file name
        with open(f'{projectpath:s}/{self.namelist:s}') as F1:
            text = F1.readlines()
            for line in text:
                # delete spaces ans separation characters
                line = ''.join(line.split())
                line = line.replace(',', '')
                line = line.replace('/', '')
                # Check parameters in namelist
                if 'INIFILE=' in line:
                    self.mnhinifile = line.split('INIFILE=')[-1].split("'")[1]
                if 'CPROPAG_MODEL=' in line:
                    self.cpropag_model = line.split('CPROPAG_MODEL=')[-1].split("'")[1]
                if 'NREFINX=' in line:
                    self.nrefinx = int(line.split('NREFINX=')[-1])
                if 'NREFINY=' in line:
                    self.nrefiny = int(line.split('NREFINY=')[-1])
        #
        # Check if INIFILE.des exists
        if not os.path.exists(f'{projectpath:s}/{self.mnhinifile:s}.des'):
            raise IOError(f'File {self.mnhinifile:s}.des not found')
        # Check if INIFILE.nc exists
        if not os.path.exists(f'{projectpath:s}/{self.mnhinifile:s}.nc'):
            raise IOError(f'File {self.mnhinifile:s}.nc not found')

        # Import XHAT and YHAT
        MNHData = Dataset(f'{projectpath:s}/{self.mnhinifile:s}.nc')
        self.xhat = MNHData.variables['XHAT'][:]
        self.yhat = MNHData.variables['YHAT'][:]
        MNHData.close()
        # get sizes
        self.nx = len(self.xhat)
        self.ny = len(self.yhat)

        self.xfiremeshsize[0] = float(self.xhat[1]-self.xhat[0]) / float(self.nrefinx)
        self.xfiremeshsize[1] = float(self.yhat[1]-self.yhat[0]) / float(self.nrefinx)
        self.firemeshsizes = [self.nx * self.nrefinx, self.ny * self.nrefiny]
        # Get mesh position of fuel cells
        self.xfiremesh = np.linspace(self.xhat[0], self.xhat[-1] + (self.xhat[1]-self.xhat[0]), self.nx * self.nrefinx, endpoint=False)
        self.xfiremesh += .5 * (self.xfiremesh[1]-self.xfiremesh[0])

        self.yfiremesh = np.linspace(self.yhat[0], self.yhat[-1] + (self.yhat[1]-self.yhat[0]), self.ny * self.nrefiny, endpoint=False)
        self.yfiremesh += .5 * (self.yfiremesh[1]-self.yfiremesh[0])

    def addRectanglePatch(self, xpos: tuple, ypos: tuple,
                          fuelindex: int = None,
                          ignitiontime: float = None,
                          unburnable: bool = None):
        """ Add rectangle patch between (xpos[0], ypos[0]) and (xpos[1], ypos[1]).

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

        xpos : tuple
            Position of west and east boundaries of the patch
        ypos : tuple
            Position of south and north boundaries of the patch
        FuelIndex : int, optional
            Index of Fuel in Scenario to place in the patch (default: `None`)
        IgnitionTime : float, optional
            Ignition time of patch (default: `None`)
        Unburnable : bool, optional
            Flag to set patch as a non burnable area (default: `None`)
        """
        # Create mask
        P = RectanglePatch(self.fuelmaparray, xpos, ypos, self.xfiremesh, self.yfiremesh, self.xfiremeshsize)

        # assign data
        self.__assign_data_to_data_array(P, fuelindex, None, ignitiontime, unburnable)

    def addLinePatch(self, xpos: tuple, ypos: tuple,
                     fuelindex: int = None,
                     walkingignitiontimes: list = None,
                     ignitiontime: float = None,
                     unburnable: bool = None):
        """ Add line patch between (xpos[0], ypos[0]) and (xpos[1], ypos[1]).

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

        xpos : tuple
            Position of west and east boundaries of the patch
        ypos : tuple
            Position of south and north boundaries of the patch
        FuelIndex : int, optional
            Index of Fuel in Scenario to place in the patch (default: `None`)
        IgnitionTime : float, optional
            Ignition time of patch (default: `None`)
        Unburnable : bool, optional
            Flag to set patch as a non burnable area (default: `None`)
        """
        # Create mask
        P = LinePatch(self.fuelmaparray, xpos, ypos, self.xfiremesh, self.yfiremesh, self.xfiremeshsize)

        # # assign data
        self.__assign_data_to_data_array(P, fuelindex, walkingignitiontimes, ignitiontime, unburnable)

    def __assign_data_to_data_array(self,
                                    patch: DataPatch,
                                    fuelindex: int = None,
                                    walkingignitiontimes: tuple = None,
                                    ignitiontime: float = None,
                                    unburnable: bool = None):
        """
        This function assigns data as a function of argument passed

        4 types of data can be allocated in the patch:
            - Fuel properties
                Select a fuel number (it should be contained in the Scenario object loaded in the FuelMap object).
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
        if isinstance(fuelindex, int):
            # check if needed fuel (corresponding fuel class and number of FuelIndex)
            fuelname = f'{_ROSMODEL_FUELCLASS_REGISTER[self.cpropag_model]}{fuelindex}'
            if fuelname in self.scenario.fuels.keys():
                # create property vector for this fuel
                propvector = self.scenario.fuels[fuelname].get_property_vector(fuelindex, self.nbpropertiesfuel)
                self.fuelmaparray = fill_fuel_array_from_patch(self.fuelmaparray, patch.datamask,
                                                           propvector, self.nbpropertiesfuel,
                                                           self.firemeshsizes[0],
                                                           self.firemeshsizes[1])
            else:
                print(f'Fuel {fuelname} Not found in Scenario. Nothing appended')
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
                dist = sqrt(pow(self.xfiremesh[ind[0]] - patch.xpos[0], 2) + pow(self.yfiremesh[ind[1]] - patch.ypos[0], 2))
                # linear interpolation
                self.walkingignitionmaparray[ind[1], ind[0]] = walkingignitiontimes[0] + dist * ignitiondt / totaldist
            return

        # case 3 : ignition of whole patch is set
        if ignitiontime is not None:
            self.ignitionmaparray[patch.datamask == 1] = ignitiontime
            return

        # case 4 : Unburnable is set
        if unburnable is not None:
            # create property vector of 0
            propvector = np.zeros(self.nbpropertiesfuel)
            self.fuelmaparray = fill_fuel_array_from_patch(self.fuelmaparray, patch.datamask,
                                                       propvector, self.nbpropertiesfuel,
                                                       self.firemeshsizes[0],
                                                       self.firemeshsizes[1])
            return
        print('WARNING: No information given on what to do. Nothing done')

    def write(self, save2dfile: bool = False, verbose: int = 0):
        """ Write Fuel map as netCFD file named FuelMap.nc

        Parameters
        ----------

        save2dfile : bool, optional
            Flag to save 2d version of FuelMap (easier to check fuelmap construction) (default: False)
        verbose : int, optional
            verbose level (0: no prints, 1: low verbosity, 2: high verbosity) (default: 0)
        """
        projectpath = os.getcwd()

        # copy .des file
        copy2(f'{projectpath:s}/{self.mnhinifile:s}.des', f'{projectpath:s}/FuelMap.des')

        # Create new netcdf file to store fuel data
        if verbose >= 1:
            print(f'>>> Create FuelMap.nc')

        NewFile = Dataset(f'{projectpath:s}/FuelMap.nc', 'w')

        if verbose >= 2:
            print(f'>> Store MesoNH file info')

        # need to be compliant with MesoNH output files nomenclature
        NewFile.Conventions = 'CF-1.7 COMODO-1.4'
        NewFile.MNH_REAL = '8'
        NewFile.MNH_INT = '4'
        NewFile.MNH_cleanly_closed = 'yes'

        NewFile.createDimension('X', self.nx)
        NewFile.createDimension('Y', self.ny)
        NewFile.createDimension('F', self.nrefinx * self.nrefiny)
        NewFile.createDimension('size3', 3)
        NewFile.createDimension('char16', 16)

        MNHversion = np.array(self.mnh_version.split('.'), dtype=np.int)
        varia = NewFile.createVariable('MNHVERSION', int, ('size3'), fill_value=-2147483647)
        varia.long_name = 'MesoNH version'
        varia.valid_min = np.intc(-2147483646)
        varia.valid_max = np.intc(2147483647)
        varia[:] = MNHversion

        varia = NewFile.createVariable('MASDEV', int, ())
        varia.long_name = 'MesoNH version (without bugfix)'
        varia = MNHversion[0]

        varia = NewFile.createVariable('BUGFIX', int, ())
        varia.long_name = 'MesoNH bugfix number'
        varia = MNHversion[1]

        varia = NewFile.createVariable('STORAGE_TYPE', 'c', ('char16'))
        varia.long_name = 'STORAGE_TYPE'
        varia.comment = 'Storage type for the information written in the FM files'
        varia[:] = 'TT              '

        varia = NewFile.createVariable('FILETYPE', 'c', ('char16'))
        varia.long_name = 'type of this file'
        varia[:] = 'BlazeData       '

        # x grid
        if verbose >= 2:
            print(f'>> Store grid')

        ni = NewFile.createVariable('X', np.float64, ('X'))
        ni.COMMENT = 'x-dimension'
        ni.GRID = np.intc(0)
        ni.standard_name = 'x coordinates'
        ni.units = 'm'
        ni.axis = 'X'
        ni[:] = self.xhat

        # y grid
        nj = NewFile.createVariable('Y', np.float64, ('Y'))
        nj.COMMENT = 'y-dimension'
        nj.GRID = np.intc(0)
        nj.standard_name = 'y coordinates'
        nj.units = 'm'
        nj.axis = 'Y'
        nj[:] = self.yhat

        # fire grid
        firelevel = NewFile.createVariable('F', np.float64, ('F'))
        firelevel.COMMENT = 'fire-dimension'
        firelevel.GRID = np.intc(0)
        firelevel.standard_name = 'Fire dimension'
        firelevel.axis = 'F'
        firelevel[:] = np.array(np.arange(0, self.nrefinx * self.nrefiny), dtype=np.float64)

        # ignition map
        if verbose >= 2:
            print(f'>> Store ignition map')

        IgnitionNC = NewFile.createVariable('Ignition', np.float64, ('F', 'Y', 'X'))
        IgnitionNC.COMMENT = 'Ignition map'
        IgnitionNC.GRID = np.intc(4)
        IgnitionNC.standard_name = 'Ignition'
        IgnitionNC[:,:,:] = fire_array_2d_to_3d(self.ignitionmaparray, self.nx, self.ny, self.nrefinx, self.nrefiny)

        # walking ignition map
        if verbose >= 2:
            print(f'>> Store walking ignition map')
        IgnitionNC = NewFile.createVariable('WalkingIgnition', np.float64, ('F', 'Y', 'X'))
        IgnitionNC.COMMENT = 'WalkingIgnition map'
        IgnitionNC.GRID = np.intc(4)
        IgnitionNC.standard_name = 'WalkingIgnition'
        IgnitionNC[:,:,:] = fire_array_2d_to_3d(self.walkingignitionmaparray, self.nx, self.ny, self.nrefinx, self.nrefiny)

        # fuel type map
        if verbose >= 2:
            print(f'>> Store fuel type map')
        FuelMap = NewFile.createVariable('Fuel01', np.float64, ('F','Y','X'))
        FuelMap.COMMENT = 'Fuel type'
        FuelMap.GRID = np.intc(4)
        FuelMap[:,:,:] = fire_array_2d_to_3d(self.fuelmaparray[0,:,:], self.nx, self.ny, self.nrefinx, self.nrefiny)

        # Write each fuel as 3d table
        if verbose >= 2:
            print(f'>> Store properties maps')
        BaseFuelname = f'{_ROSMODEL_FUELCLASS_REGISTER[self.cpropag_model]}1'
        for propertyname in vars(self.scenario.fuels[BaseFuelname]):
            propertyobj = getattr(self.scenario.fuels[BaseFuelname], propertyname)
            if propertyobj.propertyindex is not None:
                FuelMap = NewFile.createVariable(f'Fuel{propertyobj.propertyindex + 1:02d}', np.float64, ('F','Y','X'))
                FuelMap.standard_name = propertyobj.name
                FuelMap.COMMENT = propertyobj.description
                FuelMap.units = propertyobj.unit
                FuelMap.GRID = np.intc(4)
                FuelMap[:,:,:] = fire_array_2d_to_3d(self.fuelmaparray[propertyobj.propertyindex,:,:], self.nx, self.ny, self.nrefinx, self.nrefiny)

        if verbose >= 1:
            print(f'>>> Close FuelMap.nc')

        NewFile.close()

        # Create 2d file
        if save2dfile:
            if verbose >= 1:
                print(f'>>> Create FuelMap2d.nc')

            NewFile = Dataset(f'{projectpath:s}/FuelMap2d.nc', 'w')

            if verbose >= 2:
                print(f'>> Store MesoNH file info')

            # need to be compliant with MesoNH output files nomenclature
            NewFile.Conventions = 'CF-1.7 COMODO-1.4'
            NewFile.MNH_REAL = '8'
            NewFile.MNH_INT = '4'
            NewFile.MNH_cleanly_closed = 'yes'

            NewFile.createDimension('X', self.nx)
            NewFile.createDimension('Y', self.ny)
            NewFile.createDimension('XFIRE', self.nx * self.nrefinx)
            NewFile.createDimension('YFIRE', self.ny * self.nrefiny)
            NewFile.createDimension('size3', 3)
            NewFile.createDimension('char16', 16)

            MNHversion = np.array(self.mnh_version.split('.'), dtype=np.int)
            varia = NewFile.createVariable('MNHVERSION', int, ('size3'), fill_value=-2147483647)
            varia.long_name = 'MesoNH version'
            varia.valid_min = np.intc(-2147483646)
            varia.valid_max = np.intc(2147483647)
            varia[:] = MNHversion

            varia = NewFile.createVariable('MASDEV', int, ())
            varia.long_name = 'MesoNH version (without bugfix)'
            varia = MNHversion[0]

            varia = NewFile.createVariable('BUGFIX', int, ())
            varia.long_name = 'MesoNH bugfix number'
            varia = MNHversion[1]

            varia = NewFile.createVariable('STORAGE_TYPE', 'c', ('char16'))
            varia.long_name = 'STORAGE_TYPE'
            varia.comment = 'Storage type for the information written in the FM files'
            varia[:] = 'TT              '

            varia = NewFile.createVariable('FILETYPE', 'c', ('char16'))
            varia.long_name = 'type of this file'
            varia[:] = 'BlazeData       '

            # x grid
            if verbose >= 2:
                print(f'>> Store grid')

            ni = NewFile.createVariable('X', np.float64, ('X'))
            ni.COMMENT = 'x-dimension'
            ni.GRID = np.intc(0)
            ni.standard_name = 'x coordinates'
            ni.units = 'm'
            ni.axis = 'X'
            ni[:] = self.xhat

            # y grid
            nj = NewFile.createVariable('Y', np.float64, ('Y'))
            nj.COMMENT = 'y-dimension'
            nj.GRID = np.intc(0)
            nj.standard_name = 'y coordinates'
            nj.units = 'm'
            nj.axis = 'Y'
            nj[:] = self.yhat

            # fire grid
            firegrid = NewFile.createVariable('XFIRE', np.float64, ('XFIRE'))
            firegrid.COMMENT = 'x-fire-dimension'
            firegrid.GRID = np.intc(0)
            firegrid.standard_name = 'x Fire dimension'
            firegrid.axis = 'X'
            firegrid.unit = 'm'
            firegrid[:] = self.xfiremesh

            firegrid = NewFile.createVariable('YFIRE', np.float64, ('YFIRE'))
            firegrid.COMMENT = 'y-fire-dimension'
            firegrid.GRID = np.intc(0)
            firegrid.standard_name = 'y Fire dimension'
            firegrid.axis = 'Y'
            firegrid.unit = 'm'
            firegrid[:] = self.yfiremesh

            # ignition map
            if verbose >= 2:
                print(f'>> Store ignition map')

            IgnitionNC = NewFile.createVariable('Ignition', np.float64, ('YFIRE', 'XFIRE'))
            IgnitionNC.COMMENT = 'Ignition map'
            IgnitionNC.GRID = np.intc(4)
            IgnitionNC.standard_name = 'Ignition'
            IgnitionNC[:,:] = self.ignitionmaparray

            # walking ignition map
            if verbose >= 2:
                print(f'>> Store walking ignition map')
            IgnitionNC = NewFile.createVariable('WalkingIgnition', np.float64, ('YFIRE', 'XFIRE'))
            IgnitionNC.COMMENT = 'WalkingIgnition map'
            IgnitionNC.GRID = np.intc(4)
            IgnitionNC.standard_name = 'WalkingIgnition'
            IgnitionNC[:,:] = self.walkingignitionmaparray

            # fuel type map
            if verbose >= 2:
                print(f'>> Store fuel type map')
            FuelMap = NewFile.createVariable('Fuel01', np.float64, ('YFIRE', 'XFIRE'))
            FuelMap.COMMENT = 'Fuel type'
            FuelMap.GRID = np.intc(4)
            FuelMap[:,:] = self.fuelmaparray[0,:,:]

            # Write each fuel as 3d table
            if verbose >= 2:
                print(f'>> Store properties maps')
            basefuelname = f'{_ROSMODEL_FUELCLASS_REGISTER[self.cpropag_model]}1'
            for propertyname in vars(self.scenario.fuels[basefuelname]):
                propertyobj = getattr(self.scenario.fuels[basefuelname], propertyname)
                if propertyobj.propertyindex is not None:
                    FuelMap = NewFile.createVariable(f'Fuel{propertyobj.propertyindex + 1:02d}', np.float64, ('YFIRE', 'XFIRE'))
                    FuelMap.standard_name = propertyobj.name
                    FuelMap.COMMENT = propertyobj.description
                    FuelMap.UNITS = propertyobj.unit
                    FuelMap.GRID = np.intc(4)
                    FuelMap[:,:] = self.fuelmaparray[propertyobj.propertyindex,:,:]

            if verbose >= 1:
                print(f'>>> Close FuelMap2d.nc')

            NewFile.close()


def checknjit(function):
    if has_numba:
        return njit()(function)
    else:
        return function

@checknjit
def fill_fuel_array_from_patch(fuelarray, patchmask, propertyvector, np, nx, ny):
    """ Fill fuel array considering a mask

    Parameters
    ----------

    fuelarray : numpy.ndarray
        Array to modify according to `propertyvector` and `patchmask`.
    patchmask : numpy.ndarray
        Mask array.
    propertyvector : numpy.ndarray
        Vector of properties to fill in the fuel array.
    np : int
        Property vector size
    nx : int
        Fire mesh size on x axis
    ny : int
        Fire mesh size on y axis

    Returns
    -------

    fuelarray : numpy.ndarray
        Modified array according to `propertyvector` and `patchmask`.
    """
    # property loop
    for k in range(np):
        # y axis loop
        for j in range(ny):
            # x axis loop
            for i in range(nx):
                # check mask value
                if patchmask[j,i] == 1:
                    fuelarray[k,j,i] = propertyvector[k]
    return fuelarray


@checknjit
def fire_array_2d_to_3d(firearray2d, nx, ny, gammax, gammay):
    """Reshape 2d fire array into 3d fire array readable by MesoNH

    Parameters
    ----------
    firearray2d : numpy.ndarray
        2d array to reshape
    nx : int
        Fire mesh size on x axis
    ny : int
        Fire mesh size on y axis
    gammax : int
        Fire mesh refinement on x axis
    gammay : int
        Fire mesh refinement on x axis

    Returns
    -------
    firearray3d : numpy.ndarray
        Reshaped 3d array
    """
    farray3d = np.zeros((gammax * gammay, ny, nx))
    for m in range(1, ny*gammay + 1):
        for l in range(1, nx*gammax+1):
            # compute i,j,k
            i = ceil(float(l)/float(gammax))
            j = ceil(float(m)/float(gammay))
            a = l - (i-1) * gammax
            b = m - (j-1) * gammay
            k = (b-1) * gammax + a

            # fill tables
            farray3d[k-1,j-1,i-1] = firearray2d[m-1,l-1]
    return farray3d


@checknjit
def fire_array_3d_to_2d(firearray3d, nx, ny, gammax, gammay):
    """Reshape 3d fire array readable by MesoNH to 2d fire array

    Parameters
    ----------
    firearray3d : numpy.ndarray
        3d array to reshape
    nx : int
        Fire mesh size on x axis
    ny : int
        Fire mesh size on y axis
    gammax : int
        Fire mesh refinement on x axis
    gammay : int
        Fire mesh refinement on x axis

    Returns
    -------
    firearray2d : numpy.ndarray
        Reshaped 2d array
    """
    farray2d = np.zeros((ny*gammay, nx*gammax))
    for k in range(1, gammax*gammay + 1):
            b = floor((k-1) / gammax) + 1
            a = k - (b-1) * gammax
            for j in range(1, ny + 1):
                m = (j-1) * gammay + b
                for i in range(1, nx + 1):
                    l = (i - 1) * gammax + a
                    farray2d[m-1,l-1] = firearray3d[k-1, j-1, i-1]
    return farray2d


_ROSMODEL_NB_PROPERTIES = {
    "SANTONI2011": 22,
}


_ROSMODEL_FUELCLASS_REGISTER = {
    "SANTONI2011": type(BalbiFuel()).__name__,
}


def show_fuel_classes():
    """Print fuel classes available in pyrolib and default parameters values
    """
    # Balbi
    print(f"\n{type(BalbiFuel()).__name__} class is compliant with Balbi's ROS parameterization.")
    print("It contains the following properties with default value:")
    BalbiFuel().print_parameters()
    print("")


def show_default_scenario():
    """List every scenario file in data/scenario directory
    """
    data_dir_content = pkg_resources.resource_listdir(__name__, "data/scenario")
    print("The following scenario have been found in the default scenario directory:")
    for file in data_dir_content:
        if file.endswith('.yml'):
            print(f"* {file.replace('.yml','')}")
    print("")
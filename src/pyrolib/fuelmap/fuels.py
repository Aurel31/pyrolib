""" Fuel classes
"""

from abc import ABC, abstractmethod
from math import atan, cos, pow, radians, sin, sqrt
import numpy as np


class FuelProperty:
    """Represents a property for a fuel.

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
        """Set value of the property

        Parameters
        ----------

        value : float
            new value of the property
        """
        self.value = float(value)

    def __str__(self) -> str:
        """Print formatted property information.
        The following format is used:
        Property `name` = `value` [`Unit`] as `description`
        """
        return f"Property {self.name:>7s} = {self.value:5.3e} [{self.unit:<6s}] as {self.description:s}"

    def minimal_dict(self):
        """| Construct the minimal dictionnary of the class.
        |  The minimal dictionnay contains the value, the unit and the descrition of the class.

        Returns
        -------
        out : dict
            dictionnary of `value`, `unit` and `description`
        """
        return {"description": self.description, "unit": self.unit, "value": self.value}


class BaseFuel(ABC):
    """Asbtract class for fuel classes.

    A fuel class contains every fuel property of a given fuel type.
    These properties can depend on the rate of spread parameterization used.
    Therefore, the properties are locally defined for each fuel class type (Balbi, Rothermel, ...).
    The rate of spread corresponding the the physical properties and numerical parameters
    of the model can be directly computed in the class by :func:`~pyrolib.fuels.BaseFuel.getR`.
    This method is redefined for each fuel class type.
    """

    @abstractmethod
    def getR(self):
        """Compute rate of spread for current fuel.

        Raises:
            NotImplementedError: if not defined in the inherited fuel class.
        """
        raise NotImplementedError

    @abstractmethod
    def copy(self):
        """| Copy current fuel class.
        | It is possible to change any property of the new fuel class.

        Raises:
            NotImplementedError: if not defined in the inherited fuel class.
        """
        raise NotImplementedError

    def _modify_parameter_value(self, **opts):
        """Modify value as positional argument

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

    def __str__(self) -> str:
        """Show every property of the fuel.

        List every property of the fuel class and display according to the format of the
        :func:`~pyrolib.fuels.FuelProperty.show` method in the
        :class:`~pyrolib.fuels.FuelProperty` class.
        """
        out = f"{type(self).__name__} properties:\n"
        for param in vars(self).values():
            out += f"  {param.__str__()}\n"
        return out

    def copy_from_sequence(self, sequence, index):
        """| Copy fuel with changes from given sequence containing properties ensemble.
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
            DictofParam[col] = sequence.at[index, col]

        return self.copy(**DictofParam)

    def minimal_dict(self, compact: bool):
        """Construct the minimal dictionnary of the class.

        The minimal dictionnay contains the class name (key: class) and
        the dictionnary of minimal dictionnaries of each :class:`~pyrolib.fuels.FuelProperty` attributes (key: properties).
        If `compact` is `True` then the dictionnary of :class:`~pyrolib.fuels.FuelProperty` attributes `value`
        are stored instead
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

        minimaldict = {"class": type(self).__name__, "properties": propertiesdict}
        return minimaldict

    def get_property_vector(self, fuelindex, nbofproperties):
        """Construct the array of fuel properties value.

        The fuel index is an identifier of the fuel, the following content is the value of each fuel property.
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
        PropertyVector[0] = fuelindex
        for parameter in vars(self).values():
            if parameter.propertyindex is not None:
                PropertyVector[parameter.propertyindex] = parameter.value

        return PropertyVector


class BalbiFuel(BaseFuel):
    """Class of fuel for Balbi rate of spread model [1]_.

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
        # fmt: off
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
        self.wind   = FuelProperty(name='wind',    value=0.,       unit='m/s',          description='Wind at mid-flame')
        self.slope  = FuelProperty(name='slope',   value=0.,       unit='deg',          description='Slope')
        # fmt: on
        # Modify from default
        self._modify_parameter_value(**opts)

    def copy(self, **opts):
        """Copy fuel class to a new fuel class object.

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
        """Compute rate of spread according to Balbi's parameterization ([1]_, [2]_).

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
        nu = min(Sd / self.LAI.value, 1.0)
        a = self.Deltah.value / (self.cp.value * (self.Ti.value - self.Ta.value))
        # Flame thickness speed factor
        r0 = self.sd.value * self.r00.value
        A0 = (self.X0.value * self.DeltaH.value) / (4.0 * self.cp.value * (self.Ti.value - self.Ta.value))
        xsi = (self.Ml.value - self.Md.value) * (Sl / Sd) * (self.Deltah.value / self.DeltaH.value)
        # Radiant factor
        A = nu * A0 * (1.0 - xsi) / (1.0 + a * self.Md.value)
        # nominal radiant temperature
        T = self.Ta.value + (
            self.DeltaH.value
            * (1 - self.X0.value)
            * (1.0 - xsi)
            / (self.cpa.value * (1.0 + self.stoch.value))
        )
        R00 = B * pow(T, 4) / (self.cp.value * (self.Ti.value - self.Ta.value))
        V00 = (
            2.0
            * self.LAI.value
            * (1.0 + self.stoch.value)
            * T
            * self.rhod.value
            / (self.rhoa.value * self.Ta.value * self.tau0.value)
        )
        v0 = nu * V00
        gamma = radians(self.slope.value) + atan(self.wind.value / v0)
        # no wind no slope ROS
        R0 = self.e.value * R00 / (self.sigmad.value * (1.0 + a * self.Md.value)) * pow(Sd / (Sd + Sl), 2)
        # test flame angle
        if gamma <= 0.0:
            R = R0
        else:
            geomFactor = r0 * (1.0 + sin(gamma) - cos(gamma)) / cos(gamma)
            Rt = R0 + A * geomFactor - r0 / cos(gamma)
            #
            R = 0.5 * (Rt + sqrt(Rt * Rt + 4.0 * r0 * R0 / cos(gamma)))
            #
        #
        return R


_ROSMODEL_NB_PROPERTIES = {
    "SANTONI2011": 22,
}


_ROSMODEL_FUELCLASS_REGISTER = {
    "SANTONI2011": type(BalbiFuel()).__name__,
}


def show_fuel_classes(show_fuel_properties=True):
    """Print fuel classes available in pyrolib and default parameters values"""
    # Balbi
    print("\nMore information about fuel classes:")
    print(f"* < {type(BalbiFuel()).__name__} > class is compliant with the Balbi's ROS parameterization.")
    print(f"  It is used when < CPROPAG_MODEL = SANTONI2011 > in the Méso-NH namelist.")
    if show_fuel_properties:
        print("It contains the following properties with default value:")
        print(BalbiFuel())
    print()

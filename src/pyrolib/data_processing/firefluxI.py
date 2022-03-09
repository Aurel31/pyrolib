"""Post-processing of FireFlux I raw data
"""

from datetime import datetime, timedelta
import csv
import numpy as np

_MTHeight = [0.1, 0.5, 0.75, 2, 4.5, 10, 15, 20, 25, 28, 30, 35, 43, 0.13, 1.47, 2.1]
_DataFileName = "tc_data_1hz_3.dat"

FireFluxDataPath = "FireFlux_Raw"


def set_data_path(path):
    """Set path to FireFlux I data directory.

    The data directory should contains:

    .. code-block:: text

        FireFlux_Raw/
        ├── FireFlux_North_weatherstation_data.xls
        ├── FireFlux_radiosonde_022306_0655CST.xls
        ├── orography_25m_src.dat
        ├── Pfit_MT10m_FEB23_H12-13_1s.dat
        ├── Pfit_MT28m_FEB23_H12-13_1s.dat
        ├── Pfit_MT2m_FEB23_H12-13_1s.dat
        ├── Pfit_MT42m_FEB23_H12-13_1s.dat
        ├── Pfit_readme.doc
        ├── Pfit_ST10m_FEB23_H12-13_1s.dat
        ├── Pfit_ST2m_FEB23_H12-13_1s.dat
        ├── RP_FireFlux1_NEW.mov
        ├── tc_data_1hz_1.xls
        ├── tc_data_1hz_2.txt
        ├── tc_data_1hz_3.dat
        ├── tethersonde_readme.doc
        ├── tower_pro.mov
        ├── Y2524035_02.1-min.m.txt
        ├── Y2524036_03.1-min.m.txt
        ├── Y2524064_04.1-min.m.txt
        ├── Y2524067_01.1-min.m.txt
        └── Y2524068_05.1-min.m.txt

    Parameters
    ----------
    path : str
        Path to FireFlux I data directory
    """
    global FireFluxDataPath
    FireFluxDataPath = path


def datetime2seconds(listofdate, startingdatetime):
    """Convert a list of datetime to seconds from a strating datetime

    Parameters
    ----------
    listofdate : list of datetime
        List of datetime to convert to seconds.
    startingpoint : datetime
        Starting datetime.

    Returns
    -------
    SpanSec : list of float
        List of seconds elapsed since startingdatetime
    """
    SpanSec = np.zeros_like(listofdate)
    for i, date in enumerate(listofdate):
        Span = date - startingdatetime
        SpanSec[i] = Span.total_seconds()
    return SpanSec


class SonicTower:
    """Sonic anemometer data extraction class

    Extraction of Main Tower (MT) and Small Tower (ST) data.

    Class objects for Main Tower and Small towers are already created in the package. Following classes are available:

    >>> MT2  = SonicTower(height=2 , tower='main' )
    >>> MT10 = SonicTower(height=10, tower='main' )
    >>> MT28 = SonicTower(height=28, tower='main' )
    >>> MT42 = SonicTower(height=42, tower='main' )
    >>> ST2  = SonicTower(height=2 , tower='small')
    >>> ST10 = SonicTower(height=10, tower='small')

    Parameters
    ----------

    height : float
        Instrument height.
        Height is 2, 10, 28, 42 for Main Tower, and 2, 10 or Small Tower
    tower : str
        Selected tower (main, small)

    Examples
    --------
    Extract data of the 2m sonic anemometer of the Small Tower and set a fail sensor

    >>> import pyrolib.firefluxpost as ffp
    >>> from datetime import datetime
    >>>
    >>> # set FireFlux I data path
    >>> ffp.set_data_path('/home/user/data/FireFlux_Raw')
    >>> # extract 2m small tower data from file
    >>> ffp.ST2.get_wind_and_temp()
    >>> # set fail sensor
    >>> ffp.ST2.set_fail_sensor(ffp.datetime2seconds(ffp.ST2.time, datetime(2006, 2, 23, 12, 46, 44)), 455)

    """

    def __init__(self, height, tower):
        self.height = height
        self.tower = tower
        self.U = None
        self.V = None
        self.W = None
        self.Ts = None
        self.time = None
        self.Tcfine = None
        if tower == "main":
            self.file = f"Pfit_MT{self.height:d}m_FEB23_H12-13_1s.dat"
        elif tower == "small":
            self.file = f"Pfit_ST{self.height:d}m_FEB23_H12-13_1s.dat".format()

    def get_wind_and_temp(self):
        """Import wind data and sonic temperature from data files."""
        with open(f"{FireFluxDataPath:s}/{self.file:s}", "r") as f:
            reader = csv.reader(f, delimiter=" ")
            NbofRow = sum(1 for row in reader)
            f.seek(0)
            self.time = []
            counter = np.zeros(NbofRow)
            self.U = np.zeros(NbofRow)
            self.V = np.zeros(NbofRow)
            self.W = np.zeros(NbofRow)
            self.Ts = np.zeros(NbofRow)
            if self.tower == "main":
                coltc = 11
            else:
                coltc = 12

            if self.height == 2:
                self.Tcfine = np.zeros(NbofRow)
                for i, row in enumerate(reader):
                    row = list(filter(None, row))
                    self.time.append(datetime(2006, 2, 23, int(row[3]), int(row[4]), int(row[5]) - 1))
                    counter[i] = float(row[6])
                    self.U[i] = float(row[8])
                    self.V[i] = -float(row[7])
                    self.W[i] = float(row[9])
                    self.Ts[i] = float(row[10])
                    self.Tcfine[i] = float(row[coltc])
            else:
                for i, row in enumerate(reader):
                    row = list(filter(None, row))
                    self.time.append(datetime(2006, 2, 23, int(row[3]), int(row[4]), int(row[5]) - 1))
                    counter[i] = float(row[6])
                    self.U[i] = float(row[8])
                    self.V[i] = -float(row[7])
                    self.W[i] = float(row[9])
                    self.Ts[i] = float(row[10])

    def set_fail_sensor(self, timevector, failtime, endoffailtime=None):
        """Set nan into TcFine temperature for failed sensor since failtime to endoffailtime (default infinity)

        Parameters
        ----------

        timevector : list of float
            time vector (seconds)
        """
        # get index for fail timeFireFlux_Raw.zip
        if endoffailtime is None:
            self.Tcfine[timevector >= failtime] = np.nan
        else:
            self.Tcfine[timevector >= failtime and timevector <= endoffailtime] = np.nan


class _TcData:
    """
    Default class for data storage
    """

    def __init__(self, height):
        self.height = height
        self.data = None


class MainTowerTc:
    """Type T thermocouples data extraction class

    Extraction of Main Tower (MT) type T thermocouples data.

    Class object for Main Tower is already created in the package. Following class is available:

    >>> MTtc = MainTowerTc()

    Examples
    --------

    Import type T thermocouples data and use Hodrick-Prescott filter

    >>> import pyrolib.firefluxpost as ffp
    >>> import statsmodels.api as sm
    >>>
    >>> # set FireFlux I data path
    >>> ffp.set_data_path('/home/user/data/FireFlux_Raw')
    >>> # extract main tower data from file
    >>> ffp.MTtc.getdata()
    >>> # use HP filter (1600 as filtering constant)
    >>> _, filteredsignal = sm.tsa.filters.hpfilter(ffdp.MTtc.Tc['02.00'].data, 1600)

    """

    def __init__(self):
        self.Tc = {"ref": _TcData(height=-1)}
        for h in _MTHeight:
            self.Tc.update({f"{h:05.2f}": _TcData(height=h)})
        self.time = []

    def getdata(self):
        """Get data in file _DataFileName

        The file contains type T Thermocouple data for each height for Main Tower
        """
        with open(f"{FireFluxDataPath:s}/{_DataFileName:s}", "r") as f:
            reader = csv.reader(f, delimiter=" ")
            next(f)
            # Count lines in file for memory allocation of data vectors
            NbofRow = sum(1 for row in reader)
            f.seek(0)
            next(f)
            # Allocate vector size
            for tcDataKey in self.Tc.keys():
                self.Tc[tcDataKey].data = np.zeros(NbofRow)
            #
            referenceDate = datetime(2006, 2, 23, 12, 30, 0)
            # Import data
            for i, row in enumerate(reader):
                row = list(filter(None, row))
                self.time.append(referenceDate + timedelta(seconds=int(row[0]) - 1))
                # get ref data
                self.Tc["ref"].data[i] = row[1]
                # for each height, get data at line i
                for j, h in enumerate(_MTHeight):
                    self.Tc[f"{h:05.2f}"].data[i] = row[j + 2]


# base class objects
MT2 = SonicTower(height=2, tower="main")
MT10 = SonicTower(height=10, tower="main")
MT28 = SonicTower(height=28, tower="main")
MT42 = SonicTower(height=42, tower="main")
ST2 = SonicTower(height=2, tower="small")
ST10 = SonicTower(height=10, tower="small")

MTtc = MainTowerTc()

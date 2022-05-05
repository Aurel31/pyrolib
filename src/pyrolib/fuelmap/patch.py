""" Patch classes
"""

from abc import ABC, abstractmethod

import numpy as np
from bresenham import bresenham


class DataPatch(ABC):
    """Asbtract class for data patch to build fuel map

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
    """Class of a rectangle patch of data for fuel map construction

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
        """Compute mask for rectangle patch

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
                if (
                    xfiremesh[i] + 0.5 * XFIREMESHSIZE[0] > self.xpos[0]
                    and xfiremesh[i] - 0.5 * XFIREMESHSIZE[0] < self.xpos[1]
                ):
                    # get y limit
                    if (
                        yfiremesh[j] + 0.5 * XFIREMESHSIZE[1] > self.ypos[0]
                        and yfiremesh[j] - 0.5 * XFIREMESHSIZE[1] < self.ypos[1]
                    ):
                        self.datamask[j, i] = 1


class LinePatch(DataPatch):
    """Class of a rectangle patch of data for fuel map construction

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
        """Compute mask for rectangle patch

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
                if (
                    xfiremesh[i] - 0.5 * XFIREMESHSIZE[0] <= self.xpos[0]
                    and xfiremesh[i] + 0.5 * XFIREMESHSIZE[0] > self.xpos[0]
                    and yfiremesh[j] - 0.5 * XFIREMESHSIZE[1] <= self.ypos[0]
                    and yfiremesh[j] + 0.5 * XFIREMESHSIZE[1] > self.ypos[0]
                ):
                    i0 = i
                    j0 = j

                # find (x1, y1)
                if (
                    xfiremesh[i] - 0.5 * XFIREMESHSIZE[0] <= self.xpos[1]
                    and xfiremesh[i] + 0.5 * XFIREMESHSIZE[0] > self.xpos[1]
                    and yfiremesh[j] - 0.5 * XFIREMESHSIZE[1] <= self.ypos[1]
                    and yfiremesh[j] + 0.5 * XFIREMESHSIZE[1] > self.ypos[1]
                ):
                    i1 = i
                    j1 = j

        # Use bresenham algorithm to get all points between (x0, y0) and (x1, y1)
        self.line = list(bresenham(i0, j0, i1, j1))
        # mask only these points
        for ind in self.line:
            self.datamask[ind[1], ind[0]] = 1

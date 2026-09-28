"""Patch classes"""

from abc import ABC, abstractmethod

import numpy as np


def bresenham(x0, y0, x1, y1):
    """Yield the integer coordinates on the line from (x0, y0) to (x1, y1).

    Input coordinates must be integers. Both the start and the end point are
    part of the result.

    Vendored from the `bresenham` package (https://github.com/encukou/bresenham),
    Copyright (c) 2016 Petr Viktorin, MIT License. Inlined here to drop a
    single-function runtime dependency that is no longer maintained.
    """
    dx = x1 - x0
    dy = y1 - y0

    xsign = 1 if dx > 0 else -1
    ysign = 1 if dy > 0 else -1

    dx = abs(dx)
    dy = abs(dy)

    if dx > dy:
        xx, xy, yx, yy = xsign, 0, 0, ysign
    else:
        dx, dy = dy, dx
        xx, xy, yx, yy = 0, ysign, xsign, 0

    D = 2 * dy - dx
    y = 0

    for x in range(dx + 1):
        yield x0 + x * xx + y * yx, y0 + x * xy + y * yy
        if D >= 0:
            y += 1
            D -= 2 * dx
        D += 2 * dy


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
    def getmask(self, xfiremesh, yfiremesh, XFIREMESHSIZE):
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

""" FuelMap utility tools
"""

from math import ceil, floor
import numpy as np

try:
    from numba import njit

    has_numba = True
except ImportError:
    has_numba = False
    print("WARNING: Failed to find numba, loop acceleration will be not activated")
    pass


def njit_wrapper(function):
    if has_numba:
        return njit()(function)
    else:
        return function


sind = lambda degrees: np.sin(np.deg2rad(degrees))
cosd = lambda degrees: np.cos(np.deg2rad(degrees))


@njit_wrapper
def fill_fuel_array_from_patch(fuelarray, patchmask, propertyvector, np, nx, ny):
    """Fill fuel array considering a mask

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
                if patchmask[j, i] == 1:
                    fuelarray[k, j, i] = propertyvector[k]
    return fuelarray


@njit_wrapper
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
    for m in range(1, ny * gammay + 1):
        for l in range(1, nx * gammax + 1):
            # compute i,j,k
            i = ceil(float(l) / float(gammax))
            j = ceil(float(m) / float(gammay))
            a = l - (i - 1) * gammax
            b = m - (j - 1) * gammay
            k = (b - 1) * gammax + a

            # fill tables
            farray3d[k - 1, j - 1, i - 1] = firearray2d[m - 1, l - 1]
    return farray3d


@njit_wrapper
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
    farray2d = np.zeros((ny * gammay, nx * gammax))
    for k in range(1, gammax * gammay + 1):
        b = floor((k - 1) / gammax) + 1
        a = k - (b - 1) * gammax
        for j in range(1, ny + 1):
            m = (j - 1) * gammay + b
            for i in range(1, nx + 1):
                l = (i - 1) * gammax + a
                farray2d[m - 1, l - 1] = firearray3d[k - 1, j - 1, i - 1]
    return farray2d


def convert_lon_lat_to_x_y(confproj: dict, lat, lon):
    """Convert points (lon, lat) into Méso-NH conformal coordinates (x, y)

    Port of ``SM_XYHAT_S`` (Méso-NH ``mode_gridproj.f90``) on a spherical earth of
    radius 6371229 m (``XRADIUS``, ``ini_cst.f90``). The five projections of Méso-NH
    are supported, selected by the projection constant ``RPK``:

    - polar-stereographic from the south pole (``RPK = 1``),
    - Lambert conformal from the south pole (``0 < RPK < 1``),
    - Mercator (``RPK = 0``),
    - Lambert conformal from the north pole (``-1 < RPK < 0``),
    - polar-stereographic from the north pole (``RPK = -1``),

    each with an anticlockwise rotation of ``BETA`` degrees of the conformal frame with
    respect to the geographical north. Longitudes are wrapped into
    ``[LON0 - 180, LON0 + 180]``.

    Parameters
    ----------
    confproj : dict
        conformal projection parameters read from the Méso-NH initialization file,
        with keys ``k`` (``RPK``), ``beta`` (``BETA``), ``lat0``, ``lon0`` (``LAT0``,
        ``LON0``, reference point of the projection) and ``lat_ori``, ``lon_ori``
        (``LATORI``, ``LONORI``, geographical position of the ``x = 0, y = 0`` point).
        All angles in degrees.
    lat : array_like
        latitudes of the points (deg)
    lon : array_like
        longitudes of the points (deg)

    Returns
    -------
    x, y : numpy.ndarray
        conformal coordinates (m), same shape as ``lat`` and ``lon``

    Raises
    ------
    ValueError
        if ``confproj["k"]`` is outside ``[-1, 1]``
    """
    earth_radius = 6371229.0  # XRADIUS, ini_cst.f90
    rpk = float(confproj["k"])
    beta = float(confproj["beta"])
    lat0 = float(confproj["lat0"])
    lon0 = float(confproj["lon0"])
    lat_ori = float(confproj["lat_ori"])
    lon_ori = float(confproj["lon_ori"])
    if not -1.0 <= rpk <= 1.0:
        raise ValueError(f"Projection constant RPK = {rpk} is outside [-1, 1] (see SM_XYHAT_S)")

    lat = np.asarray(lat, dtype=np.float64)
    lon = np.asarray(lon, dtype=np.float64)

    # longitudes set between lon0 - 180 and lon0 + 180
    lon = lon + np.rint((lon0 - lon) / 360.0) * 360.0
    lon_ori_wrapped = lon_ori + np.rint((lon0 - lon_ori) / 360.0) * 360.0

    if rpk != 0.0:
        # Polar-stereographic and Lambert conformal projections
        from_north_pole = rpk < 0.0
        if from_north_pole:
            # projection from the north pole: mirror the earth through the equator
            # and use the south pole formulation, y is mirrored back at the end
            rpk, beta, lat0, lon0 = -rpk, -beta, -lat0, lon0 + 180.0
            lat_ori, lon_ori_wrapped = -lat_ori, lon_ori_wrapped + 180.0
            lat, lon = -lat, lon + 180.0

        clat0, slat0 = cosd(lat0), sind(lat0)
        clat_ori, slat_ori = cosd(lat_ori), sind(lat_ori)

        # position of the pole (x_p, y_p) from the origin (x = 0, y = 0)
        rho0 = (
            (earth_radius / rpk)
            * abs(clat0) ** (1.0 - rpk)
            * ((1.0 + slat0) * abs(clat_ori) / (1.0 + slat_ori)) ** rpk
        )
        gamma0 = np.deg2rad(rpk * (lon_ori_wrapped - lon0) - beta)
        x_pole = -rho0 * np.sin(gamma0)
        y_pole = rho0 * np.cos(gamma0)

        # polar coordinates (rho, gamma) of the points around the pole
        clat, slat = cosd(lat), sind(lat)
        rho = (
            (earth_radius / rpk)
            * abs(clat0) ** (1.0 - rpk)
            * ((1.0 + slat0) * np.abs(clat) / (1.0 + slat)) ** rpk
        )
        gamma = np.deg2rad(rpk * (lon - lon0) - beta)
        x = x_pole + rho * np.sin(gamma)
        y = y_pole - rho * np.cos(gamma)

        if from_north_pole:
            y = -y
    else:
        # Mercator projection with rotation. The isometric latitude is
        # XRADIUS * COS(XLAT0) * LOG(TAN(pi/4 + lat/2)), with LOG the natural logarithm.
        # As in SM_XYHAT_S, the origin longitude is not wrapped in this branch.
        cgam, sgam = cosd(-beta), sind(-beta)
        raclat0 = earth_radius * cosd(lat0)
        x_e = -raclat0 * np.deg2rad(lon_ori - lon0)
        y_e = -raclat0 * np.log(np.tan(0.25 * np.pi + 0.5 * np.deg2rad(lat_ori)))

        # coordinates in the unrotated frame, then rotation of -beta
        xpr = raclat0 * np.deg2rad(lon - lon0) + x_e
        ypr = raclat0 * np.log(np.tan(0.25 * np.pi + 0.5 * np.deg2rad(lat))) + y_e
        x = xpr * cgam - ypr * sgam
        y = xpr * sgam + ypr * cgam

    return x, y

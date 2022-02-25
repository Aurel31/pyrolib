# -*- coding: utf-8 -*-
"""Blaze computing methods
"""

import numpy as np

def SGBA_WA(phi, nx, ny):
    r"""Compute Sub-Grid Burning Area (SGBA) with Weighted Average (WA) method.

    The SGBA :math:`\mathcal S` is computed by the following expression:

    .. math::
        \mathcal S_{i, j} =& \frac{9}{16} \phi_{i, j} + 
        \frac{3}{32} \left ( \phi_{i-1, j} + \phi_{i, j-1} + \phi_{i+1, j} + \phi_{i, j+1} \right ) + \\
        & \frac{1}{64} \left ( \phi_{i-1, j-1} + \phi_{i+1, j-1} + \phi_{i+1, j+1} + \phi_{i-1, j+1} \right ).

    Parameters
    ----------
    phi : np.ndarray
        Level-set array (ny, nx)
    nx : int
        Size of fire array in x direction
    ny : int
        Size of fire array in x direction

    Returns
    -------
    S : np.ndarray
        Sub-Grid Burning Area computed with Weighted Average method
    """
    S = np.empty((ny, nx))
    for j in range(1, ny-1):
        for i in range(1, nx-1):
            S[j, i] = 9./16. * phi[j, i] \
                    + 3./32. * (phi[j, i-1] + phi[j-1, i] + phi[j, i+1] + phi[j+1, i]) \
                    + 1./64. * (phi[j-1, i-1] + phi[j-1, i+1] + phi[j+1, i-1] + phi[j+1, i+1])

    return S

def SGBA_EFFR(phi, nx, ny):
    """Compute Sub-Grid Burning Area (SGBA) with Explicit Fire Front Reconstruction (EFFR) method[2]_.

    Parameters
    ----------
    phi : np.ndarray
        Level-set array (ny, nx)
    nx : int
        Size of fire array in x direction
    ny : int
        Size of fire array in x direction

    Returns
    -------
    S : np.ndarray
        Sub-Grid Burning Area computed with Weighted Average method
    """
    S = np.empty((ny, nx))
    phi_south_west = np.empty((ny, nx))
    phi_south  = np.empty((ny, nx))
    phi_south_east = np.empty((ny, nx))
    phi_east  = np.empty((ny, nx))
    phi_north_east = np.empty((ny, nx))
    phi_north  = np.empty((ny, nx))
    phi_north_west = np.empty((ny, nx))
    phi_west  = np.empty((ny, nx))
    
    for j in range(1,ny-1):
        for i in range(1,nx-1):
            phi_south_west[j, i] = .25 * (phi[j-1, i-1] + phi[j-1, i] + phi[j, i] + phi[j, i-1])
            phi_south[j, i] = .5  * (phi[j-1, i] + phi[j, i])
            phi_south_east[j, i] = .25 * (phi[j-1, i] + phi[j-1, i+1] + phi[j, i+1] + phi[j, i])
            phi_east[j, i]  = .5  * (phi[j, i+1] + phi[j, i])
            phi_north_east[j, i] = .25 * (phi[j, i] + phi[j, i+1] + phi[j+1, i+1] + phi[j+1, i])
            phi_north[j, i] = .5  * (phi[j+1, i] + phi[j, i])
            phi_north_west[j, i] = .25 * (phi[j, i-1] + phi[j, i] + phi[j+1, i] + phi[j+1, i-1])
            phi_west[j, i]  = .5  * (phi[j, i-1] + phi[j, i])

    S = 0.25 * (_compute_quadrant_area(phi_south_west,
                               phi_south,
                               phi, phi_west,
                               nx,
                               ny)
        + _compute_quadrant_area(phi_south,
                                 phi_south_east,
                                 phi_east,
                                 phi,
                                 nx,
                                 ny)
        + _compute_quadrant_area(phi,
                                 phi_east,
                                 phi_north_east,
                                 phi_north,
                                 nx,
                                 ny)
        + _compute_quadrant_area(phi_west,
                                 phi,
                                 phi_north,
                                 phi_north_west,
                                 nx,
                                 ny)
    )
    return S

def _compute_quadrant_area(phi1, phi2, phi3, phi4, nx, ny):
    """Compute surface with EFFR method

    Parameters
    ----------
    phi1 : float
        Level-set at south west point
    phi2 : float
        Level-set at south east point
    phi3 : float
        Level-set at north east point
    phi4 : float
        Level-set at north west point
    nx : int
        Size of fire array in x direction
    ny : int
        Size of fire array in x direction

    Returns
    -------
    float
        SGBA
    """
    quadrant_area = np.empty((ny, nx))
    for j in range(1, ny-1):
        for i in range(1, nx-1):
            # phi value
            P1 = phi1[j, i]
            P2 = phi2[j, i]
            P3 = phi3[j, i]
            P4 = phi4[j, i]
            # intersection
            if (P1>.5 and P2>.5 and P3>.5 and P4>.5):
                # fire in the whole cell
                quadrant_area[j, i] = 1.
                continue
            #
            if (P1<.5 and P2<.5 and P3<.5 and P4<.5):
                # no fire in the cell
                quadrant_area[j, i] = 0.
                continue
            #
            # crossing values_surf28(P1, P4, P3, P2)
            D1 = int(.5*np.sign(P1-.5) - .5*np.sign(P2-0.5))
            D2 = int(.5*np.sign(P2-.5) - .5*np.sign(P3-0.5))
            D3 = int(.5*np.sign(P4-.5) - .5*np.sign(P3-0.5))
            D4 = int(.5*np.sign(P1-.5) - .5*np.sign(P4-0.5))
            # Case identifier
            C = (1+D1) + 3*(1+D2) + 9*(1+D3) + 27*(1+D4)
            # Case call
            if C==68:
                quadrant_area[j,i] = _surf68(P1, P2, P4)
            elif C==12:
                quadrant_area[j,i] = 1. - _surf68(P1, P2, P4)
            elif C==70:
                quadrant_area[j,i] = _surf70(P1, P2, P3, P4)
            elif C==10:
                quadrant_area[j,i] = 1. - _surf70(P1, P2, P3, P4)
            elif C==22:
                quadrant_area[j,i] = _surf22(P1, P3, P4)
            elif C==42:
                quadrant_area[j,i] = _surf22(P1, P3, P2)
            elif C==38:
                quadrant_area[j,i] = 1. - _surf22(P1, P3, P2)
            elif C==50:
                quadrant_area[j,i] = _surf70(P1, P4, P3, P2)
            elif C==30:
                quadrant_area[j,i] = 1. - _surf70(P1, P4, P3, P2)
            elif C==28:
                quadrant_area[j,i] = _surf68(P3, P2, P4)
            elif C==52:
                quadrant_area[j,i] = 1. - _surf68(P3, P2, P4)
            elif C==24:
                quadrant_area[j,i] = _surf22(P1, P3, P4) + _surf22(P1, P3, P2)
            elif C==56:
                quadrant_area[j,i] = _surf68(P1, P2, P4) + _surf68(P3, P2, P4)
            else:
                print(f'default at ({i}, {j})')
                quadrant_area[j,i] = 0.

    return quadrant_area

def _surf68(phi1, phi2, phi4):
    """Compute area of a south east fire triangle

    Parameters
    ----------
    phi1 : float
        Level-set at south west point
    phi2 : float
        Level-set at south east point
    phi4 : float
        Level-set at north west point

    Returns
    -------
    float
        SGBA
    """
    return np.power(.5-phi1, 2) / (2. * (phi2-phi1) * (phi4-phi1))

def _surf70(phi1, phi2, phi3, phi4):
    """Compute area of a south fire trapeze

    Parameters
    ----------
    phi1 : float
        Level-set at south west point
    phi2 : float
        Level-set at south east point
    phi3 : float
        Level-set at north east point
    phi4 : float
        Level-set at north west point

    Returns
    -------
    float
        SGBA
    """
    return .5 *((.5-phi1) / (phi4-phi1) + (.5-phi2) / (phi3-phi2))

def _surf22(phi1, phi3, phi4):
    """Compute area of a north east fire triangle

    Parameters
    ----------
    phi1 : float
        Level-set at south west point
    phi2 : float
        Level-set at south east point
    phi3 : float
        Level-set at north east point

    Returns
    -------
    float
        SGBA
    """
    return np.power(phi4-.5, 2) / (-2 * (phi4-phi1) * (phi3-phi4))

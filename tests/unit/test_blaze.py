""" unit tests blaze.py functions
"""

import numpy as np
from pyrolib.blaze.subgrid_burning_area import _surf68, _surf22, _surf70
import pytest

def test_surf68():
    assert np.isclose(_surf68(1, 0.5, 0.5), .5)


def test_surf22():
    assert np.isclose(_surf22(0.5, 0.5, 1), .5)


def test_surf70():
    assert np.isclose(_surf70(1., 1., 0., 0.), .5)

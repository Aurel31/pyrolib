""" unit tests blaze.py functions
"""

import numpy as np
import pyrolib.blaze as blz
import pytest

def test_surf68():
    assert np.isclose(blz._surf68(1, 0.5, 0.5), .5)

def test_surf22():
    assert np.isclose(blz._surf22(0.5, 0.5, 1), .5)

def test_surf70():
    assert np.isclose(blz._surf70(1., 1., 0., 0.), .5)
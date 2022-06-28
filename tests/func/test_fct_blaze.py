""" Test blaze.py functions
"""

import numpy as np
import pyrolib.blaze as blz
import pytest


@pytest.fixture(scope="function")
def level_set_case(request):
    if request.param == "no fire":
        # No fire test case
        return np.zeros((3, 3), dtype=np.float64)
    if request.param == "full fire":
        # Full fire test case
        return np.ones((3, 3), dtype=np.float64)
    elif request.param == "triangles":
        # All triangles test case
        return np.array([[0, 0.2, 0], [0.2, 0.6, 0.2], [0, 0.2, 0]], dtype=np.float64)
    elif request.param == "horizontal":
        # Horizontal fire lines
        return np.array([[0.2, 0.6, 0.2], [0.2, 0.6, 0.2], [0.2, 0.6, 0.2]], dtype=np.float64)
    elif request.param == "vertical":
        # Vertical fire lines
        return np.array([[0.2, 0.2, 0.2], [0.6, 0.6, 0.6], [0.2, 0.2, 0.2]], dtype=np.float64)


@pytest.mark.parametrize(
    "level_set_case, value",
    [("no fire", 0.0), ("full fire", 1.0), ("triangles", 0.125), ("horizontal", 0.5), ("vertical", 0.5)],
    indirect=["level_set_case"],
)
def test_SGBA_EFFR(level_set_case, value):
    assert np.isclose(blz.SGBA_EFFR(level_set_case, 3, 3)[1, 1], value, rtol=1e-12, atol=1e-15)


@pytest.mark.parametrize(
    "level_set_case, value",
    [("no fire", 0.0), ("full fire", 1.0), ("triangles", 0.4125), ("horizontal", 0.5), ("vertical", 0.5)],
    indirect=["level_set_case"],
)
def test_SGBA_WA(level_set_case, value):
    # print(blz.SGBA_WA(level_set_case, 3, 3)[1, 1])
    assert np.isclose(blz.SGBA_WA(level_set_case, 3, 3)[1, 1], value, rtol=1e-12, atol=1e-15)

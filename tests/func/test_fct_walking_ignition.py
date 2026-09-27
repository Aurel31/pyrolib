""" functional tests: walking ignition line patches
"""

import os

import numpy as np
import pytest

import pyrolib.fuelmap as pl

WORKDIR = "examples/fuel_map"
FUEL_KEY = "FireFluxI_tall_grass"


@pytest.fixture
def fuelmap():
    my_db = pl.FuelDatabase()
    my_db.load_fuel_database("FireFluxI")
    return pl.FuelMap(fuel_db=my_db, workdir=f"{os.getcwd()}/{WORKDIR}")


def expected_segment_times(fuelmap, a, b, t_a, t_b):
    """Ignition time of the point of segment ab closest to each line cell center, and distance to it"""
    walking = fuelmap.walkingignitionmaparray
    rows, cols = np.nonzero(walking != -1)
    a, ab = np.array(a), np.array(b) - np.array(a)
    centers = np.column_stack((fuelmap.xfiremesh[cols], fuelmap.yfiremesh[rows]))
    fraction = np.clip((centers - a) @ ab / (ab @ ab), 0.0, 1.0)
    distance = np.linalg.norm(centers - (a + fraction[:, None] * ab), axis=1)
    return (rows, cols), t_a + fraction * (t_b - t_a), distance


def test_walking_ignition_vertical_line(fuelmap):
    # line on the cell edge x = 200: every center is 2.5 m beside the segment,
    # the center of the cell holding B (y = 352.5) is also 2.5 m past B
    fuelmap.add_walking_ignition_line_patch(
        [200.0, 200.0], [300.0, 350.0], walking_ignition_times=[0.0, 100.0]
    )

    walking = fuelmap.walkingignitionmaparray
    rows, cols = np.nonzero(walking != -1)
    assert np.all(fuelmap.xfiremesh[cols] == 202.5)
    np.testing.assert_allclose(fuelmap.yfiremesh[rows], np.arange(302.5, 353.0, 5.0))
    np.testing.assert_allclose(walking[rows, cols], [*np.arange(5.0, 96.0, 10.0), 100.0])
    np.testing.assert_allclose(
        fuelmap.walkingignitiondistancearray[rows, cols], [2.5] * 10 + [np.hypot(2.5, 2.5)]
    )


@pytest.mark.parametrize(
    "a, b, t_a, t_b",
    [
        ((100.0, 100.0), (300.0, 200.0), 10.0, 60.0),
        # B south-west of A: times still grow from A to B
        ((400.0, 400.0), (150.0, 300.0), 0.0, 30.0),
    ],
)
def test_walking_ignition_oblique_line(fuelmap, a, b, t_a, t_b):
    fuelmap.add_walking_ignition_line_patch([a[0], b[0]], [a[1], b[1]], walking_ignition_times=[t_a, t_b])

    (rows, cols), times, distance = expected_segment_times(fuelmap, a, b, t_a, t_b)
    assert rows.size > 1
    np.testing.assert_allclose(fuelmap.walkingignitionmaparray[rows, cols], times)
    np.testing.assert_allclose(fuelmap.walkingignitiondistancearray[rows, cols], distance)
    # the segment is ignited within [t_a, t_b], and every center is at most half a cell diagonal away
    assert times.min() >= t_a
    assert times.max() <= t_b
    assert distance.max() <= 0.5 * np.hypot(*fuelmap.xfiremeshsize)
    # sorted by ignition time, cells go from A towards B
    order = np.argsort(times)
    xs, ys = fuelmap.xfiremesh[cols][order], fuelmap.yfiremesh[rows][order]
    assert np.sign(xs[-1] - xs[0]) == np.sign(b[0] - a[0])
    assert np.sign(ys[-1] - ys[0]) == np.sign(b[1] - a[1])


def test_walking_ignition_arrival_times_add_spread_to_center(fuelmap):
    a, b, t_a, t_b = (100.0, 100.0), (300.0, 200.0), 10.0, 60.0
    fuelmap.add_walking_ignition_line_patch([a[0], b[0]], [a[1], b[1]], walking_ignition_times=[t_a, t_b])
    # fuel set after the line, and an unburnable cut across it
    fuelmap.add_fuel_rectangle_patch([50.0, 450.0], [50.0, 450.0], fuel_key=FUEL_KEY)
    fuelmap.add_unburnable_rectangle_patch([190.0, 210.0], [50.0, 450.0])

    (rows, cols), times, distance = expected_segment_times(fuelmap, a, b, t_a, t_b)
    ros = fuelmap.fuel_db[FUEL_KEY]["BalbiFuel"].getR()
    unburnable = np.abs(fuelmap.xfiremesh[cols] - 200.0) < 10.0
    assert unburnable.any() and not unburnable.all()
    expected = np.where(unburnable, times, times + distance / ros)

    arrival = fuelmap.get_walking_ignition_arrival_times()
    np.testing.assert_allclose(arrival[rows, cols], expected)
    # -1 outside the line, and the stored segment times are left untouched
    assert np.count_nonzero(arrival != -1) == rows.size
    np.testing.assert_allclose(fuelmap.walkingignitionmaparray[rows, cols], times)


def test_walking_ignition_arrival_times_without_fuel(fuelmap):
    fuelmap.add_walking_ignition_line_patch(
        [200.0, 200.0], [300.0, 350.0], walking_ignition_times=[0.0, 100.0]
    )
    np.testing.assert_array_equal(
        fuelmap.get_walking_ignition_arrival_times(), fuelmap.walkingignitionmaparray
    )

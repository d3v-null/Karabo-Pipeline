"""Exercise EveryBeam's MWA Python API through DP3 Predict's beam primitive."""

import os

import numpy as np

import everybeam


MS_PATH = os.environ.get("EVERYBEAM_MWA_MS", "/tmp/MWA_MOCK.ms")
COEFF_PATH = os.environ["MWA_BEAM_FILE"]

# Values from EveryBeam's v0.8.2 C++ MWA regression fixture.  DP3 Predict
# converts a J2000 source position to ITRF and calls PointResponse::Response
# with one such vector for each station/frequency pair.  This normalized ITRF
# vector directly exercises that same call path through the Python binding.
TIME_MJD_SECONDS = 4.87541808e9
FREQUENCY_HZ = 133794999.99999999
SOURCE_DIRECTION_ITRF = np.array([0.8, -0.2, np.sqrt(0.32)], dtype=np.float64)


def main() -> None:
    telescope = everybeam.load_telescope(MS_PATH, coeff_path=COEFF_PATH)

    assert isinstance(telescope, everybeam.MWA)
    assert telescope.nr_stations == 128
    assert telescope.is_homogeneous
    assert np.isclose(np.linalg.norm(SOURCE_DIRECTION_ITRF), 1.0)

    # DP3 Predict's access pattern:
    #   telescope->GetPointResponse(time)->Response(kFull, station, freq, itrf)
    # The MWA Python binding exposes the identical full-Jones evaluation.
    jones = np.stack(
        [
            telescope.station_response(
                TIME_MJD_SECONDS,
                station_index,
                FREQUENCY_HZ,
                SOURCE_DIRECTION_ITRF,
            )
            for station_index in (0, 1, 127)
        ]
    )

    assert jones.shape == (3, 2, 2)
    assert np.issubdtype(jones.dtype, np.complexfloating)
    assert np.isfinite(jones).all()
    assert not np.allclose(jones[0], 0.0)
    # MWA tiles are homogeneous; therefore equal inputs give equal Jones terms.
    np.testing.assert_allclose(
        jones[1:],
        np.broadcast_to(jones[0], jones[1:].shape),
        rtol=1e-6,
        atol=1e-7,
    )

    print(
        "EveryBeam MWA DP3-Predict primitive OK:",
        f"type={type(telescope).__name__}",
        f"stations={telescope.nr_stations}",
        f"max_abs={np.abs(jones).max():.8g}",
    )
    check_time_dependent_pointing()


def check_time_dependent_pointing() -> None:
    """A MeasurementSet whose MWA_TILE_POINTING has two rows (two pointings,
    each with its own INTERVAL) must get each pointing's beam in its interval
    (the overlay's mwa-time-dependent-pointing patch; stock EveryBeam reads
    row 0 only)."""
    import shutil
    import tempfile

    from casacore.tables import table

    tilted = np.array([3, 2, 1, 0] * 4, dtype=np.int32)  # an east-west tilt
    tmp = tempfile.mkdtemp(prefix="mwa_pointing_")
    try:

        def copy_with_pointings(name, rows):
            path = os.path.join(tmp, name)
            shutil.copytree(MS_PATH, path)
            pointing = table(path + "/MWA_TILE_POINTING", readonly=False, ack=False)
            pointing.addrows(len(rows) - pointing.nrows())
            for row, (interval, delays) in enumerate(rows):
                pointing.putcell("INTERVAL", row, np.asarray(interval, dtype=float))
                pointing.putcell("DELAYS", row, delays)
            pointing.close()
            return path

        pointing = table(MS_PATH + "/MWA_TILE_POINTING", ack=False)
        start, end = pointing.getcell("INTERVAL", 0)
        zenith = pointing.getcell("DELAYS", 0)
        pointing.close()
        middle = 0.5 * (start + end)
        two = copy_with_pointings(
            "two.ms", [((middle, end), tilted), ((start, middle), zenith)]
        )
        only_tilted = copy_with_pointings("tilted.ms", [((start, end), tilted)])

        def response(path, time):
            telescope = everybeam.load_telescope(path, coeff_path=COEFF_PATH)
            return telescope.station_response(time, 0, FREQUENCY_HZ, SOURCE_DIRECTION_ITRF)

        early, late = start + 10.0, end - 10.0
        assert not np.allclose(response(MS_PATH, late), response(only_tilted, late))
        np.testing.assert_array_equal(response(two, early), response(MS_PATH, early))
        np.testing.assert_array_equal(response(two, late), response(only_tilted, late))
        print("EveryBeam MWA time-dependent pointing OK: two MWA_TILE_POINTING rows")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()

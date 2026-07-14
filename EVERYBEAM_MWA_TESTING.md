# EveryBeam 0.8.2 MWA / DP3 6.6 verification

This image installs EveryBeam `v0.8.2` (`09e43d7f44e44e5b9a16822fa4387fc790e477d9`)
and DP3 `v6.6` (`4a8f165a0f5683771cc3c84d041ffe98c14d5ceb`). The existing
Boost 1.88 pin meets EveryBeam's new Boost >=1.73 requirement.

## What is tested

EveryBeam 0.8.2 contains the MWA implementation but upstream's Python wrapper
rejects MWA measurement sets and does not bind an `MWA` class. The overlay
patch `spack-overlay/packages/everybeam/enable-mwa-python-bindings.patch`
exposes it, including:

```python
telescope = everybeam.load_telescope(ms_path, coeff_path=coeff_path)
jones = telescope.station_response(time_mjd_seconds, station_index,
                                   frequency_hz, source_direction_itrf)
```

This is deliberately not the convenience `PhasedArray.station_response` API.
It is the same primitive used in DP3 6.6 Predict:

```cpp
telescope->GetPointResponse(time)->Response(
    everybeam::BeamMode::kFull, station, frequency, source_direction_itrf)
```

`everybeam_mwa_predict_test.py` uses EveryBeam's upstream
`MWA-single-timeslot.tar.bz2` fixture and the upstream MWA embedded-element
coefficient file. It verifies that:

1. the MS loads as `everybeam.MWA`;
2. the fixture has 128 stations and reports a homogeneous MWA;
3. full-Jones responses for stations 0, 1, and 127 have shape `(2, 2)`,
   complex dtype, finite non-zero values, and agree across homogeneous tiles;
4. DP3 starts and its Python module imports.

The fixture MS is downloaded only while building the final image and removed
after the probe; it is not included in the image.

## Reproduce the image build

BuildKit's persistent local Spack buildcache is enabled explicitly. It can
reuse packages from prior builds and autopush newly built packages into the
same cache. Spack's versioned `v1.1.0` public buildcache remains configured
for binary downloads.

```bash
set -o pipefail
DOCKER_BUILDKIT=1 docker build \
  --progress=plain \
  --build-arg SPACK_BUILDCACHE_LOCAL=1 \
  -f sp5505.Dockerfile \
  -t d3vnull0/sp5505:everybeam-0.8.2-dp3-6.6 . 2>&1 | tee sp5505-everybeam-0.8.2.log
```

The build runs `everybeam_mwa_predict_test.py`, `DP3 --version`, and
`import dp3` after all runtime files have been copied. A successful probe ends
with `EveryBeam MWA DP3-Predict primitive OK`.

## Generate the Hyperbeam / PyUVBeam / EveryBeam comparison

`karabo/examples/compare_mwa_beams.py` plots the full-Jones magnitude and
phase of Hyperbeam, PyUVBeam, and EveryBeam in three columns. EveryBeam is
evaluated through the same full-Jones, station-0, ITRF-direction primitive used
by DP3 Predict. It obtains the MWA array position and observation time from
the fixture MS, then converts the requested AltAz grid to ITRF directions.

This command was run successfully with the 0.8.2 image. It writes
`karabo/examples/compare_mwa_181_everybeam.png` on the host. The coarse grid
keeps the per-direction Python binding probe quick; reduce the steps for a
higher-resolution plot.

```bash
repo="$(git rev-parse --show-toplevel)"
docker run --rm \
  -e MPLBACKEND=Agg \
  -e MWA_BEAM_FILE=/opt/mwa_full_embedded_element_pattern.h5 \
  -v "$repo/karabo/examples:/work" \
  d3vnull0/sp5505:everybeam-0.8.2-dp3-6.6 bash -lc '
    set -e
    workdir=$(mktemp -d)
    trap "rm -rf \"$workdir\"" EXIT
    wget -q -P "$workdir" \
      https://support.astron.nl/software/ci_data/EveryBeam/MWA-single-timeslot.tar.bz2
    mkdir "$workdir/MWA_MOCK.ms"
    tar -xf "$workdir/MWA-single-timeslot.tar.bz2" \
      -C "$workdir/MWA_MOCK.ms" --strip-components=1
    EVERYBEAM_MWA_MS="$workdir/MWA_MOCK.ms" \
      python /work/compare_mwa_beams.py "$MWA_BEAM_FILE" \
        --freq-mhz 181 --za-step 15 --az-step 15 \
        --out /work/compare_mwa_181_everybeam.png
  '
```

## Repeat the MWA Python probe in a built image

```bash
repo="$(git rev-parse --show-toplevel)"
docker run --rm \
  -e MWA_BEAM_FILE=/opt/mwa_full_embedded_element_pattern.h5 \
  -v "$repo/everybeam_mwa_predict_test.py:/tmp/everybeam_mwa_predict_test.py:ro" \
  d3vnull0/sp5505:everybeam-0.8.2-dp3-6.6 bash -lc '
    set -e
    workdir=$(mktemp -d)
    trap "rm -rf \"$workdir\"" EXIT
    wget -q -P "$workdir" \
      https://support.astron.nl/software/ci_data/EveryBeam/MWA-single-timeslot.tar.bz2
    mkdir "$workdir/MWA_MOCK.ms"
    tar -xf "$workdir/MWA-single-timeslot.tar.bz2" \
      -C "$workdir/MWA_MOCK.ms" --strip-components=1
    EVERYBEAM_MWA_MS="$workdir/MWA_MOCK.ms" python /tmp/everybeam_mwa_predict_test.py
    DP3 --version
    python -c "import dp3; print(\"dp3 Python import OK\")"
  '
```

## Inspect the concretized dependency versions

```bash
docker run --rm d3vnull0/sp5505:everybeam-0.8.2-dp3-6.6 bash -lc '
  spack find --format "{name}@{version} {hash:7}" everybeam dp3 boost
  python -c "import everybeam, dp3; print(everybeam.__file__); print(dp3.__file__)"
'
```

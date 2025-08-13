# This script generates simulated visibilities and images resembling SKAO data.
# It also outputs corresponding ObsCore metadata ready to be ingested to Rucio.
#
# Images: dirty image and cleaned image using WSClean.
# These are MFS images (frequency channels aggregated into one channel),
# not full image cubes.
#
# 2025-08-13 12:19:41.092249 Starting simulation
# 2025-08-13 13:18:59.351083 Creating dirty image
# 2025-08-13 13:21:44.302177 Script finished
# just under an hour to simulate a single timestep,
# imaging took 3 minutes
import math
import os
from datetime import datetime, timedelta, timezone

from karabo.data.obscore import ObsCoreMeta
from karabo.data.src import RucioMeta
from karabo.imaging.image import Image
from karabo.imaging.imager_base import DirtyImagerConfig
from karabo.imaging.imager_wsclean import (
    WscleanDirtyImager,
    WscleanImageCleaner,
    WscleanImageCleanerConfig,
)
from karabo.simulation.interferometer import InterferometerSimulation
from karabo.simulation.observation import Observation
from karabo.simulation.sky_model import SkyModel
from karabo.simulation.telescope import Telescope
from karabo.simulation.telescope_versions import SKALowAAStarVersions, SKAMidAAStarVersions
from karabo.simulation.visibility import Visibility
from karabo.simulator_backend import SimulatorBackend
from karabo.util.helpers import get_rnd_str

# Simulation
# Phase center: should be mean of coverage
# Means of values from sky model description
PHASE_CENTER_RA = 0.0
PHASE_CENTER_DEC = -27.0

# Imaging
# Image size in degrees should be smaller than FOV
# Bigger baseline -> higher resolution
# Image resolution from SKAO's generate_visibilities.ipynb
IMAGING_NPIXEL = 20000
# -> Cellsize < FOV / 20000 -> 9.32190458333e-7
IMAGING_CELLSIZE = 9.3e-7

# Metadata
OBS_COLLECTION = "SKAO/SKALOW"

obs_sim_id = 0  # inc/change for new simulation
user_rnd_str = get_rnd_str(k=7, seed=os.environ.get("USER"))
OBS_ID = "null"
RUCIO_NAME_PREFIX = "skalow_eor_"

# Output root dir, this is just a default, set to your liking
OUTPUT_ROOT_DIR = os.path.join("/cygnus", f"{RUCIO_NAME_PREFIX}output")
os.makedirs(OUTPUT_ROOT_DIR, exist_ok=True)
print(f"Output will be written under output root dir {OUTPUT_ROOT_DIR}")


def generate_visibilities() -> Visibility:
    simulator_backend = SimulatorBackend.OSKAR

    # Link to metadata of survey:
    # https://archive.sarao.ac.za/search/MIGHTEE%20COSMOS/target/J0408-6545/captureblockid/1587911796/
    sky_model = SkyModel.get_GLEAM_Sky()

    telescope = Telescope.constructor(  # type: ignore[call-overload]
        name="SKA-LOW-AAstar",
        version=SKALowAAStarVersions.SKA_OST_ARRAY_CONFIG_2_3_1,
        backend=simulator_backend,
    )

    # 1 timestep, 375 channels starting from 170 MHz to 200 MHz, 80kHz wide
    # Wavelength 185MHz = 1.62 m
    number_of_time_steps = 1
    start_frequency_hz = 170e6
    end_frequency_hz = 200e6
    frequency_increment_hz = 80e3
    number_of_channels = math.floor(
        (end_frequency_hz - start_frequency_hz) / frequency_increment_hz
    )
    print(f"{datetime.now()} number_of_channels={number_of_channels}")

    simulation = InterferometerSimulation(
        channel_bandwidth_hz=frequency_increment_hz,
        station_type="Aperture array",
        use_gpus=True,
    )

    observation = Observation(
        phase_centre_ra_deg=PHASE_CENTER_RA,
        phase_centre_dec_deg=PHASE_CENTER_DEC,
        start_date_and_time=datetime(2021, 9, 21, 14, 12, 35, 0, timezone.utc),
        length=timedelta(seconds=number_of_time_steps * 7.997),
        number_of_time_steps=number_of_time_steps,
        number_of_channels=number_of_channels,
        start_frequency_hz=start_frequency_hz,
        frequency_increment_hz=frequency_increment_hz,
    )

    return simulation.run_simulation(  # type: ignore[no-any-return]
        telescope,
        sky_model,
        observation,
        backend=simulator_backend,
        visibility_path=os.path.join(
            OUTPUT_ROOT_DIR,
            f"{RUCIO_NAME_PREFIX}.MS",
        ),
    )  # type: ignore[call-overload]


def create_visibilities_metadata(visibility: Visibility) -> None:
    ocm = ObsCoreMeta.from_visibility(
        vis=visibility,
        calibrated=False,
    )
    print(ocm)


def create_dirty_image(visibility: Visibility) -> Image:
    dirty_imager = WscleanDirtyImager(
        DirtyImagerConfig(
            imaging_npixel=IMAGING_NPIXEL,
            imaging_cellsize=IMAGING_CELLSIZE,
            combine_across_frequencies=True,
        )
    )

    return dirty_imager.create_dirty_image(
        visibility,
        output_fits_path=os.path.join(
            OUTPUT_ROOT_DIR,
            f"{RUCIO_NAME_PREFIX}dirty.fits",
        ),
    )


def create_cleaned_image(visibility: Visibility, dirty_image: Image) -> Image:
    image_cleaner = WscleanImageCleaner(
        WscleanImageCleanerConfig(
            imaging_npixel=IMAGING_NPIXEL,
            imaging_cellsize=IMAGING_CELLSIZE,
        )
    )

    return image_cleaner.create_cleaned_image(
        visibility,
        dirty_fits_path=dirty_image.path,
        output_fits_path=os.path.join(
            OUTPUT_ROOT_DIR,
            f"{RUCIO_NAME_PREFIX}cleaned.fits",
        ),
    )


def create_image_metadata(image: Image) -> None:
    # Create image metadata
    ocm = ObsCoreMeta.from_image(img=image)
    print(ocm)


if __name__ == "__main__":
    print(f"{datetime.now()} Script started")

    print(f"{datetime.now()} Starting simulation")
    visibility = generate_visibilities()

    print(f"{datetime.now()} Creating visibility metadata")
    create_visibilities_metadata(visibility)

    print(f"{datetime.now()} Creating dirty image")
    dirty_image = create_dirty_image(visibility)

    print(f"{datetime.now()} Creating dirty image metadata")
    create_image_metadata(dirty_image)

    print(f"{datetime.now()} Creating cleaned image")
    cleaned_image = create_cleaned_image(visibility, dirty_image)

    print(f"{datetime.now()} Creating cleaned image metadata")
    create_image_metadata(cleaned_image)

    print(f"{datetime.now()} Script finished")

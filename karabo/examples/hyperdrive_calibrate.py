from karabo.calibration import HyperdriveCalibration, HyperdriveCalibrationConfig
from karabo.simulation.sky_model import SkyModel
from karabo.simulation.visibility import Visibility

# Configure the calibrator
config = HyperdriveCalibrationConfig(
    binary_path="hyperdrive",  # Path to your mwa_hyperdrive executable
    num_threads=4
)
hc = HyperdriveCalibration(config)

# Load data
vis = Visibility("path/to/observation.uvfits")
sky = SkyModel() # ... load or create your sky model ...

# Run calibration
solutions_path = hc.calibrate(
    visibility=vis,
    sky_model=sky,
    output_solutions_path="calibration_solutions.bin"
)
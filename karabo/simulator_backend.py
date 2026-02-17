import enum


class SimulatorBackend(enum.Enum):
    OSKAR = "OSKAR"
    RASCIL = "RASCIL"
    HYPERDRIVE = "HYPERDRIVE"

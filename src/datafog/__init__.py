from posthog import Posthog

from .__about__ import __version__
from .presidio import PresidioPolarFog

posthog = Posthog(
    "phc_v6vMICyVCGoYZ2s2xUWB4qoTPoMNFGv2u1q0KnBpaIb", host="https://app.posthog.com"
)

__all__ = [
    "__version__",
    "PresidioPolarFog",
]
posthog.capture("device_id", "init")

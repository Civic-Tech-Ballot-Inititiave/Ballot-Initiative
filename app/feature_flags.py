import os
from dataclasses import dataclass, field


@dataclass(frozen=True, repr=True)
class FeatureFlags:
    """
    Container to manage feature flags for the application.
    """

    demo_mode: bool = field(
        default_factory=lambda: os.getenv("FEATURE_DEMO_MODE", "false").lower()
        == "true"
    )

"""Importing this package registers every rule. Order here = order on the Trends page."""
from app.findings.rules import (  # noqa: F401
    souls,
    deaths_alone,
    deaths_same_spot,
    idle,
    items_late,
    objectives_missed,
    urn,
    lane_overstay,
)

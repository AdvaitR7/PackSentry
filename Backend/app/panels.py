"""
Panel Slot Naming (ADR-0009, ADR-0013).

A single inspection carries PDP and BACK plus up to MAX_SIDE_PANELS additional
SIDE panels. Because several SIDE images share one PanelRole, the role alone no
longer identifies an image — a (role, seq) pair does. `slot_key` renders that
pair as the stable token used for scratch filenames, Storage object paths, and
the /images/{role}/{kind} fallback route, so the three call sites cannot drift.
"""

from lmpc_schema import PanelRole

# Additional SIDE panels accepted beyond the required PDP and BACK.
MAX_SIDE_PANELS = 4


def slot_key(role: PanelRole, seq: int = 1) -> str:
    """
    Renders the filename/URL token for one panel.

    PDP and BACK are singular, so they keep their bare role name. SIDE panels are
    suffixed with their 1-based sequence: 'side_1' through 'side_4'.
    """
    if role == PanelRole.SIDE:
        return f"side_{seq}"
    return role.value.lower()

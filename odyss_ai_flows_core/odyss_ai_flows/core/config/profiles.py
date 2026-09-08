# Copyright 2026 ODYSS.AI AG
# SPDX-License-Identifier: Apache-2.0
#
# See the NOTICE file for attribution information.
# core/config/profiles.py
"""Named-profile registry resolution.

A profile registry holds several named profiles under one parent key, picked
by a sibling scalar selector:

    {
      "<selector_key>": "main",
      "<config_key>": {
        "main":      {...},
        "analytics": {...}
      }
    }

Scalar values sitting next to the profiles are read as an overlay merged onto
the selected profile, so a deeper scope can patch one field without naming the
profile: ``{"<config_key>": {"timeout": 30}}``.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple


def select_profile(
    registry: Mapping[str, Any],
    selector: Optional[str],
    *,
    config_label: str = "config",
    selector_label: str = "selector",
) -> Tuple[str, Dict[str, Any]]:
    """Resolve a profile registry to ``(profile_name, merged_config)``."""
    if not isinstance(registry, dict):
        raise TypeError(
            f"{config_label} must be a dict; got {type(registry).__name__}."
        )

    profiles = {k: v for k, v in registry.items() if isinstance(v, dict)}
    overlay = {k: v for k, v in registry.items() if not isinstance(v, dict)}

    if not profiles:
        raise TypeError(
            f"{config_label} defines no profiles. Use the registry form "
            f"{{'{config_label}': {{'<name>': {{...}}}}}} with a sibling "
            f"'{selector_label}' selector."
        )

    if selector is None:
        if len(profiles) == 1:
            name = next(iter(profiles))
        else:
            raise RuntimeError(
                f"{config_label} defines profiles {sorted(profiles)}; "
                f"set `{selector_label}` in scope to select one."
            )
    elif selector not in profiles:
        raise KeyError(
            f"{config_label}: {selector_label}={selector!r} not found in "
            f"registry. Available profiles: {sorted(profiles)}."
        )
    else:
        name = selector

    merged = {**profiles[name], **overlay} if overlay else dict(profiles[name])
    return name, merged

"""Bounded reviewed brand themes. No asset execution, template import or fallback."""

import hashlib
from pathlib import Path
import re
import string
import subprocess

from engagement import Invalid, identifier, revision
from qualification import text


NEUTRAL = {"font": "Liberation Sans", "ink": "12263A", "accent": "086C75", "muted": "465766"}


def reference(value):
    if not isinstance(value, dict) or set(value) != {"id", "revision"}:
        raise Invalid("Exact brand/source reference required")
    identifier(value["id"])
    revision(value["revision"])


def validate(value):
    if (not isinstance(value, dict) or set(value) != {"schema", "brand", "theme", "issuer", "classification"}
            or type(value["schema"]) is not int or value["schema"] != 1
            or any(not text(value[key]) or len(value[key]) > 120 for key in ("issuer", "classification"))):
        raise Invalid("Explicit bounded presentation identity required")
    theme = value["theme"]
    if (not isinstance(theme, dict) or set(theme) != set(NEUTRAL)
            or not isinstance(theme["font"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 -]{0,79}", theme["font"])
            or any(not isinstance(theme[key], str) or not re.fullmatch(r"[0-9A-F]{6}", theme[key])
                   for key in ("ink", "accent", "muted"))):
        raise Invalid("Theme needs a literal font family and six-digit uppercase RGB colors")
    # These layouts use white paper. Refuse rather than silently alter selected colors.
    for key in ("ink", "accent", "muted"):
        channels = [int(theme[key][i:i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
        luminance = sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))
        if 1.05 / (luminance + .05) < (3 if key == "accent" else 4.5):
            raise Invalid("Selected theme lacks supported white-page contrast; resolve and re-review the brand")
    if value["brand"] is None:
        if theme != NEUTRAL:
            raise Invalid("A custom theme needs an exact selected brand, not a silent neutral override")
    else:
        reference(value["brand"])


def validate_profile(data, selected):
    profile = data.get("brand")
    fields = {"schema", "identity", "variant", "resolved_base", "skill", "theme", "issuer", "classification",
              "classification_authority", "composition", "override", "unresolved"}
    if (data.get("purpose") != "brand-configuration" or not isinstance(profile, dict) or set(profile) != fields
            or type(profile["schema"]) is not int or profile["schema"] != 1
            or any(not text(profile[key]) for key in ("identity", "variant", "resolved_base",
                                                     "classification_authority", "override"))
            or not Path(profile["resolved_base"]).is_absolute()
            or profile["composition"] != "theme-only" or profile["unresolved"] != []):
        raise Invalid("Resolved theme-only brand profile, authority and conflict/asset disposition required")
    reference(profile["skill"])
    if any(profile[key] != selected[key] for key in ("theme", "issuer", "classification")):
        raise Invalid("Packet presentation differs from the selected brand profile")
    return profile["skill"]


def palette(packet):
    theme = packet.get("presentation", {}).get("theme", NEUTRAL)
    return tuple(theme[key] for key in ("font", "ink", "accent", "muted"))


def identity(packet):
    value = packet.get("presentation")
    return f"{value['issuer']} · {value['classification']}" if value else ""


def font_identity(family, content=""):
    files = {}
    # Include the renderers' English labels and punctuation, not just supplied text.
    required = {ord(c) for c in content + string.printable + "·—–≠" if c not in "\n\r\t\v\f"}
    for style in ("Regular", "Bold"):
        match = subprocess.run(["fc-match", "-f", "%{family}\n%{file}", family + ":style=" + style],
                               capture_output=True, text=True, check=True, timeout=10).stdout.splitlines()
        if len(match) != 2 or family not in match[0].split(","):
            raise Invalid("Selected font unavailable; record an authorized substitution and re-review, never silently fall back")
        charset = subprocess.run(["fc-query", "-f", "%{charset}", match[1]], capture_output=True,
                                 text=True, check=True, timeout=10).stdout
        covered = set()
        for span in charset.split():
            ends = span.split("-")
            covered.update(range(int(ends[0], 16), int(ends[-1], 16) + 1))
        if required - covered:
            raise Invalid("Selected font lacks required glyphs; authorize a covering font and re-review, never silently fall back")
        files[style] = hashlib.sha256(Path(match[1]).read_bytes()).hexdigest()
    return files

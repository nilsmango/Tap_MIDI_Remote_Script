#!/usr/bin/env python3
"""Create a Tap-enabled Granulator III copy without touching Ableton's factory device."""

from __future__ import annotations

import json
import struct
from pathlib import Path


SOURCE = Path(
    "/Users/simxn/Music/Ableton/Factory Packs/Granulator III/Granulator III/"
    "Ableton Folder Info/Granulator III.amxd"
)
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Granulator III Tap" / "Granulator III Tap.amxd"


def box(box_id: str, text: str, x: float, y: float) -> dict:
    return {
        "box": {
            "id": box_id,
            "maxclass": "newobj",
            "numinlets": 1 if text.startswith("node.script") else 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [x, y, max(90.0, len(text) * 6.4), 22.0],
            "text": text,
            "hidden": 1,
        }
    }


def line(source: str, destination: str, outlet: int = 0) -> dict:
    return {
        "patchline": {
            "source": [source, outlet],
            "destination": [destination, 0],
            "hidden": 1,
        }
    }


def build() -> None:
    data = SOURCE.read_bytes()
    if data[:4] != b"ampf" or data[24:28] != b"ptch":
        raise RuntimeError("Unexpected AMXD container")

    decoded = data[48:].decode("utf-8", "surrogateescape")
    document, char_end = json.JSONDecoder().raw_decode(decoded)
    json_end = 48 + len(decoded[:char_end].encode("utf-8", "surrogateescape"))
    patcher = document["patcher"]

    tap_ids = {"tap-path", "tap-info", "tap-grain", "tap-node", "tap-route", "tap-marker"}
    patcher["boxes"] = [
        entry for entry in patcher["boxes"] if entry["box"].get("id") not in tap_ids
    ]
    patcher["lines"] = [
        entry
        for entry in patcher["lines"]
        if entry["patchline"]["source"][0] not in tap_ids
        and entry["patchline"]["destination"][0] not in tap_ids
    ]

    patcher["boxes"].extend(
        [
            box("tap-path", "prepend path", 1120.0, 630.0),
            box("tap-info", "prepend info", 1120.0, 660.0),
            box("tap-grain", "prepend grain", 1120.0, 690.0),
            box(
                "tap-node",
                "node.script tap_granulator_bridge.js @autostart 1",
                1260.0,
                660.0,
            ),
            {
                "box": {
                    "id": "tap-route",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": ["", ""],
                    "patching_rect": [1570.0, 660.0, 90.0, 22.0],
                    "text": "route instance",
                    "hidden": 1,
                }
            },
            {
                "box": {
                    "id": "tap-marker",
                    "maxclass": "live.numbox",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": ["", "float"],
                    "parameter_enable": 1,
                    "patching_rect": [1680.0, 660.0, 44.0, 15.0],
                    "hidden": 1,
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_initial": [0.0],
                            "parameter_initial_enable": 1,
                            "parameter_linknames": 1,
                            "parameter_longname": "Tap Bridge",
                            "parameter_mmax": 65535.0,
                            "parameter_mmin": 0.0,
                            "parameter_shortname": "Tap Bridge",
                            "parameter_type": 1,
                            "parameter_unitstyle": 0,
                        }
                    },
                    "varname": "Tap Bridge",
                }
            },
        ]
    )
    patcher["lines"].extend(
        [
            line("obj-28", "tap-path"),
            line("obj-5", "tap-info", outlet=2),
            line("obj-38", "tap-grain"),
            line("tap-path", "tap-node"),
            line("tap-info", "tap-node"),
            line("tap-grain", "tap-node"),
            line("tap-node", "tap-route"),
            line("tap-route", "tap-marker"),
        ]
    )

    patcher.setdefault("parameters", {})["tap-marker"] = ["Tap Bridge", "Tap Bridge", 0]

    # Do not add an AMXD dependency_cache entry for the adjacent script.  A
    # literal relative bootpath (".") is invalid inside the packed device and
    # makes Max attempt to create a directory while loading it.  node.script
    # resolves files beside the device through Max's normal patcher search path.
    dependencies = patcher.setdefault("dependency_cache", [])
    dependencies[:] = [
        entry for entry in dependencies if entry.get("name") != "tap_granulator_bridge.js"
    ]

    encoded = json.dumps(document, ensure_ascii=False, indent=1).encode(
        "utf-8", "surrogateescape"
    )
    content = data[32:48] + encoded + data[json_end:]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(data[:28] + struct.pack("<I", len(content)) + content)

    rebuilt = OUTPUT.read_bytes()
    if struct.unpack_from("<I", rebuilt, 28)[0] != len(rebuilt) - 32:
        raise RuntimeError("AMXD length check failed")
    reparsed, _ = json.JSONDecoder().raw_decode(
        rebuilt[48:].decode("utf-8", "surrogateescape")
    )
    ids = {entry["box"].get("id") for entry in reparsed["patcher"]["boxes"]}
    if not tap_ids.issubset(ids):
        raise RuntimeError("Tap bridge objects missing from rebuilt AMXD")
    if any(
        entry.get("name") == "tap_granulator_bridge.js"
        for entry in reparsed["patcher"].get("dependency_cache", [])
    ):
        raise RuntimeError("Tap bridge must not use an embedded relative bootpath")

    print(f"Built {OUTPUT}")


if __name__ == "__main__":
    build()

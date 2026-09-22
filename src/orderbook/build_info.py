"""Build provenance checks used outside the matching/benchmark timing path."""

import hashlib
import json
from pathlib import Path
import sys
import sysconfig

SOURCES = (
    "cpp/core.hpp",
    "cpp/bindings.cpp",
    "scripts/build_native.py",
    "src/orderbook/build_info.py",
)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes(root):
    return {name: file_hash(root / name) for name in SOURCES}


def validate_native_build(root, binary):
    """Fail closed on stale/missing metadata, changed source, or a different binary."""
    root, binary = Path(root).resolve(), Path(binary).resolve()
    try:
        data = json.loads((root / "native-build.json").read_text())
        expected = (
            root
            / "src/orderbook"
            / ("_native" + sysconfig.get_config_var("EXT_SUFFIX"))
        )
        valid = (
            isinstance(data, dict)
            and data.get("schema") == 1
            and data.get("sources") == source_hashes(root)
            and data.get("python_cache_tag") == sys.implementation.cache_tag
            and data.get("soabi") == sysconfig.get_config_var("SOABI")
            and binary == expected.resolve()
            and data.get("binary_sha256") == file_hash(binary)
            and isinstance(data.get("command"), list)
            and bool(data["command"])
            and isinstance(data.get("compiler"), str)
            and bool(data["compiler"])
        )
    except (OSError, ValueError, TypeError):
        valid = False
    if not valid:
        raise RuntimeError(
            "Native build provenance is missing or stale; "
            "run python scripts/build_native.py before benchmarking"
        )
    return data

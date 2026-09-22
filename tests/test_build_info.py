"""Provenance regression tests: stale results must fail before any timing."""

import json
import sys
import sysconfig

import pytest

from orderbook.build_info import (
    SOURCES,
    file_hash,
    source_hashes,
    validate_native_build,
)


@pytest.fixture
def build(tmp_path):
    for name in SOURCES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
    binary = (
        tmp_path
        / "src/orderbook"
        / ("_native" + sysconfig.get_config_var("EXT_SUFFIX"))
    )
    binary.write_bytes(b"fixture binary")
    data = dict(
        schema=1,
        sources=source_hashes(tmp_path),
        binary_sha256=file_hash(binary),
        python_cache_tag=sys.implementation.cache_tag,
        soabi=sysconfig.get_config_var("SOABI"),
        command=["c++", "-O3"],
        compiler="test",
    )
    metadata = tmp_path / "native-build.json"
    metadata.write_text(json.dumps(data))
    return tmp_path, binary, metadata, data


def test_matching_build(build):
    root, binary, _, data = build
    assert validate_native_build(root, binary) == data


@pytest.mark.parametrize(
    "failure",
    [
        "missing",
        "invalid_json",
        "empty",
        "schema",
        "source",
        "binary",
        "python",
        "soabi",
        "other_checkout",
    ],
)
def test_unverifiable_build_is_rejected(build, failure):
    root, binary, metadata, data = build
    if failure == "missing":
        metadata.unlink()
    elif failure == "invalid_json":
        metadata.write_text("{broken")
    elif failure == "empty":
        metadata.write_text("{}")
    elif failure == "source":
        (root / SOURCES[0]).write_text("changed matching rules")
    elif failure == "binary":
        binary.write_bytes(b"different binary")
    elif failure == "other_checkout":
        other = root / "elsewhere" / binary.name
        other.parent.mkdir()
        other.write_bytes(binary.read_bytes())
        binary = other
    else:
        key = {"schema": "schema", "python": "python_cache_tag", "soabi": "soabi"}[
            failure
        ]
        data[key] = "wrong"
        metadata.write_text(json.dumps(data))
    with pytest.raises(RuntimeError, match="build provenance"):
        validate_native_build(root, binary)

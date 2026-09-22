"""Build the optional extension; no compiler is needed for the Python engine."""

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import sysconfig
import tempfile

import pybind11

ROOT = Path(__file__).resolve().parents[1]
# Use this checkout's helpers even when another Redline is installed.
sys.path.insert(0, str(ROOT / "src"))


def main():
    from orderbook.build_info import file_hash, source_hashes

    parser = argparse.ArgumentParser()
    parser.add_argument("--cxx", default=os.environ.get("CXX", "c++"))
    args = parser.parse_args()
    if sys.platform == "win32":
        parser.error("Use Linux/WSL or macOS for this build helper.")
    compiler = shlex.split(args.cxx)
    if not compiler:
        parser.error("--cxx must name a compiler")
    version = subprocess.check_output(compiler + ["--version"], text=True).splitlines()[
        0
    ]
    sources = source_hashes(ROOT)
    output = (
        ROOT / "src/orderbook" / ("_native" + sysconfig.get_config_var("EXT_SUFFIX"))
    )
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="native-", dir=build) as temporary:
        temporary = Path(temporary)
        artifact = temporary / output.name
        command = compiler + [
            "-O3",
            "-DNDEBUG",
            "-std=c++17",
            "-shared",
            "-fPIC",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-fvisibility=hidden",
            "-I" + pybind11.get_include(),
            "-I" + sysconfig.get_path("include"),
            str(ROOT / "cpp/bindings.cpp"),
            "-o",
            str(artifact),
        ]
        if sys.platform == "darwin":
            command += ["-undefined", "dynamic_lookup"]
        subprocess.run(command, check=True)
        if source_hashes(ROOT) != sources:
            raise RuntimeError("Sources changed during compilation; rebuild")
        metadata = dict(
            schema=1,
            command=command,
            sources=sources,
            compiler=version,
            binary_sha256=file_hash(artifact),
            python_cache_tag=sys.implementation.cache_tag,
            soabi=sysconfig.get_config_var("SOABI"),
        )
        metadata_path = temporary / "native-build.json"
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
        # A compiler failure cannot overwrite a working extension. A process
        # interruption between these two replacements is caught by provenance.
        os.replace(artifact, output)
        os.replace(metadata_path, ROOT / "native-build.json")
    print(output)


if __name__ == "__main__":
    main()

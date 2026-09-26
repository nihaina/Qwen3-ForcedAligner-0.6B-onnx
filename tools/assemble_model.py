#!/usr/bin/env python3
"""Reassemble the Qwen3 ForcedAligner ONNX external weights from Release assets."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path


BUFFER_SIZE = 8 * 1024 * 1024
GRAPH_NAME = "forced_aligner.onnx"
DATA_NAME = "forced_aligner.onnx.data"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path.cwd(), help="Directory containing all Release assets")
    args = parser.parse_args()
    directory = args.directory.resolve()
    manifest = directory / "SHA256SUMS.txt"
    checksums = {}
    for line in manifest.read_text(encoding="ascii").splitlines():
        digest, name = line.split("  ", 1)
        checksums[name] = digest

    graph = directory / GRAPH_NAME
    if sha256(graph) != checksums[GRAPH_NAME]:
        raise ValueError(f"Checksum mismatch: {graph.name}")

    parts = sorted(name for name in checksums if name.startswith(DATA_NAME + ".part"))
    if not parts or parts != [f"{DATA_NAME}.part{i:02d}" for i in range(1, len(parts) + 1)]:
        raise ValueError("The checksum file does not list a complete sequence of weight parts")

    output = directory / DATA_NAME
    if output.exists():
        if sha256(output) != checksums[DATA_NAME]:
            raise ValueError(f"Existing file has a different checksum: {output}")
        print(f"Already verified: {output}", flush=True)
        return
    temporary = directory / (DATA_NAME + ".tmp")
    full_hash = hashlib.sha256()
    try:
        with temporary.open("wb") as destination:
            for name in parts:
                part_hash = hashlib.sha256()
                with (directory / name).open("rb") as source:
                    while block := source.read(BUFFER_SIZE):
                        destination.write(block)
                        part_hash.update(block)
                        full_hash.update(block)
                if part_hash.hexdigest() != checksums[name]:
                    raise ValueError(f"Checksum mismatch: {name}")
                print(f"Verified {name}", flush=True)
        if full_hash.hexdigest() != checksums[DATA_NAME]:
            raise ValueError(f"Checksum mismatch: {DATA_NAME}")
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Ready: {output}", flush=True)


if __name__ == "__main__":
    main()

"""Local-only AN9J save compatibility restoration; contains no game code bytes."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import sys

VERSION = '0.5'


class RestoreError(ValueError):
    """A source, recipe, or output did not satisfy the restoration contract."""


@dataclass(frozen=True)
class Image:
    size: int
    sha256: str


@dataclass(frozen=True)
class Recipe:
    korean: Image
    japanese: Image
    result: Image
    windows: tuple[tuple[int, int], ...]  # (file offset, byte length)
    differences: tuple[tuple[int, int], ...]  # half-open intervals


# Revision identities and coordinates only. All replacement bytes come from
# the user's local Japanese input, never from an embedded patch or download.
V05 = Recipe(
    korean=Image(12582912, 'f94cb5a128c8a98e6e18e6a0598ebf9b266f54da0750367af8defac3eb2df7d4'),
    japanese=Image(8388608, 'a92c0f6dbb5c013b47b7178e23d81663e3952a10df7b1f68967ebf7bb3b98eb7'),
    result=Image(12582912, '9c7a8ae87c303a16c71bd164e7409a5aaabf01bd3246fa9e700931eed6179d4f'),
    windows=((0xA60D4, 4), (0xA6258, 40), (0xA6308, 40)),
    differences=((0xA60D4, 0xA60D8), (0xA625A, 0xA625D), (0xA625E, 0xA6280),
                 (0xA6308, 0xA6309), (0xA630A, 0xA630D), (0xA630E, 0xA6330)),
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_image(data: bytes, expected: Image, label: str) -> None:
    if len(data) != expected.size or digest(data) != expected.sha256:
        raise RestoreError(f'{label}: unsupported or damaged file; expected '
                           f'{expected.size} bytes, SHA-256 {expected.sha256}')


def validate_recipe(recipe: Recipe) -> tuple[int, ...]:
    if recipe.result.size != recipe.korean.size:
        raise RestoreError('Resizing is not permitted')
    last_end = 0
    writable: set[int] = set()
    for offset, length in recipe.windows:
        if type(offset) is not int or type(length) is not int or offset < 0 or length <= 0:
            raise RestoreError('Invalid write window')
        end = offset + length
        if offset < last_end or end > min(recipe.korean.size, recipe.japanese.size):
            raise RestoreError('Overlapping, unordered, or out-of-bounds write window')
        writable.update(range(offset, end))
        last_end = end
    expected: list[int] = []
    last_end = 0
    for begin, end in recipe.differences:
        if type(begin) is not int or type(end) is not int or begin < last_end or end <= begin:
            raise RestoreError('Invalid or overlapping difference interval')
        positions = range(begin, end)
        if not set(positions).issubset(writable):
            raise RestoreError('Difference outside registered write windows')
        expected.extend(positions)
        last_end = end
    if not expected:
        raise RestoreError('An empty restoration recipe is not supported')
    return tuple(expected)


def verify_result(korean: bytes, japanese: bytes, result: bytes,
                  recipe: Recipe = V05) -> None:
    expected = validate_recipe(recipe)
    check_image(korean, recipe.korean, 'Korean input')
    check_image(japanese, recipe.japanese, 'Japanese input')
    check_image(result, recipe.result, 'Result')
    changed = tuple(i for i, (before, after) in enumerate(zip(korean, result)) if before != after)
    if changed != expected:
        raise RestoreError('Result differs outside the exact registered difference set')
    for offset, length in recipe.windows:
        if result[offset:offset + length] != japanese[offset:offset + length]:
            raise RestoreError('Restored window does not match the donor')


def restore_bytes(korean: bytes, japanese: bytes, recipe: Recipe = V05) -> bytes:
    """Plan from immutable inputs, apply one write path, verify the whole result."""
    validate_recipe(recipe)
    check_image(korean, recipe.korean, 'Korean input')
    check_image(japanese, recipe.japanese, 'Japanese input')
    plan = [(offset, japanese[offset:offset + length]) for offset, length in recipe.windows]
    output = bytearray(korean)
    for offset, replacement in plan:
        output[offset:offset + len(replacement)] = replacement
    result = bytes(output)
    verify_result(korean, japanese, result, recipe)
    return result


def read_input(path: Path, expected: Image, label: str) -> bytes:
    if not path.is_file() or path.stat().st_size != expected.size:
        raise RestoreError(f'{label}: expected a regular file of {expected.size} bytes')
    with path.open('rb') as stream:
        data = stream.read(expected.size + 1)
    check_image(data, expected, label)
    return data


def restore_files(korean_path: Path, japanese_path: Path, output_path: Path,
                  recipe: Recipe = V05) -> dict:
    # Do not resolve the output through an existing/dangling symlink.
    output_path = output_path.absolute()
    if os.path.lexists(output_path):
        raise RestoreError('Output already exists; overwriting is never allowed')
    if output_path.resolve() in (korean_path.resolve(), japanese_path.resolve()):
        raise RestoreError('Output must not alias either input')
    if output_path.suffix.lower() != '.gba':
        raise RestoreError('Choose a new .gba output file, never a .sav file')
    if not output_path.parent.is_dir():
        raise RestoreError('Output parent directory must already exist')
    korean = read_input(korean_path, recipe.korean, 'Korean input')
    japanese = read_input(japanese_path, recipe.japanese, 'Japanese input')
    result = restore_bytes(korean, japanese, recipe)
    # Exclusive creation also rejects a file created after the earlier check.
    # If a disk write fails, do not claim success or overwrite/delete anything.
    try:
        with output_path.open('xb') as stream:
            stream.write(result)
            stream.flush()
            os.fsync(stream.fileno())
        persisted = output_path.read_bytes()
        verify_result(korean, japanese, persisted, recipe)
    except OSError as error:
        raise RestoreError(f'Output write/read failed. A new incomplete output may remain; '
                           f'do not use it. Inputs are unchanged. {error}') from error
    return {'version': VERSION, 'output_sha256': digest(persisted),
            'output_size': len(persisted), 'changed_bytes': len(validate_recipe(recipe)),
            'all_other_bytes_identical': True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='AN9J v0.5 local save compatibility restoration')
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('--korean', type=Path, required=True, help='Untouched K_FFR Korean ROM')
    parser.add_argument('--japanese', type=Path, required=True, help='Matching Japanese donor ROM')
    parser.add_argument('--output', type=Path, required=True, help='NEW .gba file; no overwrites')
    args = parser.parse_args(argv)
    try:
        report = restore_files(args.korean, args.japanese, args.output)
    except (RestoreError, OSError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
    print(f"OK: {report['changed_bytes']} bytes restored; all other bytes unchanged.")
    print(f"SHA-256: {report['output_sha256']}")
    print('Save files were not read or modified. Keep your own backups.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

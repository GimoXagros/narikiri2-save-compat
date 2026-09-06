"""Apply v0.9b only to the exact FFR BETA3(071102) cartridge."""
import argparse
import hashlib
import os
from pathlib import Path
from bps import apply_bps

SOURCE = 'c6d7a401aa2a22362b2d27d0d31632cb2180a86b094788815d949b84c7fc944d'
TARGET = 'd761088a8549cb5bc60a2f03a4b78eea5282dbc17ed5da4ef1de27da4ad8d4d4'
PATCH = '51dbdb8ef24a32ca5efb05ec3196b98ae08a32f3a4d6bb88673d58266837dcf6'
NAME = 'NARIKIRI2_AN9J_K_DALMOORI_v0.9b'


def checked(source, patch):
    sha = lambda data: hashlib.sha256(data).hexdigest()
    if len(source) != 9961472 or sha(source) != SOURCE:
        raise ValueError('Exact original FFR BETA3(071102) required; BETA2, Japanese and previously patched ROMs are not accepted')
    if sha(patch) != PATCH:
        raise ValueError('The BPS file is not the verified v0.9b patch')
    target = apply_bps(source, patch)
    if len(target) != 13107200 or sha(target) != TARGET:
        raise ValueError('Patched cartridge verification failed')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--patch', type=Path, default=Path(__file__).with_name(NAME+'_FROM_BETA3.bps'))
    parser.add_argument('--output', type=Path, default=Path(NAME+'.gba'))
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Output exists; choose a new filename to preserve your files')
    target = checked(args.source.read_bytes(), args.patch.read_bytes())
    with args.output.open('xb') as stream:
        stream.write(target)
        stream.flush()
        os.fsync(stream.fileno())
    if args.output.read_bytes() != target:
        raise OSError('Output read-back verification failed')
    print('Verified v0.9b ROM: '+str(args.output.resolve()))
    print('SHA-256: '+TARGET)


if __name__ == '__main__':
    main()

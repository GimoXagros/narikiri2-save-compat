"""Apply the cumulative v0.9a BPS with exact source, patch and target checks."""
import argparse,hashlib,os
from pathlib import Path
from bps import apply_bps
SOURCE='f94cb5a128c8a98e6e18e6a0598ebf9b266f54da0750367af8defac3eb2df7d4'
TARGET='faa2f0ebe1f7bbd9f4a7e1d38b7d35ca2349bfed1d8c2a5d8ae45feb0f7631f6'
PATCH='9289ff85f946fa661c17dee9a9cb6afcd91278caf1af23590e59964ad461810a'
NAME='NARIKIRI2_AN9J_K_DALMOORI_v0.9a'

def checked(source,patch):
    sha=lambda b:hashlib.sha256(b).hexdigest()
    if len(source)!=12582912 or sha(source)!=SOURCE:raise ValueError('The input must be the exact supported original FFR ROM')
    if sha(patch)!=PATCH:raise ValueError('The BPS file is not the verified v0.9a patch')
    target=apply_bps(source,patch)
    if len(target)!=13041664 or sha(target)!=TARGET:raise ValueError('Patched ROM verification failed')
    return target

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('--patch',type=Path,default=Path(__file__).with_name(NAME+'_FROM_FFR.bps'))
    p.add_argument('--output',type=Path,default=Path(NAME+'.gba'));a=p.parse_args()
    if a.output.exists():raise ValueError('Output exists; choose a new filename to preserve your files')
    target=checked(a.source.read_bytes(),a.patch.read_bytes())
    with a.output.open('xb') as f:
        f.write(target);f.flush();os.fsync(f.fileno())
    if a.output.read_bytes()!=target:raise OSError('Output read-back verification failed')
    print('Verified v0.9a ROM: '+str(a.output.resolve()))
    print('SHA-256: '+TARGET)

if __name__=='__main__':main()

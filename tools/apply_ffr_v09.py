"""Apply the single v0.9 BPS after checking full source, patch and target hashes."""
import argparse,hashlib,os
from pathlib import Path
from bps import apply_bps
SOURCE='f94cb5a128c8a98e6e18e6a0598ebf9b266f54da0750367af8defac3eb2df7d4'
TARGET='560535ba5dce7246a4c1b210a082b93a08091b8f9e2bfa96467e44adbbf65c81'
PATCH='38cba8fbf0fee41af02859df1a607eda2dbedee17f37afbb05fac05316449866'
NAME='NARIKIRI2_AN9J_K_DALMOORI_v0.9'
def checked(source,patch):
    sha=lambda b:hashlib.sha256(b).hexdigest()
    if len(source)!=12582912 or sha(source)!=SOURCE:raise ValueError('The input must be the exact supported FFR ROM')
    if sha(patch)!=PATCH:raise ValueError('The BPS file is not the verified v0.9 patch')
    target=apply_bps(source,patch)
    if len(target)!=12713984 or sha(target)!=TARGET:raise ValueError('Patched ROM verification failed')
    return target
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('--patch',type=Path,default=Path(__file__).with_name(NAME+'_FROM_FFR.bps'))
    p.add_argument('--output',type=Path,default=Path(NAME+'.gba'));a=p.parse_args()
    if a.output.exists():raise ValueError('Output exists; choose a new filename to preserve your files')
    target=checked(a.source.read_bytes(),a.patch.read_bytes())
    # Exclusive creation also protects against a race with another invocation.
    with a.output.open('xb') as f:
        f.write(target);f.flush();os.fsync(f.fileno())
    if a.output.read_bytes()!=target:raise OSError('Output read-back verification failed')
    print('Verified v0.9 ROM: '+str(a.output.resolve()))
    print('SHA-256: '+TARGET)
if __name__=='__main__':main()

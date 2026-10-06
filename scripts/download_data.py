"""Restore input data from pinned owner mirrors; never silently trust changed bytes."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def main():
    manifest = json.loads((ROOT/'research/upstream-data-manifest.json').read_text())
    wanted = {'training_features','existing_faults','sample_submission','ext_gdr_qfaults_traces'}
    receipt = []
    for e in manifest['files']:
        if e['id'] not in wanted: continue
        dest = ROOT/'data'/e['dest']; dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or sha256(dest) != e['sha256']:
            temp = dest.with_suffix('.partial')
            with temp.open('wb') as out:
                for p in e.get('parts', [e.get('path')]):
                    print('Fetching',p,flush=True)
                    subprocess.run(['gh','api',f"repos/{e['repo']}/contents/{p}?ref={e['ref']}",'-H','Accept: application/vnd.github.raw'],stdout=out,check=True)
            if sha256(temp) != e['sha256']: raise ValueError(f'Checksum mismatch: {dest}')
            temp.replace(dest)
        receipt.append(e)
    # Educational benchmark only. Model construction never reads this raster.
    ref=(ROOT/'research/comparison-ref.txt').read_text().strip()
    path='docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif'
    dest=ROOT/'data/comparison-h33.tif'
    expected='c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9'
    if not dest.exists() or sha256(dest)!=expected:
        temp=dest.with_suffix('.partial')
        with temp.open('wb') as out:
            subprocess.run(['gh','api',f'repos/buffedlizard55-lab/GEMSDOE32/contents/{path}?ref={ref}','-H','Accept: application/vnd.github.raw'],stdout=out,check=True)
        if sha256(temp)!=expected: raise ValueError('Historical comparison checksum mismatch')
        temp.replace(dest)
    official=ROOT/'data/official/qfaults.zip'
    if sha256(official)!='c7b091c9ac8bca140ad89ee6bb2bd63dd3ac12e3013acbfd8373d11c9faee59d':
        raise ValueError('Official archived geometry checksum mismatch')
    (ROOT/'research/input-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')

if __name__ == '__main__': main()

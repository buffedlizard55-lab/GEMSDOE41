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
    (ROOT/'research/input-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')

if __name__ == '__main__': main()

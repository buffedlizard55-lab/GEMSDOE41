"""Review provided sibling site source via GitHub API; do not ingest predictions.

These are owner reports, not official validation. Direct HTTP is sandbox-blocked.
"""
import base64
import concurrent.futures
import hashlib
import html
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITES=[('GEMSDOE','docs/index.html'),('6GEMSDOE','index.html'),('GEMSDOE3','docs/index.html'),('GEMSDOE2','docs/index.html'),('GEMSDOE4','index.html'),('5GEMSDOE','docs/index.html'),('7GEMSDOE','index.html'),('8GEMSDOE','index.html'),('GEMSDOE9','docs/index.html'),('11GEMSDOE','docs/index.html'),('12GEMSDOE','docs/index.html'),('15GEMSDOE','docs/index.html'),('14GEMSDOE','docs/index.html'),('17GEMSDOE','index.html'),('18GEMSDOE','index.html'),('19GEMSDOE','docs/index.html'),('GEMSDOE10','index.html'),('13GEMSDOE','index.html'),('16GEMSDOE','docs/index.html'),('GEMSDOE21','index.html'),('20GEMSDOE','docs/index.html'),('GEMSDOE22','docs/index.html'),('GEMSDOE23','index.html'),('GEMSDOE24','docs/index.html'),('GEMSDOE25','docs/index.html'),('GEMSDOE26','docs/index.html'),('GEMSDOE27','docs/index.html'),('GEMSDOE28','docs/index.html'),('GEMSDOE29','docs/index.html'),('GEMSDOE30','index.html'),('GEMSDOE31','docs/index.html'),('GEMSDOE32','docs/index.html'),('GEMSDOE33','index.html'),('GEMSDOE34','docs/index.html'),('GEMSDOE35','docs/index.html'),('GEMSDOE36','docs/index.html'),('GEMSDOE37','index.html'),('GEMSDOE38','docs/index.html'),('GEMSDOE39','index.html')]

def audit(item):
    repo,path=item
    result=dict(repo=repo,url=f'https://buffedlizard55-lab.github.io/{repo}/{path}',evidence_class='secondary owner-authored site source, NOT organizer receipt')
    p=subprocess.run(['gh','api',f'repos/buffedlizard55-lab/{repo}/contents/{path}'],capture_output=True,text=True)
    if p.returncode:
        result.update(status='unavailable',error=p.stderr[:400]);return result
    obj=json.loads(p.stdout)
    if not obj.get('content'):
        result.update(status='no_inline_content');return result
    raw=base64.b64decode(obj['content']).decode('utf-8',errors='replace')
    # Strip scripts/styles, then markup, to avoid treating code as claims.
    text=re.sub(r'<(script|style)\b[^>]*>.*?</\1>',' ',raw,flags=re.S|re.I)
    text=html.unescape(re.sub('<[^>]+>',' ',text));text=re.sub(r'\s+',' ',text)
    snippets=[]
    for word in ['PRIMARY','Download','holdout','0.2778','hypoth','score']:
        m=re.search(re.escape(word),text,re.I)
        if m:snippets.append(text[max(0,m.start()-60):m.start()+420])
    result.update(status='source_reviewed',github_blob_sha=obj['sha'],text_sha256=hashlib.sha256(text.encode()).hexdigest(),excerpt=text[:500],claim_excerpts=snippets,
                  warning='Snapshot of repository source; redirect targets and dynamic rendered contents not exhaustively reviewed.')
    return result

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool: rows=list(pool.map(audit,SITES))
    p=ROOT/'docs/related-sites.json';p.write_text(json.dumps(dict(checked_utc='2026-10-05',method='GitHub contents API source audit',sites=rows),indent=2)+'\n')
    print({s:sum(r['status']==s for r in rows) for s in set(r['status'] for r in rows)})
if __name__=='__main__':main()

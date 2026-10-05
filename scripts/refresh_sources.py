"""Daily public-source health snapshot; no credentials or competition submissions.

Run in GitHub Actions where direct internet transport is available. Failures are
published explicitly; a failed fetch must never be presented as a current score.
"""
from datetime import datetime,timezone
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import requests

URLS={
'leaderboard':'https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/',
'problem':'https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/',
'rules':'https://docs.nlr.gov/docs/fy26osti/96647.pdf',
'ingenious':'https://gdr.openei.org/submissions/1391',
'faulds2005':'https://nbmg.unr.edu/staff/Faulds/faulds_et_al_geology_paper.pdf',
'astor_pass':'https://www.osti.gov/servlets/purl/1110516',
'emerson_pass':'https://www.osti.gov/servlets/purl/1110518'}

class TableParser(HTMLParser):
    """Small text-only HTML table parser; retain line breaks inside cells."""
    def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        if tag in ('td','th') and self.row is not None:self.cell=''
        elif tag=='br' and self.cell is not None:self.cell+='\n'
    def handle_data(self,text):
        if self.cell is not None:self.cell+=text
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(self.cell.strip());self.cell=None
        if tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None


def _ranked_table_rows(rows):
    """Extract rank, displayed participant, and score without inventing file IDs."""
    import re
    rank_re=re.compile(r'^#?\s*(\d+)\b')
    score_re=re.compile(r'^0\.\d{4,}$')
    participant_col=None
    for row in rows:
        headers=[cell.casefold().strip() for cell in row]
        if any(h=='rank' for h in headers) and any('participant' in h for h in headers):
            participant_col=next(i for i,h in enumerate(headers) if 'participant' in h)
            break
    result=[]
    for row in rows:
        ranks=[rank_re.match(cell.strip()) for cell in row]
        rank_match=next((m for m in ranks if m),None)
        score=next((float(cell.strip()) for cell in row if score_re.fullmatch(cell.strip())),None)
        if rank_match is None or score is None or not 0<=score<=1:continue
        participant=None
        if participant_col is not None and participant_col<len(row):
            lines=[line.strip() for line in row[participant_col].splitlines() if line.strip()]
            participant=lines[0] if lines else None
        if not participant:
            candidates=[cell.strip() for cell in row if cell.strip() and not rank_re.match(cell.strip()) and not score_re.fullmatch(cell.strip())]
            participant=candidates[0] if candidates else None
        result.append({'rank':int(rank_match.group(1)),'participant':participant,'score':score})
    return sorted(result,key=lambda item:item['rank'])


def parse_ranked_scores(text):
    parser=TableParser();parser.feed(text)
    return _ranked_table_rows(parser.rows)


def parse_scores(text):
    """Compatibility helper returning only scores from structurally ranked rows."""
    return [row['score'] for row in parse_ranked_scores(text)]


def valid_leaderboard_rows(rows):
    """Require the page's first three sequential ranks before calling it a snapshot."""
    return (len(rows)>=3 and [row['rank'] for row in rows[:3]]==[1,2,3]
            and all(0<=row['score']<=1 for row in rows))


def parse_rendered_rank_rows(text):
    """Read visible rank/participant/score lines, never numbers in JS source."""
    import re
    parsed=[];rank=None;pending=[]
    def flush():
        nonlocal rank,pending
        if rank is not None:
            scores=[line for line in pending if re.fullmatch(r'0\.\d{4,}',line)]
            if scores:
                participant=next((line for line in pending if not re.fullmatch(r'0\.\d{4,}',line) and not re.fullmatch(r'\d+\s+submissions?',line,re.I)),None)
                parsed.append({'rank':rank,'participant':participant,'score':float(scores[0])})
        rank=None;pending=[]
    for raw in text.splitlines():
        line=raw.strip()
        match=re.fullmatch(r'#?\s*(\d+)',line)
        if match:
            flush();rank=int(match.group(1))
        elif rank is not None and line:
            pending.append(line)
    flush()
    # Require a sequential visible lead rather than accepting an isolated number.
    if len(parsed)<3 or [row['rank'] for row in parsed[:3]]!=[1,2,3]:return []
    return parsed


def parse_rendered_ranks(text):
    """Compatibility helper for callers that need only the rendered scores."""
    return [row['score'] for row in parse_rendered_rank_rows(text)]


def render_public_leaderboard(url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as browser_api:
        browser=browser_api.chromium.launch()
        try:
            page=browser.new_page()
            page.goto(url,wait_until='domcontentloaded',timeout=45000)
            try:
                page.wait_for_function("/0[.][0-9]{4}/.test(document.body.innerText)",timeout=30000)
            except Exception:
                pass  # Inspect the visible page even on timeout; never invent scores.
            text=page.inner_text('body')
            rows=parse_ranked_scores(page.content())
            if not valid_leaderboard_rows(rows):rows=parse_rendered_rank_rows(text)
            if not valid_leaderboard_rows(rows):rows=[]
            return rows, hashlib.sha256(text.encode()).hexdigest(), text[:5000]
        finally: browser.close()


def main():
    output={'checked_utc':datetime.now(timezone.utc).isoformat(),'method':'public HTTP fetch; daily snapshot, not live scoring','leader_score':None,'sources':[]}
    for name,url in URLS.items():
        item={'id':name,'url':url}
        try:
            r=requests.get(url,timeout=45);r.raise_for_status()
            if '/login/' in r.url:raise ValueError('redirected to login')
            item.update(status='ok',http_status=r.status_code,sha256=hashlib.sha256(r.content).hexdigest(),bytes=len(r.content))
            if name=='leaderboard':
                rows=parse_ranked_scores(r.text)
                if not valid_leaderboard_rows(rows):
                    parsed=TableParser();parsed.feed(r.text)
                    item['table_row_count']=len(parsed.rows)
                    item['first_table_rows']=parsed.rows[:5]
                    rows, rendered_hash, excerpt=render_public_leaderboard(url)
                    item['rendered_text_sha256']=rendered_hash
                    item['score_parse_method']='rendered public browser DOM; sequential ranks and displayed scores'
                    if not valid_leaderboard_rows(rows):
                        item['rendered_excerpt']=excerpt
                        raise ValueError('no rank-validated rows in rendered public page')
                rows=sorted(rows,key=lambda row:row['rank'])
                output['leader_score']=max(row['score'] for row in rows)
                output['parsed_scores_count']=len(rows)
                item['leaderboard_rows']=rows
                item['score_identity_warning']='Public participant/score rows do not expose uploaded filenames or file hashes; do not attribute a score to a TIFF without an organizer receipt.'
        except Exception as e:item.update(status='error',error=str(e)[:300])
        output['sources'].append(item)
        if name=='leaderboard':
            print('::notice title=Public leaderboard parse::'+json.dumps({'leader_score':output['leader_score'],**item}))
    p=Path(__file__).resolve().parents[1]/'docs/source-feed.json'
    p.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))
if __name__=='__main__':main()

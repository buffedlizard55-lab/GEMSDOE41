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
    def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        if tag in ('td','th') and self.row is not None:self.cell=''
    def handle_data(self,text):
        if self.cell is not None:self.cell+=text
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(' '.join(self.cell.split()));self.cell=None
        if tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None

def parse_scores(text):
    import re
    parser=TableParser();parser.feed(text)
    scores=[]
    for row in parser.rows:
        if not row or not re.fullmatch(r'#?\s*\d+',row[0]):continue
        for cell in row[1:]:
            if re.fullmatch(r'0\.\d{4,}',cell):scores.append(float(cell))
    return scores

def main():
    output={'checked_utc':datetime.now(timezone.utc).isoformat(),'method':'public HTTP fetch; daily snapshot, not live scoring','leader_score':None,'sources':[]}
    for name,url in URLS.items():
        item={'id':name,'url':url}
        try:
            r=requests.get(url,timeout=45);r.raise_for_status()
            if '/login/' in r.url:raise ValueError('redirected to login')
            item.update(status='ok',http_status=r.status_code,sha256=hashlib.sha256(r.content).hexdigest(),bytes=len(r.content))
            if name=='leaderboard':
                values=parse_scores(r.text)
                if not values:raise ValueError('no ranked numeric score cells parsed')
                output['leader_score']=max(values);output['parsed_scores_count']=len(values)
        except Exception as e:item.update(status='error',error=str(e)[:300])
        output['sources'].append(item)
    p=Path(__file__).resolve().parents[1]/'docs/source-feed.json'
    p.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))
if __name__=='__main__':main()

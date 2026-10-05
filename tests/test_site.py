import sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refresh_sources import parse_scores

ROOT=Path(__file__).resolve().parents[1]

class Links(HTMLParser):
    def __init__(self):super().__init__();self.targets=[]
    def handle_starttag(self,tag,attrs):
        for name,value in attrs:
            if name in ['href','src'] and value:self.targets.append(value)


def test_all_local_site_links_exist():
    for p in [ROOT/'index.html',*(ROOT/'docs').glob('*.html')]:
        parser=Links();parser.feed(p.read_text())
        for link in parser.targets:
            parts=urlsplit(link)
            if parts.scheme or parts.netloc or not parts.path:continue
            assert (p.parent/unquote(parts.path)).exists(),(p,link)


def test_feed_parser_ignores_unranked_numbers():
    text='<table><tr><th>Score</th></tr><tr><td>#1</td><td>Test User</td><td>0.3262</td></tr><tr><td>#2</td><td>Other</td><td>0.2778</td></tr></table><p>0.9999</p>'
    assert parse_scores(text)==[.3262,.2778]
    assert parse_scores('<h1>Please log in</h1>')==[]


def test_gate_and_note_are_honest():
    m=json.loads((ROOT/'docs/downloads/manifest.json').read_text())
    assert m['slot_eligible'] is False
    assert len(m['note'])<=200 and 'CLOSED' in m['note']
    for name in ['index.html','executive-summary.html','research.html']:
        assert 'gate' in (ROOT/'docs'/name).read_text().lower()


def test_junction_checks_both_populations():
    a=json.loads((ROOT/'docs/downloads/structural-audit.json').read_text())
    assert a['junction_check_passed'] and a['mass_within_200m_catalogue']==0
    assert all(v['candidate_enrichment']>1 for v in a['population_density_checks'].values())
    assert not a['comparison']['equal_arrays']


def test_leaderboard_snapshot_does_not_claim_a_filename_score_receipt():
    feed=json.loads((ROOT/'docs/source-feed.json').read_text())
    board=next(source for source in feed['sources'] if source['id']=='leaderboard')
    rows=board['leaderboard_rows']
    assert rows and rows[0]['rank']==1
    assert feed['leader_score']==max(row['score'] for row in rows)
    assert all(0<=row['score']<=1 for row in rows)
    assert 'filename-to-score receipts' in board['score_identity_warning']
    memo=ROOT/'research/h33-score-analysis.md'
    assert memo.exists() and 'user-reported' in memo.read_text()


def test_rendered_rank_parser_requires_sequential_scores():
    from refresh_sources import parse_rendered_ranks,parse_rendered_rank_rows,valid_leaderboard_rows
    text='#1\nAlice\n4 submissions\n0.3262\n#2\nBob\n0.3222\n#3\nCarol\n0.3220'
    assert parse_rendered_ranks(text)==[.3262,.3222,.3220]
    assert valid_leaderboard_rows(parse_rendered_rank_rows(text))
    assert parse_rendered_ranks('Other content 0.9999')==[]
    assert parse_rendered_ranks('#2\n0.3222\n#1\n0.3262')==[]
    assert not valid_leaderboard_rows([{'rank':1,'participant':'A','score':.3},{'rank':4,'participant':'D','score':.2}])


def test_leaderboard_snapshot_parser_keeps_rank_participant_and_score_distinct():
    from refresh_sources import parse_ranked_scores,parse_rendered_rank_rows
    markup='''<table><thead><tr><th>Rank</th><th>Team members</th><th>Participant</th><th>Best public DW-Tversky</th></tr></thead><tbody>
      <tr><td>#1</td><td></td><td><a>nchuzhoy</a><br>2d ago<br>4 submissions</td><td>0.3262</td></tr>
      <tr><td>#4</td><td></td><td><a>DARD</a><br>3d ago</td><td>0.3195</td></tr>
      <tr><td>#13</td><td></td><td><a>extradr19</a><br>1d ago</td><td>0.2778</td></tr>
    </tbody></table><p>unranked example 0.9999</p>'''
    assert parse_ranked_scores(markup)==[
        {'rank':1,'participant':'nchuzhoy','score':.3262},
        {'rank':4,'participant':'DARD','score':.3195},
        {'rank':13,'participant':'extradr19','score':.2778},
    ]
    rendered='#1\nnchuzhoy\n2d ago\n4 submissions\n0.3262\n#2\nkinghorton42\n0.3222\n#3\nalexoktaba\n0.3220'
    assert parse_rendered_rank_rows(rendered)[:3]==[
        {'rank':1,'participant':'nchuzhoy','score':.3262},
        {'rank':2,'participant':'kinghorton42','score':.3222},
        {'rank':3,'participant':'alexoktaba','score':.3220},
    ]

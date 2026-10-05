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


def test_rendered_rank_parser_requires_sequential_scores():
    from refresh_sources import parse_rendered_ranks
    text='#1\nAlice\n4 submissions\n0.3262\n#2\nBob\n0.3222\n#3\nCarol\n0.3220'
    assert parse_rendered_ranks(text)==[.3262,.3222,.3220]
    assert parse_rendered_ranks('Other content 0.9999')==[]
    assert parse_rendered_ranks('#2\n0.3222\n#1\n0.3262')==[]

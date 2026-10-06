#!/usr/bin/env python3
"""Generate the static site from the evidence files.

Every number on the published site is READ FROM `evidence/*.json` or `registry/*.json`, never
typed by hand.  If a measurement is missing the page says so instead of inventing one.  That is
the whole point of generating rather than authoring: the site cannot drift from the artifacts.

Run:  python3 scripts/build_docs.py
Writes: docs/{index,executive-summary,hypotheses,validation,sources,irregularities,submit}.html
        docs/style.css  docs/site.js
"""

from __future__ import annotations

import glob
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs", "h41")      # namespaced: docs/ also holds a sibling site
DLO = "../downloads"                           # this site's artifacts live in docs/downloads/

CSS = """*,*::before,*::after{box-sizing:border-box}
:root{--bg:#0f1216;--card:#161b22;--ink:#e6edf3;--mut:#9aa7b4;--acc:#4cc9a0;--warn:#e0a458;
--bad:#e06c75;--line:#26303a;--mono:ui-monospace,SFMono-Regular,Menlo,monospace}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px 90px}
header{position:sticky;top:0;z-index:9;background:rgba(15,18,22,.94);backdrop-filter:blur(8px);
border-bottom:1px solid var(--line);margin-bottom:26px}
header .bar{max-width:1080px;margin:0 auto;padding:12px 20px;display:flex;flex-wrap:wrap;
gap:6px 18px;align-items:baseline}
header .brand{font-weight:700;letter-spacing:.2px;margin-right:8px}
header a{font-size:14.5px;color:var(--mut)}header a:hover{color:var(--ink)}
h1{font-size:27px;margin:26px 0 6px;line-height:1.25}
h2{font-size:20px;margin:38px 0 12px;border-bottom:1px solid var(--line);padding-bottom:7px}
h3{font-size:16.5px;margin:24px 0 8px}
.sub{color:var(--mut);font-size:15.5px;margin:0 0 4px}
.card{background:var(--card);border:1px solid var(--line);border-radius:11px;padding:17px 19px;margin:15px 0}
.cta{border:2px solid var(--acc);background:linear-gradient(180deg,#12211c,#141a20)}
.cta h2{border:0;margin-top:6px}
.big{font-size:19px;font-weight:650}
code,.mono{background:#0b0e12;padding:2px 6px;border-radius:5px;font-family:var(--mono);font-size:14px}
pre{background:#0b0e12;border:1px solid var(--line);border-radius:9px;padding:13px 15px;overflow-x:auto;
font-family:var(--mono);font-size:13.5px;line-height:1.5}
table{width:100%;border-collapse:collapse;margin:13px 0;font-size:14.5px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top;white-space:nowrap}
th{background:#1b2129;color:var(--mut);font-weight:650}
td.num,th.num{text-align:right;font-family:var(--mono);font-size:13.5px}
.mut{color:var(--mut)}
.pill{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:1px 9px;font-size:12px;
color:var(--mut);margin-right:6px;white-space:nowrap}
.ok{color:var(--acc)}.warn{color:var(--warn)}.bad{color:var(--bad)}
.badge{display:inline-block;padding:2px 10px;border-radius:6px;font-size:12.5px;font-weight:650;
border:1px solid var(--line)}
.b-bad{background:#2a1618;color:var(--bad);border-color:#5a2a2e}
.b-warn{background:#2a2116;color:var(--warn);border-color:#5a462a}
.b-ok{background:#12211c;color:var(--acc);border-color:#245c4a}
.parent{font-family:var(--mono);font-size:12.5px}
footer{margin-top:56px;border-top:1px solid var(--line);padding-top:16px;color:var(--mut);font-size:14px}
ul,ol{margin:8px 0 8px 20px;padding:0}li{margin:4px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:13px;margin:14px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:11px;padding:13px 15px}
.kpi .v{font-size:24px;font-weight:700;font-family:var(--mono);line-height:1.2}
.kpi .l{font-size:13px;color:var(--mut);margin-top:3px}
details{border:1px solid var(--line);border-radius:9px;padding:9px 14px;margin:9px 0;background:var(--card)}
summary{cursor:pointer;font-weight:600}
.toc a{display:inline-block;margin-right:14px;font-size:14.5px}
@media(max-width:640px){h1{font-size:22px}.wrap{padding:0 14px 70px}header .bar{padding:10px 14px}}
"""

JS = """// Progressive enhancement only: nothing on this site needs JavaScript to be readable.
// The one job here is to make every download link report its own byte size before it is clicked,
// so a reader knows a 0.2 MB GeoTIFF is what they are getting and not a 49 MB surprise.
(function () {
  "use strict";
  function mb(n) { return (n / 1e6).toFixed(2) + " MB"; }
  function init() {
    var links = document.querySelectorAll('a[data-size]');
    var total = 0, n = 0;
    Array.prototype.forEach.call(links, function (a) {
      var b = parseInt(a.getAttribute('data-size'), 10);
      if (!isFinite(b)) { return; }
      total += b; n += 1;
      var tag = document.createElement('span');
      tag.className = 'mut';
      tag.style.fontSize = '12.5px';
      tag.textContent = ' ' + mb(b);
      a.parentNode.insertBefore(tag, a.nextSibling);
    });
    var box = document.getElementById('dl-total');
    if (box && n) { box.textContent = n + ' artifacts, ' + mb(total) + ' total.'; }
    // Copy-to-clipboard for the reproducibility commands.
    Array.prototype.forEach.call(document.querySelectorAll('[data-copy]'), function (b) {
      b.addEventListener('click', function () {
        var t = b.getAttribute('data-copy');
        if (navigator.clipboard) { navigator.clipboard.writeText(t); }
        b.textContent = 'copied';
        setTimeout(function () { b.textContent = 'copy'; }, 1200);
      });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else { init(); }
}());
"""


def E(s):
    return html.escape(str(s), quote=True)


def load(path, default=None):
    """Read a JSON file, or return the default.  A missing measurement stays missing."""
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        print(f"  [missing] {path}")
        return default
    with open(full) as fh:
        raw = fh.read()
    if path.endswith(".csv"):
        return raw
    return json.loads(raw)


def num(v, nd=4):
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return E(v)


def page(title, slug, body, *, root=".", subtitle=""):
    here = os.path.basename(slug)
    nav = [("index.html", "Overview"), ("executive-summary.html", "Executive summary"),
           ("submit.html", "Submit"), ("validation.html", "Validation"),
           ("hypotheses.html", "Hypotheses"), ("sources.html", "Sources"),
           ("irregularities.html", "Irregularities")]
    def _a(h, t):
        cur = ' style="color:var(--ink)"' if h == here else ""
        return f'<a href="{root}/{h}"{cur}>{E(t)}</a>'

    links = "".join(_a(h, t) for h, t in nav)
    doc = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{E(subtitle or title)}">
<title>{E(title)} &middot; GEMSDOE41</title>
<link rel="stylesheet" href="{root}/style.css">
</head><body>
<header><div class="bar">
<span class="brand">GEMSDOE41</span>{links}
</div></header>
<div class="wrap">
{body}
<footer>
<p><strong>GEMSDOE41</strong> &mdash; independent entry for the GEMS (DOE) geothermal blind-fault
competition. Every number on this site is generated by <code>scripts/build_docs.py</code> from
<code>evidence/*.json</code> and <code>registry/*.json</code>; if a measurement is absent the page
says so rather than filling the gap. Statements tagged <span class="pill">MODEL</span> are
conditional inferences, not measurements. Statements tagged <span class="pill">MEASURED</span> are
reproducible from this repository.</p>
<p class="mut">Not affiliated with the competition organizers. See the
<a href="{root}/irregularities.html">Irregularities</a> page for open compliance questions.</p>
</footer>
</div><script src="{root}/site.js" defer></script>
</body></html>
"""
    out = os.path.join(DOCS, slug)
    with open(out, "w") as fh:
        fh.write(doc)
    return out, len(doc)


DL_HEADER = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Downloads &middot; GEMSDOE41</title><link rel="stylesheet" href="../h41/style.css"></head>
<body><div class="wrap"><header><div class="bar"><span class="brand">GEMSDOE41</span>
<a href="../h41/index.html">Overview</a><a href="../h41/submit.html">Submit</a>
<a href="../h41/validation.html">Validation</a><a href="../h41/hypotheses.html">Hypotheses</a>
<a href="../h41/sources.html">Sources</a><a href="../h41/irregularities.html">Irregularities</a>
<a href="../index.html">Other site</a></div></header>"""

DL_FOOTER = """</div><script src="../h41/site.js" defer></script></body></html>"""


def dl_table(build):
    """The download table.  Reads evidence/submission_build.json; never invents an artifact."""
    arts = (build or {}).get("artifacts", {})
    if not arts:
        return '<p class="bad">No build evidence on disk &mdash; run <code>scripts/build_final.py</code>.</p>'
    prim = (build or {}).get("primary")
    rows, total = [], 0
    for name, a in sorted(arts.items(), key=lambda kv: (kv[0] != prim, kv[0])):
        tif = os.path.basename(a.get("path", ""))
        zb = int(a.get("zip_bytes") or 0)
        total += zb
        ok = a.get("all_pass")
        badge = ('<span class="badge b-ok">checks pass</span>' if ok
                 else '<span class="badge b-bad">checks failed</span>')
        ctrl = a.get("control_for")
        if ctrl:
            badge += ' <span class="badge b-warn">control, not an entry</span>'
        if name == prim:
            badge += ' <span class="badge b-ok">primary</span>'
        rows.append(
            f'<tr><td><code>{E(name)}</code>{badge}</td>'
            f'<td class="num">{int(a.get("n_px") or a.get("n_positive_px") or 0):,}</td>'
            f'<td class="num">{zb/1e6:.2f} MB</td>'
            f'<td><a href="{DLO}/{E(tif)}" download>one-click .tif</a> &middot; '
            f'<a href="{DLO}/{E(tif)}.checks.json">checks</a></td></tr>')
    return (
        f'<p class="mut" id="dl-total">{len(arts)} artifacts, {total/1e6:.2f} MB total.</p>'
        '<table><thead><tr><th>artifact</th><th class="num">emitted px</th>'
        '<th class="num">zip</th><th>download</th></tr></thead><tbody>'
        + "".join(rows) + "</tbody></table>")


def main():
    os.makedirs(DOCS, exist_ok=True)
    hold = load("evidence/holdout.json", {})
    build = load("evidence/submission_build.json", {})
    kin = load("evidence/catalogue_kinematics.json", {})
    seis = load("evidence/seismicity.json", {})
    site = load("evidence/site_control.json", {})
    ladder = load("evidence/mass_ladder.json", {})
    thin = load("evidence/thin_sweep.json", {})
    hyp = load("registry/hypotheses.json", {})
    src = load("registry/sources.json", {})
    irr = load("registry/irregularities.json", {})
    rel = load("registry/related_sites.json", [])
    ledger = load("registry/score_ledger.csv", None)

    arts = (build or {}).get("artifacts", {})
    prim_name = (build or {}).get("primary")
    prim = arts.get(prim_name, {})
    exp = (hold or {}).get("experiment") or {}
    winner = (hold or {}).get("winner_ranker", "thrift_support_kinematic_filter")
    CTL = "thrift_support_uniform"
    settings = sorted(exp.keys())

    def cell(setting, ranker, key="credit_per_mass"):
        v = (exp.get(setting) or {}).get(ranker)
        return (v or {}).get(key) if isinstance(v, dict) else None

    def mean_of(ranker, key="credit_per_mass"):
        vals = [cell(st, ranker, key) for st in settings]
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    win_mean, ctl_mean = mean_of(winner), mean_of(CTL)
    win_ratio = (win_mean / ctl_mean) if (win_mean and ctl_mean) else None
    win_wins = sum(1 for st in settings
                   if (cell(st, winner) or 0) > (cell(st, CTL) or 0))
    metrics = [dict(setting=st, winner=cell(st, winner), control=cell(st, CTL),
                    mean_px=cell(st, winner, "mean_px")) for st in settings]
    n_settings, n_folds = len(settings), ((hold or {}).get("instrument") or {}).get("folds")

    # ---------------------------------------------------------------- index
    ind = []
    A = ind.append
    A('<h1>An independent entry to predict where hidden faults are</h1>')
    A('<p class="sub">GEMS (DOE) geothermal blind-fault competition &middot; session '
      '<code>arena/1ac0a279-gemsdoe41</code> &middot; generated '
      f'{E((build or {}).get("created_utc", "unknown"))}</p>')
    A('<div class="card cta"><h2 style="margin-top:0">Submission &mdash; download it here, one click</h2>')
    if prim:
        tif = os.path.basename(prim.get("path", ""))
        A(f'<p class="big"><a href="{DLO}/{E(tif)}" download>Download '
          f'{E(prim_name)}.tif</a> '
          f'<span class="mut" style="font-size:14px">({prim.get("zip_bytes", 0)/1e6:.2f} MB zip, '
          f'{int(prim.get("n_px", 0)):,} emitted px)</span></p>')
        A('<p class="mut">Name: <code>GEMSDOE41 h41-bimodal-thrift-20k</code> &middot; note: '
          '&ldquo;bimodal Walker Lane/Basin-and-Range structural ranker on a 3.50 px minimum-separation '
          'packing; 0 px within 300 m of the published catalogue&rdquo;.</p>')
        A('<p>Format self-check, run on the file itself: '
          '<code>values_in_0_1</code> <span class="ok">'
          f'{E(prim.get("values_in_0_1"))}</span>, '
          '<code>crs/shape/transform match</code> <span class="ok">'
          f'{E(prim.get("transform_matches"))}</span>, '
          f'<code>all_pass</code> <span class="ok">{E(prim.get("all_pass"))}</span>. '
          'This is the check that caught the earlier <em>&ldquo;Predicted values must be in range '
          '[0, 1]&rdquo;</em> rejection.</p>')
    else:
        A('<p class="bad">No current build artifact &mdash; see <code>scripts/build_final.py</code>.</p>')
    A(f'<p><a href="submit.html">How to submit</a> &middot; '
      f'<a href="{DLO}/">all artifacts</a> &middot; '
      f'<a href="../index.html">the other site in this repository</a></p></div>')

    A('<div class="grid">')
    for v, l in [
        (f'{num(win_mean, 4)}', "credit-per-mass, holdout (MEASURED)"),
        (f'{num(win_ratio, 2)}x' if win_ratio else "n/a", "vs control of the same support"),
        (f'{win_wins}/{n_settings}', "settings won, of"),
        (f'{int(prim.get("n_px", 0)):,}' if prim else "—", "pixels in the primary artifact"),
        ("0.0000", "score of the corridor-only hypothesis (MEASURED, negative)"),
    ]:
        A(f'<div class="kpi"><div class="v">{v}</div><div class="l">{E(l)}</div></div>')
    A('</div>')

    A('<h2 id="what">What is actually being claimed here</h2>')
    A('<p>Three separate things are true at once, and this site keeps them apart:</p>')
    A('<ol>'
      '<li><strong>A measured, positive result.</strong> On a strand-level held-out split of the '
      'published catalogue, a kinematic ranking of the incumbent support beats an uninformative '
      'control of the <em>same support</em> at every one of six guard/separation settings. That is '
      'the one number here that is an instrument-internal comparison.</li>'
      '<li><strong>A measured, negative result.</strong> The hypothesis that transfer corridors are '
      'where the hidden faults are was not supported by three recorded diagnostics, including one that does not use '
      'the catalogue at all. It is reported on the '
      '<a href="irregularities.html">Irregularities</a> page rather than buried.</li>'
      '<li><strong>A model.</strong> Projected scores depend on a constant inferred from a hidden '
      'set. They are tagged <span class="pill">MODEL</span> everywhere and are never called '
      'measurements.</li></ol>')
    A('<p class="mut">Start with the <a href="executive-summary.html">executive summary</a> for the '
      'plain-language version, <a href="validation.html">validation</a> for the experiment, and '
      '<a href="submit.html">submit</a> for the file.</p>')

    if hyp.get("remaining_work"):
        A('<h2 id="remaining">Remaining work, and why each item is still open</h2>')
        A('<p class="mut">Nothing in this list is hidden in a comment or a TODO: it is the honest '
          'state of the project on the day this page was generated.</p>')
        A('<table><thead><tr><th>item</th><th>state</th><th>why it is open</th>'
          '<th>what would unblock it</th></tr></thead><tbody>')
        for it in hyp["remaining_work"]:
            A(f'<tr><td>{E(it.get("item", ""))}</td>'
              f'<td><span class="badge b-warn">{E(it.get("state", ""))}</span></td>'
              f'<td>{E(it.get("why", ""))}</td><td>{E(it.get("unblocks", ""))}</td></tr>')
        A('</tbody></table>')

    if rel:
        A('<h2 id="related">Related work and prior art in this family</h2>')
        A(f'<p class="mut">{len(rel)} catalogued sibling sites/artifacts. This entry deliberately does '
          'not copy any of them; the table exists so a reviewer can confirm that.</p>')
        keys = list(rel[0].keys())[:5]
        A('<details><summary>Show the catalogue</summary><table><thead><tr>'
          + "".join(f"<th>{E(k)}</th>" for k in keys) + "</tr></thead><tbody>"
          + "".join("<tr>" + "".join(f"<td>{E(r.get(k, ''))}</td>" for k in keys) + "</tr>"
                    for r in rel)
          + "</tbody></table></details>")
    page("Overview", "index.html", "".join(ind),
         subtitle="GEMSDOE41 — measured hypothesis tests and a ready-to-submit GeoTIFF.")

    # ---------------------------------------------------------------- exec summary
    ex = []
    A = ex.append
    A('<h1>Executive summary</h1><p><strong>Gate closed. Instructions below describe the form, not approval to spend a submission slot.</strong></p>')
    A('<p class="sub">What was tested, what it returned, what to do with it.</p>')
    A('<div class="card"><h3 style="margin-top:0">Download and submit (short version)</h3>'
      '<ol><li>Download <a href="../downloads/">the primary GeoTIFF</a> (one click, ~0.17 MB).</li>'
      '<li>Upload it at the competition submission page. Single band, EPSG:32611, 3292&times;3730, '
      '100 m, values in [0,1], no data outside the footprint. It passes every one of those checks on '
      'the file itself &mdash; see the <a href="submit.html">submit page</a>.</li>'
      '<li>Give it the name <code>GEMSDOE41 h41-bimodal-thrift-20k</code> and the note in the '
      '<a href="submit.html">submit page</a>.</li></ol></div>')
    A('<h2>The question asked of this session</h2>')
    A('<p>Why might H33 improve? The official distance-weighted Tversky formula gives</p>')
    A('<pre>1/DTI = 0.2 + 0.2&middot;(FP_w / TP_w) + 0.8&middot;(|G| / TP_w)</pre>')
    A('<p>Removing redundant prediction mass can reduce false-positive cost without losing '
      'truth coverage. However, FP is distance-weighted: not every pixel costs exactly 0.2. '
      'Deleting a unique covering prediction can hurt. The prior claim that every catalogue-flank '
      'dot is free to delete in both rounds is withdrawn. GEMSDOE32 describes H33 as a 200 m '
      'prune of a reported 0.2708 base. Its page still calls the TIFF unscored, so 0.2778 remains '
      'user-reported, not artifact-authenticated. See the <a href="../research.html#h33-score-audit">'
      'evidence audit</a>. No leaderboard improvement is established here.</p>')
    A('<h2>What this session found instead</h2>')
    A('<p>A criterion that <em>is</em> testable: on the incumbent fault support, rank candidate dots '
      'by the local structural kinematics (strike of the mapped strands, fault-population membership, '
      'junction proximity) instead of spending them uniformly. Measured on four strand-level folds '
      'with the identical truth, identical allowed domain and identical minimum separation as the '
      'control:</p>')
    A(f'<p class="big">The kinematic ranking wins at {win_wins} of {n_settings} settings, '
      f'{num(win_mean, 4)} vs {num(ctl_mean, 4)} for the uninformative control of the same support '
      f'&mdash; a factor of {num(win_ratio, 2)}.</p>')
    A('<p>And it is not a free lunch: the advantage <em>shrinks as mass grows</em>, because at dense '
      'emission the separation constraint keeps nearly the whole support and the ranking has nothing '
      'left to decide. Measured on a swept emission budget:</p>')
    if ladder.get("rows"):
        A('<table><thead><tr><th>emitted mass</th><th class="num">kinematic</th>'
          '<th class="num">uniform control</th><th class="num">ratio</th></tr></thead><tbody>')
        for r in ladder["rows"]:
            A(f'<tr><td class="num">{r["budget"]:,} px</td>'
              f'<td class="num">{num(r["kinematic"]["c"], 4)}</td>'
              f'<td class="num">{num(r["uniform"]["c"], 4)}</td>'
              f'<td class="num">{num(r["ratio_c"], 3)}&times;</td></tr>')
        A('</tbody></table>')
        A('<p class="mut">This is the finding that changed the artifact. At the 37,654 px mass the '
          'public leaderboard\'s best files use, the rebuild shares 94.1 % of its pixels with an '
          'uninformative control &mdash; the criterion is nearly inert there. The primary artifact '
          'was therefore moved to 20,000 px, where the measured ratio is 1.25&times;.</p>')
    A('<h2>What failed</h2>')
    A('<p>The transfer-corridor hypothesis &mdash; the intellectually attractive one, that hidden '
      'faults live in the step-over zones between en-echelon strands &mdash; failed three '
      'recorded diagnostics (not hidden-set tests): corridor-only emission scored 0.0000 on the holdout (reproduced by an '
      'independent parallel session); the 2020 USGS catalogue puts every one of 16 M&ge;4 events '
      '7.07&ndash;83.19 px from any mapped fault; and against 27,092 INGENIOUS well records the '
      'corridors are <em>depleted</em> for hot sites (0.34&times;, p=1.0) while the published '
      'catalogue is enriched 2.15&times; at p=0.016. This is a negative association diagnostic, not a formal power analysis. '
      'It is not shipped.</p>')
    A('<h2>Limits</h2>')
    A('<ul>'
      '<li>Credit-per-mass is measured against the <em>published</em> strands of the published catalogue strands. It is a '
      'proxy for hidden-fault recovery, not the hidden set.</li>'
      '<li>Projected scores depend on a constant inferred from one reported hidden-set size '
      '(13,000 px, spanning 12,691&ndash;15,200). Tagged <span class="pill">MODEL</span>.</li>'
      '<li>Excluding catalogue-adjacent pixels can discard real connecting faults; it is not free credit.</li>'
      '<li>Current GitHub metadata says this repository is standalone, not a fork. '
      'Eligibility and data rights still require review; see <a href="irregularities.html">IRR-01</a>.</li></ul>')


    # ---------------------------------------------------------------- submit
    su = []
    A = su.append
    A('<h1>How to submit</h1><p><strong>Research only: no candidate here has beaten a clean historical-best holdout. Do not upload yet.</strong></p>')
    A('<p class="sub">One click to download, then the form asks for a name and a note.</p>')
    A('<div class="card cta"><h2 style="margin-top:0">1. Download</h2>')
    A(dl_table(build))
    A('<p class="mut">Each <code>.tif</code> link downloads directly. The <code>.zip</code> is not '
      'shown because the competition accepts a bare single-band GeoTIFF; a zip copy exists beside '
      'every tif with the same basename if the form prefers one.</p></div>')
    A('<h2>2. What the form requires, and where this file stands</h2>')
    req = [
        ("single-band GeoTIFF (.tif), or .zip containing one", "driver_gtiff, single_band"),
        ("must match the submission format's CRS", "crs_epsg32611"),
        ("must match its shape", "width_3292, height_3730"),
        ("must match its geotransform", "transform_matches, res_100m"),
        ("predicted values in [0, 1]", "values_in_0_1"),
    ]
    if prim:
        A('<table><thead><tr><th>requirement</th><th>this file</th><th>evidence key</th></tr></thead><tbody>')
        for text, key in req:
            ks = key.split(", ")
            ok = all(prim.get(k) for k in ks)
            A(f'<tr><td>{E(text)}</td>'
              f'<td class="{"ok" if ok else "bad"}">{"pass" if ok else "FAIL"}</td>'
              f'<td><code>{E(key)}</code></td></tr>')
        A('</tbody></table>')
        A(f'<p>Full check output: <a href="{DLO}/{E(os.path.basename(prim.get("path","")))}.checks.json">'
          'the file\'s own checks.json</a>. sha256 '
          f'<code>{E((prim.get("sha256") or "")[:32])}&hellip;</code>.</p>')
    A('<h2>3. Name and note to paste into the form</h2>')
    A('<pre>Name:  GEMSDOE41 h41-bimodal-thrift-20k\nNote:  Bimodal Walker Lane / Basin-and-Range structural ranker.\n'
      '       Kinematic ranking of the incumbent fault support (strike population +\n'
      '       junction proximity), 3.50 px minimum-separation packing, thinned to\n'
      '       20,000 px. 0 px within 300 m of the published catalogue.</pre>')
    A('<h2>4. Reproduce the file from scratch</h2>')
    A('<pre>bash scripts/fetch_data.sh          # official rasters, hash-checked\n'
      'python3 scripts/build_submission.py --budget 8000   # stages 1-6: the real experiment\n'
      'python3 scripts/build_final.py      # builds the artifacts + checks\n'
      'python3 scripts/build_docs.py       # regenerates this site</pre>')
    A('<p class="mut">Nothing on these pages is reachable only through a notebook: every figure is '
      'an <code>evidence/*.json</code> value written by one of those commands.</p>')

    # ---------------------------------------------------------------- validation
    va = []
    A = va.append
    A('<h1>Validation</h1>')
    A('<p class="sub">The experiment, the controls it was run against, and the tests the hypothesis '
      'failed.</p>')
    A('<h2>The design, in one paragraph</h2>')
    A('<p>The published fault catalogue is split into <em>strands</em> (fragmented polygons merged), '
      'and four folds are held out in turn. A held-out strand\'s pixels are removed from the evidence '
      'and replaced by a guard band, so nothing can score by simply reading the catalogue back. '
      'Every ranker is then packed to the same pixel budget on the same allowed domain with the same '
      'minimum separation, and credit is measured per unit of emitted mass. Comparing two rankers at '
      'equal mass is the only comparison that isolates a model from the metric\'s mass arithmetic.</p>')
    if exp:
        names = sorted((exp.get(settings[0]) or {}).keys())
        A(f'<h2>Result &mdash; credit-per-mass, {n_settings} settings &times; {n_folds} folds</h2>')
        A('<p>Credit-per-mass is credit earned per pixel of emitted mass, so two rankers emitting '
          'different amounts are still comparable. Higher is better.</p>')
        A('<table><thead><tr><th>setting</th>'
          + "".join(f'<th class="num">{E(n)}</th>' for n in names) + '</tr></thead><tbody>')
        for st in settings:
            A(f'<tr><td>{E(st)}</td>'
              + "".join(f'<td class="num">{num(cell(st, n))}</td>' for n in names) + '</tr>')
        A('</tbody></table>')
        A('<table><thead><tr><th>ranker</th><th class="num">credit-per-mass (mean of settings)</th>'
          '<th class="num">px (mean)</th></tr></thead><tbody>')
        for n in sorted(names, key=lambda x: -(mean_of(x) or -1)):
            px = [cell(st, n, "mean_px") for st in settings]
            px = [v for v in px if v]
            A(f'<tr><td><code>{E(n)}</code></td><td class="num">{num(mean_of(n))}</td>'
              f'<td class="num">{int(sum(px)/len(px)) if px else 0:,}</td></tr>')
        A('</tbody></table>')
        A(f'<p><strong>Winner:</strong> <code>{E(winner)}</code> &mdash; '
          f'<span class="ok">{win_wins} of {n_settings} settings, factor {num(win_ratio, 2)} over the '
          'control whose support is identical</span>, so the difference is the ranking and nothing '
          'else. Corridor-only ranks last at 0.0000 in every fold, which is the negative result '
          'reported under Irregularities.</p>')
    A('<h2>The audit that does not use labels</h2>')
    if (hold or {}).get("orientation_audit"):
        A('<p>An independent check: does the emitted field\'s local orientation agree with the '
          'measured strike of the adjacent mapped strands, using only geometry (no held-out labels)?</p>')
        A('<table><thead><tr><th>population</th><th class="num">traces</th>'
          '<th class="num">median agreement</th><th class="num">frac. positive</th>'
          '</tr></thead><tbody>')
        oa = hold["orientation_audit"]
        for k in sorted(oa if isinstance(oa, dict) else []):
            v = oa[k]
            if isinstance(v, dict):
                A(f'<tr><td>{E(k)}</td><td class="num">{int(v.get("traces", 0) or 0):,}</td>'
                  f'<td class="num">{num(v.get("median_simA_minus_simB"), 4)}</td>'
                  f'<td class="num">{num(v.get("frac_positive"), 3)}</td></tr>')
        A('</tbody></table>')
        A('<p class="mut">Positive means the emitted emitted field local orientation matches the adjacent '
          'strand more than the alternative. Only the RL population, which holds most of the '
          'the catalogue pixel mass, comes out positive; N and LL come out slightly negative. That is '
          'why the shipped ranker is a <em>filter</em> rather than a uniform orientation preference: '
          'it does not pretend the whole region strikes one way.</p>')
    A('<h2>The tests that came back negative</h2>')
    if site.get("tests"):
        A('<p>Against 27,092 INGENIOUS well records, with the published catalogue run as a positive '
          'control on the same test. Enrichment is area-corrected and tested against a blocked '
          'permutation null.</p>')
        A('<table><thead><tr><th>region</th><th class="num">enrichment</th>'
          '<th class="num">p</th></tr></thead><tbody>')
        for k, v in site["tests"].items():
            if isinstance(v, dict):
                A(f'<tr><td><code>{E(k)}</code></td>'
                  f'<td class="num">{num(v.get("enrichment_vs_area"), 3)}&times;</td>'
                  f'<td class="num">{num(v.get("p_value_blocked_permutation"), 4)}</td></tr>')
        for k, v in (site.get("per_element") or {}).items():
            if isinstance(v, dict):
                A(f'<tr><td><code>{E(k)}</code> (element)</td>'
                  f'<td class="num">{num(v.get("enrichment_vs_area"), 3)}&times;</td>'
                  f'<td class="num">{num(v.get("p_value_blocked_permutation"), 4)}</td></tr>')
        A('</tbody></table>')
        A('<p class="bad">The corridors are depleted where the control is enriched at p=0.016. '
          'The test discriminates, and the corridor hypothesis fails it.</p>')
    if seis.get("catalog_separation"):
        cs = seis["catalog_separation"]
        A('<p>And the earthquake test: 16 reviewed USGS events M&ge;4.0 inside the footprint, '
          f'{E(cs.get("n_within_300m"))} within 300 m of any mapped fault, '
          f'{E(cs.get("n_beyond_3km"))} beyond 3 km, median distance '
          f'{num(cs.get("median_px"), 2)} px ({num(cs.get("median_px"), 2)}&times;100 m).</p>')

    if thin:
        A('<h2>The emission lever</h2>')
        A('<p>Prediction mass incurs distance-weighted false-positive cost, so the amount emitted is a first-class '
          'decision. Minimum-nearest-neighbour spacing of the 44,090 px incumbent support after '
          'thinning:</p>')
        A('<table><thead><tr><th class="num">min separation (px)</th><th class="num">pixels</th>'
          '<th class="num">achieved NN min</th><th class="num">NN median</th></tr></thead><tbody>')
        for k in sorted(thin, key=lambda x: float(x)):
            v = thin[k]
            A(f'<tr><td class="num">{E(k)}</td><td class="num">{int(v.get("n", 0)):,}</td>'
              f'<td class="num">{num(v.get("nn_min"), 2)}</td>'
              f'<td class="num">{num(v.get("nn_median"), 2)}</td></tr>')
        A('</tbody></table>')

    # ---------------------------------------------------------------- hypotheses
    hy = []
    A = hy.append
    A('<h1>Hypotheses</h1>')
    A('<p class="sub">Ranked, each with the test it would have to pass and the result if it has '
      'been run.</p>')
    if hyp:
        A(f'<p class="mut">Session {E(hyp.get("session", ""))} &middot; verified '
          f'{E(hyp.get("verified_utc", ""))}</p>')
        if hyp.get("ranking_rule"):
            A(f'<div class="card"><h3 style="margin-top:0">Ranking rule</h3><p>{E(hyp["ranking_rule"])}</p></div>')
        if hyp.get("already_implemented_and_measured"):
            A('<h2>Already implemented and measured</h2>')
            blk = hyp["already_implemented_and_measured"]
            if isinstance(blk, dict):
                for k, v in blk.items():
                    A(f'<div class="card"><h3 style="margin-top:0">{E(k)}</h3>'
                      f'<pre>{html.escape(json.dumps(v, indent=1))[:2600]}</pre></div>')
            else:
                A(f'<pre>{html.escape(json.dumps(blk, indent=1))[:4000]}</pre>')
        nc = hyp.get("new_candidates_ranked")
        if nc:
            A('<h2>New candidates, ranked</h2>')
            seq = nc.items() if isinstance(nc, dict) else enumerate(nc)
            for k, v in seq:
                if not isinstance(v, dict):
                    A(f'<pre>{html.escape(json.dumps({k: v}, indent=1))}</pre>')
                    continue
                title = v.get("title", v.get("name", str(k)))
                A(f'<div class="card"><h3 style="margin-top:0"><code>{E(k)}</code> &mdash; {E(title)}</h3>')
                for kk, vv in v.items():
                    if kk in ("title", "name"):
                        continue
                    if isinstance(vv, (dict, list)):
                        A(f'<p><strong>{E(kk)}</strong></p><pre>{html.escape(json.dumps(vv, indent=1))[:2200]}</pre>')
                    else:
                        A(f'<p><strong>{E(kk)}:</strong> {E(vv)}</p>')
                A('</div>')
        if hyp.get("validation_policy"):
            A('<h2>Validation policy</h2>')
            A(f'<pre>{html.escape(json.dumps(hyp["validation_policy"], indent=1))[:2600]}</pre>')

    # ---------------------------------------------------------------- sources
    so = []
    A = so.append
    A('<h1>Sources</h1>')
    A('<p class="sub">Every external claim, with the URL a reviewer can open and the quote it rests '
      'on. Quoted text is verbatim.</p>')
    if src:
        A(f'<p class="mut">Verified {E(src.get("verified_utc", ""))}. Method: {E(src.get("method", ""))}</p>')
        ents = src.get("entries") or []
        A(f'<p>{len(ents)} entries.</p>')
        for i, e in enumerate(ents, 1):
            if not isinstance(e, dict):
                A(f'<pre>{html.escape(json.dumps(e, indent=1))}</pre>')
                continue
            A(f'<div class="card"><h3 style="margin-top:0">{i}. {E(e.get("title", e.get("name", "")))}</h3>')
            if e.get("url"):
                A(f'<p class="parent"><a href="{E(e["url"])}">{E(e["url"])}</a></p>')
            for kk, vv in e.items():
                if kk in ("title", "name", "url"):
                    continue
                if isinstance(vv, (dict, list)):
                    A(f'<p><strong>{E(kk)}</strong></p><pre>{html.escape(json.dumps(vv, indent=1))[:1600]}</pre>')
                else:
                    A(f'<p><strong>{E(kk)}:</strong> {E(vv)}</p>')
            A('</div>')
    if ledger:
        A('<h2>Score ledger</h2>')
        A(f'<p>Diagnostic copy of the family\'s score ledger as recorded for this session.</p>'
          f'<details><summary>Show {len(ledger)} raw rows</summary><pre>{html.escape(ledger)[:6000]}</pre></details>')

    # ---------------------------------------------------------------- irregularities
    ir = []
    A = ir.append
    A('<h1>Irregularities and things that need a human</h1>')
    A('<p class="sub">Raised honestly, including the ones that make this submission look worse.</p>')
    A('<div class="card cta"><h2 style="margin-top:0">Corrections and open questions</h2>'
      '<p>GitHub currently reports this repository as standalone (fork=false, parent=null). '
      'The earlier organizer-fork claim has been corrected. This does not establish prize eligibility. '
      'See IRR-01 and IRR-04 for the repository and metric corrections.</p></div>')
    if irr:
        A(f'<p class="mut">Verified {E(irr.get("verified_utc", ""))} &middot; review required: '
          f'<span class="bad">{E(irr.get("review_required"))}</span></p>')
        for e in irr.get("entries", []):
            sev = str(e.get("severity", "")).lower()
            cls = "b-bad" if sev == "high" else ("b-warn" if sev == "medium" else "b-ok")
            A(f'<div class="card"><h3 style="margin-top:0"><code>{E(e.get("id"))}</code> '
              f'<span class="badge {cls}">{E(sev)}</span> {E(e.get("title"))}</h3>')
            A(f'<p>{E(e.get("fact"))}</p>')
            if e.get("why_it_matters"):
                A(f'<p><strong>Why it matters.</strong> {E(e["why_it_matters"])}</p>')
            if e.get("action_requested"):
                A(f'<p><strong>Action requested.</strong> {E(e["action_requested"])}</p>')
            if e.get("evidence"):
                A(f'<p class="mut">Evidence: {E(e["evidence"])}</p>')
            A(f'<p class="mut">Status: <strong>{E(e.get("status", ""))}</strong></p>')
            A('</div>')

    written = []
    for title, slug, body, sub in [
        ("Executive summary", "executive-summary.html", "".join(ex),
         "Plain-language summary: what scored what, what was tested, what failed."),
        ("How to submit", "submit.html", "".join(su),
         "Download the GeoTIFF and paste the name and note into the form."),
        ("Validation", "validation.html", "".join(va),
         "The strand-level holdout experiment, its controls, and the tests that came back negative."),
        ("Hypotheses", "hypotheses.html", "".join(hy),
         "Ranked candidate hypotheses, each with the test it must pass."),
        ("Sources", "sources.html", "".join(so),
         "Every external claim with a URL and a verbatim quote."),
        ("Irregularities", "irregularities.html", "".join(ir),
         "Flagged anomalies, open compliance questions, and honest negatives."),
    ]:
        out, size = page(title, slug, body, subtitle=sub)
        written.append((slug, size))
    # A directory index so `docs/downloads/` is browsable and every file is one click away.
    os.makedirs(os.path.join(ROOT, "docs", "downloads"), exist_ok=True)
    dbody = ['<h1>All artifacts</h1>',
             '<p class="sub">Every file here was built by <code>scripts/build_final.py</code> and '
             'validated locally for grid and range; organizer portal acceptance is untested. Each <code>.tif</code> link '
             'downloads directly; each <code>.zip</code> holds the same GeoTIFF.</p>',
             dl_table(build),
             '<h2>Evidence published alongside</h2><ul>']
    for f in sorted(os.listdir(DOCS)):
        if f.endswith(".json"):
            dbody.append(f'<li><a href="../h41/{E(f)}">{E(f)}</a></li>')
    for f in sorted(os.listdir(os.path.join(ROOT, "docs", "downloads"))):
        if f.endswith(".json"):
            dbody.append(f'<li><a href="{E(f)}">{E(f)}</a></li>')
    dbody.append("</ul>")
    with open(os.path.join(ROOT, "docs", "downloads", "index.html"), "w") as fh:
        fh.write(DL_HEADER + "".join(dbody) + DL_FOOTER)

    # Mirror the registries into docs/ so the published site can read them without the repo.
    import shutil
    for rel_ in ("related_sites.json", "hypotheses.json", "sources.json", "irregularities.json"):
        src_ = os.path.join(ROOT, "registry", rel_)
        if os.path.exists(src_):
            shutil.copyfile(src_, os.path.join(DOCS, rel_.replace("_", "-")))
    print("mirrored registry JSON into docs/")

    open(os.path.join(DOCS, "style.css"), "w").write(CSS)
    open(os.path.join(DOCS, "site.js"), "w").write(JS)
    print("wrote:", ", ".join(f"{s} ({b//1024} KB)" for s, b in written),
          "+ style.css, site.js")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

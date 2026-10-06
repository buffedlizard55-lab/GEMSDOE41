"""H41-I site fragments generated from measured receipts, not hand-entered scores."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
REPO = 'https://github.com/buffedlizard55-lab/GEMSDOE41'
E = html.escape


def load():
    return json.loads((DOCS / 'evidence/h41i/manifest.json').read_text())


def panel():
    m = load()
    return f'''<section class="card" id="latest-candidate"><span class="eyebrow">LATEST BUILD · 06 OCT 2026 · H41-I</span>
<h2>New local-strike transfer GeoTIFF</h2><p>Freshly computed from mapped geometry and the existing topographic tangent—not copied from H33 or another submission.</p>
<div class="actions"><a class="button primary" download href="downloads/{E(m['filename'])}">↓ Download new H41-I .tif</a><a href="h41i-executive-summary.html">Results &amp; submission instructions →</a></div>
<p><span class="pill warn">Format verified · holdout gate CLOSED · do not submit yet</span></p>
<p class="fine">Single float32 band · EPSG:32611 · 3730 rows × 3292 columns · all 12,279,160 numeric cells finite [0,1] · internal footprint mask. Earlier experiments below remain archived, not promoted.</p></section>'''


def render(page, table):
    m = load()
    conditional = json.loads((DOCS / 'evidence/h41i/conditional-holdout.json').read_text())
    strict = json.loads((DOCS / 'evidence/h41i/strict-holdout.json').read_text())
    a = m['concentration']
    rows = [[f['fold'], f['removed_sources'], f['models']['H41-I']['truth_pixels'],
             f"{f['models']['H41-I']['dti']:.6f}", f"{f['models']['H41-A_matched']['dti']:.6f}",
             f"{f['models']['catalogue_density']['dti']:.6f}", f"{f['models']['topography_only']['dti']:.6f}"] for f in conditional['folds']]
    summary = [[k, f"{v['mean_dti']:.6f}", f"{v['pooled_dti']:.6f}"] for k, v in conditional['summary'].items()]
    body = panel() + f'''<section class="section prose"><span class="eyebrow">EXECUTIVE SUMMARY</span><h1>A valid new file.<br>An unsuccessful refinement.</h1>
<p class="lead">H41-I replaces universal family axes with the actual local strike of the nearest mapped strand in the closer population. The hypothesis is distinct; the experiment does not justify a weekly submission.</p>
<h2>Decision first</h2><p>The strict 20 km audit remains at DTI {strict['summary']['H41-I']['mean_dti']:.6f}. The new geographically grouped, conditional short-strand audit retains donor/receiver context and withholds whole target sources. At matched mass, H41-I has lower mean and pooled DTI than H41-A. One fold has zero true-positive credit despite nonzero emission. <strong>No slot was used.</strong></p>
<p>This conditional audit is not a blind geographic holdout: visible context remains inside test quadrants, and short-strand target selection uses known transfer habitat. It is more appropriate for testing missing links but is selection-biased and not organizer truth. A clean historical-best OOF comparator is still absent.</p>
<h2>Exactly how to enter a submission—only after the gate passes</h2><ol>
<li>For inspection now, click <strong>Download new H41-I .tif</strong>. This is the actual raster, not an HTML report. No unzip or conversion is needed.</li>
<li>Check the file against the <a href="evidence/h41i/manifest.json">independent format receipt</a>. SHA-256: <code>{m['format']['sha256']}</code>. Do not resave it in an image editor.</li>
<li><strong>Stop for this candidate.</strong> It has not beaten the locked comparison. Format success is not validation success. These remaining steps describe the form, not a recommendation to use a slot.</li>
<li>For a future gate-cleared candidate, sign in to the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">official competition</a>, review its rules, choose New submission → File to submit, and select the exact <code>.tif</code>.</li>
<li>Use the tracking name and short note below. Preserve the organizer submission ID, score receipt, timestamp and exact file hash; never infer a filename score from a participant leaderboard row.</li></ol>
<p><strong>Tracking name:</strong> <code>{E(m['submission_name'])}</code></p>
<div class="copybox"><code id="h41i-note">{E(m['note'])}</code><button class="copy" type="button" data-copy="h41i-note">Copy note</button></div>
<h2>Why the range-error risk is addressed</h2><p>Independent re-read checks every numerical cell: min {m['format']['min']:.1f}, max {m['format']['max']:.9f}, no NaN, infinity, negative sentinel or nodata tag. Outside-region values are zero with an internal dataset mask, stored in the TIFF itself. CRS, shape, bounds and affine transform exactly match the pinned template. Organizer portal acceptance has not been tested. The legacy NaN-outside variants are not substituted for this finite export.</p>
<h2>Conditional spatial results</h2><p>{len(conditional['targets'])} eligible complete sources, allocated by centroid into four quadrants. Exclude 200 m around the retained catalogue; score 300 m-eroded interiors. All orientation, family distances, endpoints and exclusions are rebuilt from retained source geometry. Raw and matched-mass baselines are both retained, including negative results.</p>
{table(['Fold','Withheld sources','Scored truth px','H41-I','H41-A matched','Density matched','Terrain matched'], rows)}
{table(['Model','Mean DTI','Pooled DTI'], summary)}
<p>Means weight folds equally; pooled DTI combines TP/FP/FN. They are different estimands and are not leaderboard projections. The baseline initially looked weaker under raw unequal mass; the matched-mass comparison reverses that impression. No model thresholds were tuned after evaluation.</p>
<h2>Is it merely catalogue density?</h2><p>{100*a['junction_mass_fraction']:.2f}% of confidence mass and {100*a['top5percent_positive_at_junction_fraction']:.2f}% of the highest 5% positive cells lie in pre-defined cross-population junctions. NW-density enrichment: {a['family_density_controls']['0']['enrichment']:.2f}×; N/NNE-density enrichment: {a['family_density_controls']['1']['enrichment']:.2f}×. Zero positive pixels lie within 200 m of the catalogue. These are <strong>construction diagnostics, not discovery evidence</strong>.</p>
<p>All {len(m['novelty']['comparisons'])} available prior TIFF comparisons have different valid-pixel arrays. The field is built without any prior predictions. <strong>Important: it has the same nonzero support as H41-A; all 150,421 positive-cell confidence values changed. This is a new local-strike weighting hypothesis, not newly discovered geographic support.</strong> This does not prove uniqueness against unavailable private files.</p>
<h2>Can this beat 0.2778 or 0.3195?</h2><p><strong>Not established, and this candidate should not be used to test that hope.</strong> H33's documented 200 m flank prune removed 2,545 of 40,199 dots (6.33%). Under distance-weighted Tversky, eliminating redundant mass can improve precision without reducing maximum truth coverage. That is a plausible metric explanation—not proof of the reported score, a new geological observation, or proof that more pruning will help. A sparse, accurate new detector would need to improve coverage per unit false-positive cost. This local-strike experiment did not establish that improvement.</p>
<p>The reported filename score 0.2778 remains user-reported; GEMSDOE32 still labels its artifact unscored. Current leaderboard standings are unknown; this site does not poll DrivenData. See the <a href="research.html#h33-score-audit">dated score audit</a> and <a href="related-sites.json">all 39 related-site source checks</a>.</p>
<h2>Primary scientific sources and corrections</h2><ul>
<li><a href="https://nbmg.unr.edu/staff/Faulds/faulds_et_al_geology_paper.pdf">Faulds, Henry &amp; Hinz (2005)</a>: regional NW dextral-to-N normal transfer; also an ENE sinistral population. Strike class is a geometric proxy, not measured slip.</li>
<li><a href="https://www.osti.gov/servlets/purl/1110516">Siler, Mayhew &amp; Faulds: Astor Pass</a>: NW dextral / NNW normal interaction and 3D intersections. Not Emerson Pass and not uniformly NNE.</li>
<li><a href="https://www.osti.gov/servlets/purl/1110518">Anderson &amp; Faulds: Emerson Pass</a>: oppositely dipping normal-fault intersections in a regional transfer setting. Neither case validates this raster.</li>
<li><a href="https://gdr.openei.org/submissions/1391">INGENIOUS GDR 1391</a>: public CC BY 4.0 fault archive; attribution Ayling et al., DOI 10.15121/1881483. Raw raster mirrors are checksum-pinned but not authenticated organizer originals.</li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Competition specification</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official prize rules</a> · <a href="{REPO}/blob/main/research/hypotheses-20261006.md">Four preregistered hypotheses and protocol</a>.</li></ul>
<h2>Audit downloads and reproducibility</h2><ul><li><a href="evidence/h41i/manifest.json">File checks, concentration, all novelty comparisons, input/code hashes</a></li><li><a href="evidence/h41i/strict-holdout.json">Strict folds (negative regression audit)</a></li><li><a href="evidence/h41i/conditional-holdout.json">Conditional folds, source IDs and sufficient statistics</a></li><li><a href="{REPO}/blob/main/research/review-20261006.md">Three-pass review, limitations and next steps</a></li></ul>
<pre>bash scripts/download_competition_data.sh
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/experiment_h41i.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/build_site.py</pre>
<p>CPU-only. The static site serves a precomputed artifact; it does not pretend to generate TIFFs in the browser. The manual GitHub rebuild workflow regenerates it from pinned inputs without a competition upload.</p>
<p><strong>Cross-run reproducibility:</strong> local and branch-CI builds were byte-identical. A post-merge runner changed 36,761 confidence cells by at most 5 float32 epsilons, with exact support, grid, mask and outside values. This passes the existing 64-epsilon numerical gate; the cause remains unidentified. The published file hash has not changed. <a href="evidence/h41i/reproduction-postmerge.json">Runner receipt</a>.</p>
<h2>Next session: evidence before another slot</h2><ol><li>Obtain or reconstruct clean H33 out-of-fold predictions under exactly the same source withholding; a final H33 raster is contaminated as a comparator.</li><li>Validate independent terrain lineaments on a locked, new test region. Official USGS 3DEP metadata availability is not proof of downloaded coverage; acquire and audit actual needed tiles before claiming viability.</li><li>Only then consider the preregistered H41-J visibility, H41-K scale-relative reach, or H41-L receiver-incidence hypotheses. They are untested, not expected-score promises.</li><li>Do not infer geothermal vents, heat supply or hydraulic connectivity from this fault-confidence field.</li></ol></section>'''
    (DOCS / 'h41i-executive-summary.html').write_text(page('H41-I executive summary & download', body))

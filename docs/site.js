'use strict';
for (const button of document.querySelectorAll('[data-copy]')) {
  button.addEventListener('click', async () => {
    const text = document.getElementById(button.dataset.copy)?.textContent || '';
    try {
      await navigator.clipboard.writeText(text);
      button.textContent = 'Copied ✓';
    } catch {
      button.textContent = 'Select the note to copy';
      const range = document.createRange();
      range.selectNodeContents(document.getElementById(button.dataset.copy));
      const selection = window.getSelection();
      selection.removeAllRanges(); selection.addRange(range);
    }
  });
}

const feed = document.getElementById('source-feed');
if (feed) {
  fetch('source-feed.json', {cache: 'no-cache'})
    .then(response => {if (!response.ok) throw new Error('Feed unavailable'); return response.json();})
    .then(data => {
      const sources = data.sources || [];
      const failed = sources.filter(source => source.status === 'error').length;
      const board = sources.find(source => source.id === 'leaderboard');
      const rows = board?.leaderboard_rows || [];
      const wantedRanks = [1, 2, 3, 4, 13];
      const shown = wantedRanks
        .map(rank => rows.find(row => row.rank === rank))
        .filter(Boolean)
        .map(row => `#${row.rank} ${row.participant || 'participant not shown'} ${Number(row.score).toFixed(4)}`);
      feed.replaceChildren();
      let summary;
      if (board?.status === 'error' || !Number.isFinite(data.leader_score)) {
        summary = `Public-source snapshot: ${data.checked_utc}. The current leaderboard could not be verified; do not treat an older score as current. `;
      } else {
        summary = `Official public leaderboard snapshot: ${data.checked_utc}. ${shown.join(' · ')}. These are participant-level scores, not TIFF receipts. `;
      }
      feed.append(document.createTextNode(summary));
      if (failed) feed.append(document.createTextNode(`${failed} source check(s) failed; inspect the feed before relying on freshness. `));
      const boardLink = document.createElement('a');
      boardLink.href = board?.url || 'https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/';
      boardLink.textContent = 'Open official leaderboard ↗';
      feed.append(boardLink, document.createTextNode(' · '));
      const auditLink = document.createElement('a');
      auditLink.href = 'research.html#h33-score-audit';
      auditLink.textContent = 'H33 score audit ↗';
      feed.append(auditLink, document.createTextNode(' · '));
      const feedLink = document.createElement('a');
      feedLink.href = 'source-feed.json';
      feedLink.textContent = 'Inspect feed ↗';
      feed.append(feedLink);
    })
    .catch(() => {feed.append(' Latest feed unavailable; the dated observation above may be stale.');});
}

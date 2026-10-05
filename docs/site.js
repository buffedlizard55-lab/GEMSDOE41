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
      const failed = (data.sources || []).filter(source => source.status === 'error').length;
      feed.textContent = `Public-source snapshot: ${data.checked_utc}. ` +
        (Number.isFinite(data.leader_score) ? `Official leaderboard best: ${data.leader_score.toFixed(4)}. ` : 'Leaderboard could not be refreshed. ') +
        (failed ? `${failed} source check(s) failed; inspect the feed before relying on freshness. ` : '') +
        'Daily snapshot—not a prediction of our score. ';
      const link = document.createElement('a'); link.href = 'source-feed.json'; link.textContent = 'Inspect feed ↗'; feed.append(link);
    })
    .catch(() => {feed.append(' Latest feed unavailable; the dated observation above may be stale.');});
}

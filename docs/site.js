'use strict';

for (const button of document.querySelectorAll('[data-copy]')) {
  button.addEventListener('click', async () => {
    const target = document.getElementById(button.dataset.copy);
    const text = target?.textContent || '';
    try {
      await navigator.clipboard.writeText(text);
      button.textContent = 'Copied ✓';
    } catch {
      button.textContent = 'Select the note to copy';
      if (!target) return;
      const range = document.createRange();
      range.selectNodeContents(target);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
    }
  });
}

// This is a same-origin, static JSON read. It never fetches DrivenData or its
// leaderboard endpoint; users open the official link themselves if they choose.
const feed = document.getElementById('source-feed');
if (feed) {
  fetch('source-feed.json', {cache: 'no-store'})
    .then(response => {
      if (!response.ok) throw new Error('Public source snapshot unavailable');
      return response.json();
    })
    .then(data => {
      const competition = data.competition_leaderboard || {};
      const historic = competition.last_recorded_public_observation || {};
      const total = (data.sources || []).length;
      const ok = Number.isInteger(data.source_checks_ok) ? data.source_checks_ok : 0;
      const failed = Number.isInteger(data.source_checks_failed) ? data.source_checks_failed : Math.max(0, total - ok);
      const parts = [
        `Non-competition official-source snapshot: ${data.checked_utc || 'timestamp unavailable'}.`,
        `${ok}/${total} checks succeeded; ${failed} probe errors (not proof a source is offline).`,
        'DrivenData leaderboard monitoring is disabled by its Terms of Use; no current score is claimed.'
      ];
      if (Number.isFinite(historic.score) && historic.observed_date_utc) {
        parts.push(`Last recorded public observation: ${historic.score.toFixed(4)} on ${historic.observed_date_utc} (historical only; not current).`);
      }
      feed.replaceChildren(document.createTextNode(`${parts.join(' ')} `));
      const leaderboard = document.createElement('a');
      leaderboard.href = competition.leaderboard_url || 'https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/';
      leaderboard.textContent = 'Open official leaderboard ↗';
      feed.append(leaderboard, document.createTextNode(' · '));
      const terms = document.createElement('a');
      terms.href = competition.terms_url || 'https://www.drivendata.org/termsofuse/';
      terms.textContent = 'Terms of Use ↗';
      feed.append(terms, document.createTextNode(' · '));
      const details = document.createElement('a');
      details.href = 'source-feed.json';
      details.textContent = 'Inspect source snapshot ↗';
      feed.append(details);
    })
    .catch(() => {
      feed.replaceChildren(document.createTextNode('Public-source snapshot is unavailable; no current competition score is asserted. '));
      const link = document.createElement('a');
      link.href = 'https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/';
      link.textContent = 'Open official leaderboard ↗';
      feed.append(link);
    });
}

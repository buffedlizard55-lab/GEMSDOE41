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

// Live, public USGS ComCat events are useful regional context, but are not a
// fault inventory, geothermal confirmation, validation labels, or competition score.
const comcatStatus = document.getElementById('comcat-status');
const comcatList = document.getElementById('comcat-events');
const comcatQuery = document.getElementById('comcat-query');
if (comcatStatus && comcatList && comcatQuery) {
  const start = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const end = new Date().toISOString().slice(0, 10);
  const params = new URLSearchParams({
    format: 'geojson',
    starttime: start,
    endtime: end,
    minlatitude: '37.33119',
    maxlatitude: '40.72788',
    minlongitude: '-120.03717',
    maxlongitude: '-116.14092',
    minmagnitude: '1.0',
    orderby: 'time',
    limit: '20'
  });
  const url = `https://earthquake.usgs.gov/fdsnws/event/1/query?${params.toString()}`;
  comcatQuery.href = url;
  fetch(url, {headers: {Accept: 'application/geo+json'}, cache: 'no-store'})
    .then(response => {
      if (!response.ok) throw new Error(`USGS returned HTTP ${response.status}`);
      return response.json();
    })
    .then(payload => {
      const events = Array.isArray(payload.features) ? payload.features : [];
      comcatList.replaceChildren();
      if (events.length === 0) {
        const item = document.createElement('li');
        item.textContent = 'No magnitude ≥1 events were returned in this window.';
        comcatList.append(item);
      }
      for (const event of events) {
        const properties = event.properties || {};
        const item = document.createElement('li');
        const time = Number.isFinite(properties.time)
          ? new Date(properties.time).toLocaleString()
          : 'time unavailable';
        const magnitude = Number.isFinite(properties.mag)
          ? `M ${properties.mag.toFixed(1)}`
          : 'M —';
        item.append(document.createTextNode(`${magnitude} · ${properties.place || 'Unlocated event'} · ${time} `));
        if (properties.url) {
          const link = document.createElement('a');
          link.href = properties.url;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          link.textContent = 'USGS ↗';
          item.append(link);
        }
        comcatList.append(item);
      }
      comcatStatus.textContent = `Updated from USGS ComCat ${new Date().toLocaleString()} · ${events.length} event(s)`;
    })
    .catch(error => {
      comcatStatus.textContent = 'Live USGS feed unavailable in this browser; use the linked official query.';
      comcatList.replaceChildren();
      console.warn('USGS ComCat feed error:', error);
    });
}

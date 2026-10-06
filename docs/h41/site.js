// Progressive enhancement only: nothing on this site needs JavaScript to be readable.
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

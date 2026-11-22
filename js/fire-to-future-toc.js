// Fire to Future contents (fire-to-future/index.html): client-side search over the list
// Jekyll renders from _data/fire_to_future_chapters.json. Without this script the full
// list still shows; with it, typing filters it by title, number or part. Deferred, so the
// page is parsed when it runs.
(function () {
    var input = document.getElementById('tocSearch');
    var empty = document.getElementById('tocEmpty');
    var groups = document.querySelectorAll('.toc-group');
    if (!input || !empty) { return; }

    // A search typed with straight quotes still matches curly ones, and the other way round.
    function fold(s) {
        return String(s).toLowerCase().replace(/[‘’]/g, "'").replace(/[“”]/g, '"');
    }

    // Each row is matched on its number and title plus the name of its part.
    var rows = [];
    for (var g = 0; g < groups.length; g++) {
        var part = fold(groups[g].querySelector('.toc-group-head').textContent);
        var items = groups[g].querySelectorAll('.toc-rows > li');
        for (var i = 0; i < items.length; i++) {
            var num = items[i].querySelector('.toc-num');
            var title = items[i].querySelector('.toc-title');
            rows.push({
                li: items[i],
                group: groups[g],
                text: fold((num ? num.textContent : '') + ' ' + (title ? title.textContent : '')) + ' ' + part
            });
        }
    }

    function filter() {
        var q = fold(input.value).trim();
        var shown = 0;
        for (var g = 0; g < groups.length; g++) { groups[g].hidden = true; }
        for (var r = 0; r < rows.length; r++) {
            var hit = !q || rows[r].text.indexOf(q) !== -1;
            rows[r].li.hidden = !hit;
            if (hit) {
                rows[r].group.hidden = false;
                shown++;
            }
        }
        empty.hidden = shown !== 0;
    }

    input.addEventListener('input', filter);
    if (input.value) { filter(); }  // a query the browser restored on back/forward
})();

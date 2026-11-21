// Novel table of contents (novel/index.html): render + client-side search.
// Chapter data comes from /novel/chapters.js (Jekyll-rendered global). Both scripts are
// deferred, so the page is parsed when this runs.
(function () {
    var CHAPTERS = window.NOVEL_CHAPTERS || [];

    // Escape strings before injecting into innerHTML (titles come from site data)
    function esc(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    // Titles use curly quotes and apostrophes; a search typed with straight ones still matches.
    function fold(s) {
        return String(s).toLowerCase().replace(/[‘’]/g, "'").replace(/[“”]/g, '"');
    }

    // Known volume markers: chapter number -> volume label
    var VOLUMES = { 514: "Volume 6", 1758: "Volume 19", 1816: "Volume 20" };

    function renderToc(filter) {
        var list = document.getElementById('tocList');
        var empty = document.getElementById('tocEmpty');
        var q = fold(filter || '').trim();
        var html = '';
        var count = 0;

        for (var i = 0; i < CHAPTERS.length; i++) {
            var ch = CHAPTERS[i];
            if (q && fold(ch.title).indexOf(q) === -1 && String(ch.num).indexOf(q) === -1) {
                continue;
            }
            if (VOLUMES[ch.num]) {
                html += '<li class="toc-volume-divider">' + esc(VOLUMES[ch.num]) + '</li>';
            }
            html += '<li><a href="/translated/' + esc(ch.file) + '">' +
                '<span class="chapter-num">' + esc(ch.num) + '</span>' +
                '<span class="chapter-title">' + esc(ch.title) + '</span>' +
                '</a></li>';
            count++;
        }

        list.innerHTML = html;
        empty.hidden = count !== 0;
    }

    document.getElementById('tocSearch').addEventListener('input', function (e) {
        renderToc(e.target.value);
    });

    renderToc('');
})();

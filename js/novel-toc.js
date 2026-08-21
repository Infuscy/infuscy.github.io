// Novel table-of-contents: render + client-side search.
// Chapter data comes from /novel/chapters.js (Jekyll-rendered global).
(function () {
    var CHAPTERS = window.NOVEL_CHAPTERS || [];

    // Escape strings before injecting into innerHTML (titles come from site data)
    function esc(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    // Known volume markers: chapter number -> volume label
    var VOLUMES = { 514: "Volume 6", 1758: "Volume 19", 1816: "Volume 20" };

    function renderToc(filter) {
        var list = document.getElementById('tocList');
        var empty = document.getElementById('tocEmpty');
        var q = (filter || '').toLowerCase().trim();
        var html = '';
        var count = 0;

        for (var i = 0; i < CHAPTERS.length; i++) {
            var ch = CHAPTERS[i];
            if (q && ch.title.toLowerCase().indexOf(q) === -1 && String(ch.num).indexOf(q) === -1) {
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
        empty.style.display = count === 0 ? '' : 'none';
    }

    document.getElementById('tocSearch').addEventListener('input', function(e) {
        renderToc(e.target.value);
    });

    renderToc('');
})();

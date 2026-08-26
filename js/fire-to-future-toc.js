// Fire to Future table-of-contents: render + client-side search.
// Chapter data comes from /fire-to-future/chapters.js (Jekyll-rendered global).
(function () {
    var CHAPTERS = window.FIRE_TO_FUTURE_CHAPTERS || [];

    // Escape strings before injecting into innerHTML (titles come from site data)
    function esc(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    function renderToc(filter) {
        var list = document.getElementById('tocList');
        var empty = document.getElementById('tocEmpty');
        var q = (filter || '').toLowerCase().trim();
        var html = '';
        var count = 0;
        var lastPart = null;

        for (var i = 0; i < CHAPTERS.length; i++) {
            var ch = CHAPTERS[i];
            if (q && ch.title.toLowerCase().indexOf(q) === -1 &&
                String(ch.num).toLowerCase().indexOf(q) === -1 &&
                ch.part.toLowerCase().indexOf(q) === -1) {
                continue;
            }
            if (ch.part !== lastPart) {
                html += '<li class="toc-part-divider">' + esc(ch.part) + '</li>';
                lastPart = ch.part;
            }
            var typeTag = ch.type === 'chapter' ? '' : ' <span class="chapter-type">' +
                (ch.type === 'appendix' ? 'appendix' : 'intro') + '</span>';
            html += '<li><a href="/fire-to-future/' + esc(ch.file) + '">' +
                '<span class="chapter-num">' + esc(ch.num) + '</span>' +
                '<span class="chapter-title">' + esc(ch.title) + typeTag + '</span>' +
                '</a></li>';
            count++;
        }

        list.innerHTML = html;
        empty.style.display = count === 0 ? '' : 'none';
    }

    var input = document.getElementById('tocSearch');
    if (input) {
        input.addEventListener('input', function () { renderToc(input.value); });
    }
    renderToc('');
})();

// Site behaviour for the Jekyll layer, with no library behind it: the mobile
// menu, the nav dropdowns, the section highlight, the shrinking navbar and
// the scroll-to-top button. The markup keeps Bootstrap 3's class names
// (.collapse.in, .dropdown.open, .active) because the stylesheet styles those.

// Clickjacking protection: GitHub Pages cannot set X-Frame-Options /
// frame-ancestors (no custom headers, and meta CSP can't express it).
// Break out of any frame that isn't our own top-level window.
(function () {
    try {
        if (window.top && window.top !== window.self) {
            window.top.location = window.self.location;
        }
    } catch (e) {
        // Cross-origin framing: can't inspect top; hide the page instead.
        document.documentElement.style.display = 'none';
    }
})();

(function () {
    'use strict';

    var nav = document.querySelector('.navbar-fixed-top');
    if (!nav) {
        return;
    }
    var toggle = nav.querySelector('.navbar-toggle');
    var menu = nav.querySelector('.navbar-collapse');
    var dropdowns = Array.prototype.slice.call(nav.querySelectorAll('.dropdown'));

    // ---- Mobile menu ----
    function setMenu(open) {
        menu.classList.toggle('in', open);
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (!open) {
            closeDropdowns();
        }
    }
    toggle.addEventListener('click', function () {
        setMenu(!menu.classList.contains('in'));
    });

    // ---- Dropdowns ----
    function setDropdown(item, open) {
        item.classList.toggle('open', open);
        item.querySelector('.dropdown-toggle').setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    function closeDropdowns(except) {
        dropdowns.forEach(function (item) {
            if (item !== except) {
                setDropdown(item, false);
            }
        });
    }
    function menuLinks(item) {
        return Array.prototype.slice.call(item.querySelectorAll('.dropdown-menu a'));
    }
    dropdowns.forEach(function (item) {
        var button = item.querySelector('.dropdown-toggle');
        // The toggle's href points at the section, so the link still works
        // without JavaScript; with it, the click opens the submenu instead.
        button.addEventListener('click', function (event) {
            event.preventDefault();
            var open = !item.classList.contains('open');
            closeDropdowns(item);
            setDropdown(item, open);
        });
        item.addEventListener('keydown', function (event) {
            var links = menuLinks(item);
            var at = links.indexOf(document.activeElement);
            if (event.key === 'Escape' && item.classList.contains('open')) {
                setDropdown(item, false);
                button.focus();
            } else if (event.key === ' ' && document.activeElement === button) {
                // role="button": Space activates it, like Enter does for a link.
                event.preventDefault();
                button.click();
            } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
                if (!item.classList.contains('open')) {
                    closeDropdowns(item);
                    setDropdown(item, true);
                }
                var step = event.key === 'ArrowDown' ? 1 : -1;
                var next = at === -1 ? (step === 1 ? 0 : links.length - 1) : (at + step + links.length) % links.length;
                links[next].focus();
            }
        });
        // Leaving the dropdown with Tab closes it.
        item.addEventListener('focusout', function (event) {
            if (event.relatedTarget && !item.contains(event.relatedTarget)) {
                setDropdown(item, false);
            }
        });
    });
    document.addEventListener('click', function (event) {
        if (!event.target.closest('.navbar-fixed-top .dropdown')) {
            closeDropdowns();
        }
    });

    // Following a menu link closes the mobile menu (in-page links stay on the page).
    menu.addEventListener('click', function (event) {
        var link = event.target.closest('a');
        if (link && !link.classList.contains('dropdown-toggle')) {
            setMenu(false);
        }
    });

    // ---- Scroll state: shrunk navbar, scroll-to-top button, section highlight ----
    var topButton = document.querySelector('.scroll-top');
    var spies = Array.prototype.slice.call(nav.querySelectorAll('[data-spy]')).map(function (item) {
        return { item: item, section: document.getElementById(item.getAttribute('data-spy')) };
    }).filter(function (spy) {
        return spy.section;
    });

    // Floating "back to contents" pill of the long report (romania-deficit):
    // hidden while the contents list itself is near (is-top), and marked
    // is-reading while scrolling down, so on narrow screens, where it sits
    // over the text, it only shows when the reader scrolls back up.
    var tocPill = document.querySelector('.la-cuprins');
    var lastY = window.scrollY;

    function update() {
        ticking = false;
        var y = window.scrollY;
        nav.classList.toggle('navbar-shrink', y >= 300);
        if (topButton) {
            topButton.classList.toggle('is-visible', y > 600);
        }
        if (tocPill) {
            tocPill.classList.toggle('is-top', y < 600);
            if (Math.abs(y - lastY) > 4) {
                tocPill.classList.toggle('is-reading', y > lastY);
            }
        }
        lastY = y;
        // The current section is the last one whose top has passed under the
        // navbar (sections have scroll-margin-top: 4rem, plus a little slack).
        var current = null;
        var atBottom = window.innerHeight + y >= document.documentElement.scrollHeight - 2;
        spies.forEach(function (spy) {
            if (spy.section.getBoundingClientRect().top <= 80) {
                current = spy;
            }
        });
        if (atBottom && spies.length) {
            current = spies[spies.length - 1];
        }
        spies.forEach(function (spy) {
            spy.item.classList.toggle('active', spy === current);
        });
    }
    var ticking = false;
    window.addEventListener('scroll', function () {
        if (!ticking) {
            ticking = true;
            window.requestAnimationFrame(update);
        }
    }, { passive: true });
    window.addEventListener('resize', update);
    update();
})();

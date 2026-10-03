/*!
 * Start Bootstrap - Freelancer Bootstrap Theme (http://startbootstrap.com)
 * Code licensed under the Apache License v2.0.
 * For details, see http://www.apache.org/licenses/LICENSE-2.0.
 */

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

// In-page scrolling is CSS (scroll-behavior + scroll-margin-top in main.css),
// so "/#portfolio" links work the same from the home page and from subpages.

// Highlight the top nav as scrolling occurs. The offset covers the sections'
// scroll-margin-top (4rem) plus a little slack.
$('body').scrollspy({
    target: '.navbar-fixed-top',
    offset: 80
});

// Closes the Responsive Menu on Menu Item Click (not on the dropdown toggle,
// which would collapse the menu before its submenu can be used).
$('.navbar-collapse ul li a:not(.dropdown-toggle)').on('click', function() {
    $('.navbar-toggle:visible').click();
});

// Keep hamburger aria-expanded in sync (Bootstrap 3 toggles collapse only).
$(function() {
    var $toggle = $('.navbar-toggle');
    var $menu = $('#bs-example-navbar-collapse-1');
    $menu.on('shown.bs.collapse', function() { $toggle.attr('aria-expanded', 'true'); });
    $menu.on('hidden.bs.collapse', function() { $toggle.attr('aria-expanded', 'false'); });
});

// Scroll-to-top button: only shown once the hero is out of view.
$(function() {
    var $btn = $('.scroll-top');
    if (!$btn.length) {
        return;
    }
    var ticking = false;
    function update() {
        $btn.toggleClass('is-visible', window.scrollY > 600);
        ticking = false;
    }
    window.addEventListener('scroll', function() {
        if (!ticking) {
            ticking = true;
            window.requestAnimationFrame(update);
        }
    }, { passive: true });
    update();
});

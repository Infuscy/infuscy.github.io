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

// jQuery for page scrolling feature - requires jQuery Easing plugin
// Anchors may carry a path ("/#portfolio"): same-path anchors keep the
// smooth scroll; cross-path anchors fall through to normal navigation
// so the navbar links work from subpages too.
$(function() {
    var reduceMotion = window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    function smoothTo($target) {
        var top = $target.offset().top;
        if (reduceMotion) {
            $('html, body').stop().scrollTop(top);
            return;
        }
        $('html, body').stop().animate({
            scrollTop: top
        }, 1500, 'easeInOutExpo');
    }
    $('.page-scroll a').on('click', function(event) {
        var href = $(this).attr('href') || '';
        var hashIdx = href.indexOf('#');
        if (hashIdx === -1) {
            return; // plain/external link: normal navigation
        }
        var path = href.slice(0, hashIdx) || location.pathname;
        var hash = href.slice(hashIdx);
        if (path === location.pathname) {
            var $target = $(hash);
            if ($target.length) {
                smoothTo($target);
                event.preventDefault();
            }
        }
        // else: link to another page - let the browser navigate
    });
    // Hero CTA is a plain anchor (not inside .page-scroll li).
    $('.page-scroll-cta').on('click', function(event) {
        var $target = $($(this).attr('href'));
        if ($target.length) {
            smoothTo($target);
            event.preventDefault();
        }
    });
});

// Floating label headings for the contact form
$(function() {
    $("body").on("input propertychange", ".floating-label-form-group", function(e) {
        $(this).toggleClass("floating-label-form-group-with-value", !! $(e.target).val());
    }).on("focus", ".floating-label-form-group", function() {
        $(this).addClass("floating-label-form-group-with-focus");
    }).on("blur", ".floating-label-form-group", function() {
        $(this).removeClass("floating-label-form-group-with-focus");
    });
});

// Highlight the top nav as scrolling occurs
$('body').scrollspy({
    target: '.navbar-fixed-top'
})

// Closes the Responsive Menu on Menu Item Click
$('.navbar-collapse ul li a').click(function() {
    $('.navbar-toggle:visible').click();
});

// Keep hamburger aria-expanded in sync (Bootstrap 3 toggles collapse only).
$(function() {
    var $toggle = $('.navbar-toggle');
    var $menu = $('#bs-example-navbar-collapse-1');
    $menu.on('shown.bs.collapse', function() { $toggle.attr('aria-expanded', 'true'); });
    $menu.on('hidden.bs.collapse', function() { $toggle.attr('aria-expanded', 'false'); });
});

// Portfolio modals: focus management + keyboard-dismissable custom X.
// Keeps jQuery-3 compatible API (.on only).
$(function() {
    var lastTrigger = null;
    $('.portfolio-modal').on('show.bs.modal', function(event) {
        lastTrigger = event.relatedTarget || document.activeElement;
    });
    $('.portfolio-modal').on('shown.bs.modal', function() {
        $(this).find('[data-dismiss="modal"].btn, .close-modal').first().focus();
    });
    $('.portfolio-modal').on('hidden.bs.modal', function() {
        if (lastTrigger && lastTrigger.focus) {
            lastTrigger.focus();
        }
        lastTrigger = null;
    });
    $('.portfolio-modal .close-modal').on('keydown', function(event) {
        if (event.which === 13 || event.which === 32) {
            event.preventDefault();
            $(this).closest('.portfolio-modal').modal('hide');
        }
    });
});

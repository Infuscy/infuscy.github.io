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
                $('html, body').stop().animate({
                    scrollTop: $target.offset().top
                }, 1500, 'easeInOutExpo');
                event.preventDefault();
            }
        }
        // else: link to another page - let the browser navigate
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

/**
 * Future HSE Academy — Main JavaScript
 * Minimal JS for navbar scroll effect and smooth interactions.
 */

document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    // ── Navbar scroll shadow effect ────────────────────────────
    var navbar = document.getElementById('main-navbar');
    if (navbar) {
        var scrollThreshold = 10;
        window.addEventListener('scroll', function () {
            if (window.scrollY > scrollThreshold) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        }, { passive: true });
    }
});

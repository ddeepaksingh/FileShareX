// Hamburger menu toggle
(function () {
    const btn    = document.getElementById('hamburger');
    const mobile = document.getElementById('nav-mobile');
    if (!btn || !mobile) return;

    btn.addEventListener('click', function () {
        const open = mobile.classList.toggle('open');
        btn.classList.toggle('open', open);
        btn.setAttribute('aria-expanded', open);
    });

    document.addEventListener('click', function (e) {
        if (!btn.contains(e.target) && !mobile.contains(e.target)) {
            mobile.classList.remove('open');
            btn.classList.remove('open');
            btn.setAttribute('aria-expanded', 'false');
        }
    });
})();

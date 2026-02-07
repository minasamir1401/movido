/**
 * THE VACCINE: Aggressive Ad-Killer & Popup Blocker
 * This script is injected into sanitized streams to kill ads dead.
 */

(function() {
    console.log("💉 Vaccine Injected: Starting sterilization...");

    // 1. Kill window.open (Prevents Popups)
    window.open = function(url, target, features) {
        console.log("🚫 Blocked popup to:", url);
        return null;
    };

    // 2. Kill Form Submits to new tabs
    document.addEventListener('submit', function(e) {
        if (e.target.target === '_blank') {
            e.preventDefault();
            console.log("🚫 Blocked new tab form submit");
        }
    }, true);

    // 3. Kill Link Clicks that open new windows (if not content)
    document.addEventListener('click', function(e) {
        // Find closest anchor
        let target = e.target.closest('a');
        if (target) {
            // Allow clicking control buttons or internal links
            if (target.getAttribute('href') === '#' || target.getAttribute('href').startsWith('javascript:')) {
                return;
            }
            
            // If it tries to open a new tab or goes to common ad networks
            if (target.target === '_blank' || isAdDomain(target.href)) {
                e.preventDefault();
                e.stopPropagation(); // Stop bubbling
                console.log("🚫 Blocked click to:", target.href);
            }
        }
    }, true);

    // 4. Aggressive Element Remover (Invisible Overlays)
    setInterval(function() {
        const suspicious = document.querySelectorAll('div, iframe, a');
        suspicious.forEach(el => {
            const style = window.getComputedStyle(el);
            
            // Full screen invisible overlays (Clickjacking)
            if (style.position === 'fixed' && style.zIndex > 100 && style.opacity < 0.1) {
                el.remove();
                console.log("🗑️ Removed invisible overlay");
            }
            
            // Known ad class names
            if (el.className && typeof el.className === 'string' && 
                (el.className.includes('ads') || el.className.includes('banner') || el.className.includes('pop'))) {
                el.style.display = 'none';
            }
        });
    }, 1000);

    // Helper: Check for ad domains
    function isAdDomain(url) {
        const adKeywords = ['bet', 'casino', 'dating', 'tracker', 'click', 'adservice', 'pop'];
        return adKeywords.some(keyword => url.toLowerCase().includes(keyword));
    }

    console.log("🛡️ Vaccine Active: Area Secured.");
})();

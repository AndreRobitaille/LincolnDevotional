(function () {
    document.addEventListener('DOMContentLoaded', () => {
        const link = document.getElementById('devotionLink');
        if (!link) {
            return;
        }

        link.addEventListener('click', async (event) => {
            if (
                event.button !== 0 ||
                event.ctrlKey ||
                event.metaKey ||
                event.shiftKey ||
                event.altKey
            ) {
                return;
            }

            const href = link.getAttribute('href');
            if (!href || href === '#') {
                return;
            }

            const permalinkUrl = new URL(href, window.location.href).toString();
            const linkTitle =
                link.dataset.linkTitle ||
                document.title ||
                "The Believer's Daily Treasure";

            if (typeof navigator.share === 'function') {
                event.preventDefault();
                try {
                    await navigator.share({ title: linkTitle, url: permalinkUrl });
                } catch (err) {
                    if (err && err.name !== 'AbortError') {
                        const ok = await copyToClipboard(permalinkUrl);
                        showToast(ok ? 'Link copied' : "Couldn’t open link tool");
                    }
                }
                return;
            }

            event.preventDefault();
            const ok = await copyToClipboard(permalinkUrl);
            showToast(ok ? 'Link copied' : "Couldn’t copy link");
        });
    });

    async function copyToClipboard(text) {
        if (navigator.clipboard && window.isSecureContext) {
            try {
                await navigator.clipboard.writeText(text);
                return true;
            } catch (err) {
                // Fall through to legacy path
            }
        }
        return legacyCopy(text);
    }

    function legacyCopy(text) {
        try {
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.setAttribute('readonly', '');
            ta.style.position = 'fixed';
            ta.style.top = '0';
            ta.style.left = '0';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            ta.setSelectionRange(0, text.length);
            const ok = document.execCommand('copy');
            document.body.removeChild(ta);
            return ok;
        } catch (err) {
            return false;
        }
    }

    let toastTimer = null;
    function showToast(message) {
        let toast = document.getElementById('permalinkToast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'permalinkToast';
            toast.className = 'permalink-toast';
            toast.setAttribute('role', 'status');
            toast.setAttribute('aria-live', 'polite');
            const host = document.getElementById('devotionLinkArea') || document.body;
            host.appendChild(toast);
        }
        toast.textContent = message;
        void toast.offsetWidth;
        toast.classList.add('permalink-toast--visible');
        if (toastTimer) {
            clearTimeout(toastTimer);
        }
        toastTimer = setTimeout(() => {
            toast.classList.remove('permalink-toast--visible');
        }, 2200);
    }
})();

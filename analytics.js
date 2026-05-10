(function () {
    var GA_ID = 'G-STY5G3WBEQ';

    var loader = document.createElement('script');
    loader.async = true;
    loader.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(loader);

    window.dataLayer = window.dataLayer || [];
    function gtag() { window.dataLayer.push(arguments); }
    window.gtag = gtag;

    gtag('js', new Date());
    gtag('config', GA_ID);
})();

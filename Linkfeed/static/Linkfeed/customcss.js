function applyCustomCSS() {
    fetch("/Linkfeed/upload_css/")
        .then(response => response.json())
        .then(data => {
            console.log("Hello")
            var customCSSLink = data.link;
            var head = document.head || document.getElementsByTagName('head')[0];
            var existingCSSLink = document.getElementById("customCSS");

            if (existingCSSLink) {
                existingCSSLink.href = customCSSLink;
            } else {
                var cssLink = document.createElement('link');
                cssLink.rel = 'stylesheet';
                cssLink.type = 'text/css';
                cssLink.href = customCSSLink;
                cssLink.id = "customCSS";
                head.appendChild(cssLink);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            // Handle error if needed
        });
}
window.onload = applyCustomCSS;


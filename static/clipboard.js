// Source - https://stackoverflow.com/a/72239825
// Posted by Alicia Sykes, modified by community. See post 'Timeline' for change history
// Retrieved 2026-08-28, License - CC BY-SA 4.0
// unsecured to allow for plain http
function unsecuredCopyToClipboard(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
        document.execCommand("copy");
    } catch (err) {
        console.error("Unable to copy to clipboard", err);
    }
    document.body.removeChild(textArea);
    Toastify({
        text: "Copied to clipboard!",
        duration: 1000,
        position: "center", // `left`, `center` or `right`
        style: {
            background: "var(--back-color)",
            color: "var(--front-color)",
            border: "solid var(--border-thickness) var(--front-color)",
        },
    }).showToast();
}

function copyMe(el) {
    unsecuredCopyToClipboard(el.innerText);
}

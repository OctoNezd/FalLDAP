const clicktocopytext = document.createElement("span");
clicktocopytext.id = "clicktocopytext";
clicktocopytext.innerText = "(Click to copy)";
bar.text.appendChild(clicktocopytext);

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
}

const timeframe = 0.1;
const reloadinterval = setInterval(() => {
    remaining_time -= 0.1;
    const progress = remaining_time / total_time;
    bar.setValue(progress);
    let finalcolor = "green";
    if (progress < 0.3) {
        finalcolor = "red";
    } else if (progress < 0.8) {
        finalcolor = "yellow";
    }
    bar.colorFg = finalcolor;
    bar.draw(true);
    if (remaining_time <= 0) {
        console.log("Reloading.");
        clearInterval(reloadinterval);
        location.reload();
    }
}, timeframe * 1000);
document.getElementById("bar").onclick = () => {
    unsecuredCopyToClipboard(codeEl.innerText);
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
};

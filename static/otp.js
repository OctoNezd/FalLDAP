window.ticker = undefined;
function init_otp(total_time, code) {
    clearInterval(window.ticker);
    var bar = new RadialProgress(document.getElementById("bar"), {
        progress: 0.9,
        colorFg: "#FF5858",
        thick: 2.5,
        fixedTextSize: 0.8,
        noPercentage: true,
    });
    const codeEl = document.createElement("span");
    codeEl.id = "code";
    codeEl.classList.add("code");
    codeEl.innerText = code;
    bar.text.appendChild(codeEl);

    var remaining_time = total_time;
    const clicktocopytext = document.createElement("span");
    clicktocopytext.id = "clicktocopytext";
    clicktocopytext.innerText = "(Click to copy)";
    bar.text.appendChild(clicktocopytext);

    const timeframe = 0.1;
    window.ticker = setInterval(() => {
        remaining_time -= 0.1;
        const progress = remaining_time / total_time;
        bar.setValue(progress);
        // i asked deepseek for this and it threw that at me
        // it looks good enough
        let hue;
        if (progress >= 0.8) {
            const t = (progress - 0.8) / 0.2; // 1 → 0
            hue = 60 + 60 * t; // 120 (green) → 60 (yellow)
        } else if (progress >= 0.3) {
            const t = (progress - 0.3) / 0.5; // 1 → 0
            hue = 60 * t; // 60 (yellow) → 0 (red)
        } else {
            hue = 0;
        }
        bar.colorFg = `hsl(${hue}, 100%, 50%)`;
        bar.draw(true);
    }, timeframe * 1000);
    document.getElementById("bar").onclick = () => {
        unsecuredCopyToClipboard(codeEl.innerText);
    };
}

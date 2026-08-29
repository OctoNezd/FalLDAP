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
        let finalcolor = "green";
        if (progress < 0.3) {
            finalcolor = "red";
        } else if (progress < 0.8) {
            finalcolor = "yellow";
        }
        bar.colorFg = finalcolor;
        bar.draw(true);
    }, timeframe * 1000);
    document.getElementById("bar").onclick = () => {
        unsecuredCopyToClipboard(codeEl.innerText);
    };
}

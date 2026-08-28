const clicktocopytext = document.createElement("span");
clicktocopytext.id = "clicktocopytext";
clicktocopytext.innerText = "(Click to copy)";
bar.text.appendChild(clicktocopytext);

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
};

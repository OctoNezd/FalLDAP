function modal_toggle(modalId) {
    const modalEl = document.getElementById(modalId);
    if (modalEl.classList.contains("open")) {
        modal_close(modalId);
        return;
    }
    modalEl.classList.add("open");
}
function modal_reset(modalId) {
    console.log("mdl reset");
    const modal = document.getElementById(modalId);
    modal.querySelector(".modal-body").innerHTML =
        modal.getAttribute("original-body");
    modal.classList.remove("open");
    modal_toggle(modalId);
    htmx.process(modal);
}
function modal_close(modalId) {
    const modal = document.getElementById(modalId);
    modal_reset(modalId);
    modal.classList.remove("open");
}
console.log(document.querySelectorAll(".modal"));
for (const modal of document.querySelectorAll(".modal")) {
    modal.setAttribute(
        "original-body",
        modal.querySelector(".modal-body").innerHTML,
    );
    modal.addEventListener("click", (e) => {
        if (e.target == modal) {
            e.preventDefault();
            modal_close(modal.id);
        }
    });
}

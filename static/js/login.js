// function showLoader() {
//     const btn = document.getElementById("submitBtn");
//     btn.disabled = true;
//     btn.innerHTML = "Please wait...";
// }
function showLoader(form) {
    const btn = form.querySelector("button[type='submit']");
    const btnText = btn.querySelector(".btn-text");
    const loader = btn.querySelector(".loading");

    btn.disabled = true;
    btn.style.cursor = "not-allowed";

    // Hide text and show loader
    btnText.style.display = "none";
    loader.style.display = "flex";

    return true; // Allow form submit
}

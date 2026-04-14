// content.js - Injects a floating button when text is selected
let floatingButton = null;

document.addEventListener('mouseup', (e) => {
    const selectedText = window.getSelection().toString().trim();

    if (selectedText.length > 0) {
        showFloatingButton(e.clientX, e.clientY, selectedText);
    } else {
        removeFloatingButton();
    }
});

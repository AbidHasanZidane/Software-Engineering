function getSelectedText() {
    return window.getSelection().toString().trim();
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getText") {
        sendResponse({ text: getSelectedText() });
    }
});
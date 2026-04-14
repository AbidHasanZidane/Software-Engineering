// background.js - Handles API calls and popup opening
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'checkText') {
        // Call the Flask API
        fetch('http://localhost:5000/check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: request.text })
        })
            .then(response => response.json())
            .then(data => {
                sendResponse(data);
            })
            .catch(error => {
                sendResponse({ error: error.message, verdict: 'API Error', confidence: 0, details: 'Could not reach AI service' });
            });
        return true; // Keep message channel open for async response
    }

    if (request.action === 'openPopup') {
        // Open the popup programmatically (optional, user can also click extension icon)
        chrome.action.openPopup();
    }
});

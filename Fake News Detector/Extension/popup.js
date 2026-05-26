// popup.js - Automatically checks text when popup opens
document.addEventListener('DOMContentLoaded', async () => {
    const selectedTextDiv = document.getElementById('selectedText');
    const resultDiv = document.getElementById('result');

    // Get the currently selected text from the active tab (not from storage)
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const results = await chrome.scripting.executeScript({
        target: { tabId: tabs[0].id },
        func: () => window.getSelection().toString().trim()
    });

    const currentSelectedText = results[0]?.result || '';

    if (currentSelectedText) {
        // Display the currently selected text
        selectedTextDiv.textContent = `"${currentSelectedText.substring(0, 100)}${currentSelectedText.length > 100 ? '...' : ''}"`;

        // Store it for the API call
        await chrome.storage.local.set({ selectedText: currentSelectedText });

        // Auto-check when popup opens
        resultDiv.innerHTML = '<span class="loading">Checking with AI...</span>';

        chrome.runtime.sendMessage(
            { action: 'checkText', text: currentSelectedText },
            (response) => {
                if (response.error) {
                    resultDiv.innerHTML = `<span class="error">Error: ${response.error}</span>`;
                } else {
                    resultDiv.innerHTML = `
                        <strong>Result:</strong><br>
                        Verdict: ${response.verdict}<br>
                        Confidence: ${response.confidence}%<br>
                        <small>${response.details}</small>
                    `;
                }
            }
        );
    } else {
        // No text selected - clear everything
        selectedTextDiv.textContent = 'Please select some text.';
        resultDiv.innerHTML = '<span class="error"></span>';

        // Clear the stored text to prevent old results
        await chrome.storage.local.remove('selectedText');
    }
    
});


document.getElementById("check").onclick = async () => {
    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    chrome.tabs.sendMessage(tab.id, { action: "getText" }, async (response) => {
        let text = response.text;

        if (!text) {
            alert("Please select some text first.");
            return;
        }

        try {
            console.log("Sending request...");

            let response = await fetch("http://127.0.0.1:5000/predict", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ text })
            });

            console.log("Response received:", response);

            let data = await response.json();
            console.log("Data:", data);

            alert(`Result: ${data.label} (${data.confidence})\n${data.explanation}`);
        } catch (err) {
            console.error("Fetch error:", err);
            alert("Error connecting to API");
        }
    });
};
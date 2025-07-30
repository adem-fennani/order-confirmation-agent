chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "sendOrderData") {
        fetch("http://localhost:8000/orders", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(request.orderData)
        })
        .then(response => response.json())
        .then(data => {
            console.log("Order created successfully:", data);
            sendResponse({ status: "success", data: data });
        })
        .catch(error => {
            console.error("Error creating order:", error);
            sendResponse({ status: "error", message: error.message });
        });
        return true; // Indicates that sendResponse will be called asynchronously
    }
});

// Optional: Listen for tab updates to potentially inject content script earlier or for debugging
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url && (
        tab.url.includes('facebook.com/marketplace/checkout/done') ||
        tab.url.includes('facebook.com/marketplace/orders')
    )) {
        console.log(`Tab updated: ${tab.url}`);
        // You might want to programmatically inject the content script here
        // if it's not reliably injecting via manifest.json for some reason.
        // For now, manifest.json should handle it.
    }
});
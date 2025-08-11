chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "sendOrderData") {
        chrome.storage.sync.get(['apiKey', 'siteId'], (items) => {
            const { customer_name, customer_phone, ...order_data_rest } = request.orderData;

            const submissionData = {
                site_id: items.siteId,
                site_url: sender.tab.url,
                order_data: {
                    items: order_data_rest.items,
                    total_amount: order_data_rest.total_amount,
                    notes: order_data_rest.notes
                },
                customer_info: {
                    customer_name: customer_name,
                    customer_phone: customer_phone
                }
            };

            fetch("http://localhost:8000/orders/submit", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-Key": items.apiKey
                },
                body: JSON.stringify(submissionData)
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.detail) });
                }
                return response.json();
            })
            .then(data => {
                console.log("Order created successfully:", data);
                sendResponse({ status: "success", data: data });
            })
            .catch(error => {
                console.error("Error creating order:", error);
                sendResponse({ status: "error", message: error.message });
            });
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
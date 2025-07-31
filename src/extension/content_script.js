// This script runs on the Facebook Marketplace confirmation page.

async function extractOrderData() {
    // 1. Get user data from storage
    const userData = await new Promise((resolve) => {
        chrome.storage.sync.get(['customerName', 'customerPhone'], (items) => {
            resolve(items);
        });
    });

    let orderData = {};

    // --- Customer Information ---
    orderData.customer_name = userData.customerName || "Facebook User"; // Fallback to placeholder
    orderData.customer_phone = userData.customerPhone || "+15551234567"; // Fallback to placeholder

    // --- Item Details ---
    let items = [];
    // Example selectors - these will need to be updated based on actual Facebook Marketplace HTML
    const itemElements = document.querySelectorAll("._1g_5"); // This is a generic placeholder selector

    itemElements.forEach(itemEl => {
        const name = itemEl.querySelector("._3-94").innerText; // Placeholder
        const quantity = parseInt(itemEl.querySelector("._3-95").innerText.replace("x", "")); // Placeholder
        const priceText = itemEl.querySelector("._3-96").innerText; // Placeholder
        const price = parseFloat(priceText.replace(/[^0-9.-]+/g," "));

        if (name && quantity && price) {
            items.push({
                name: name,
                quantity: quantity,
                price: price
            });
        }
    });
    orderData.items = items;

    // --- Total Amount ---
    // Example selector - will need to be updated
    const totalAmountElement = document.querySelector("._3-97"); // Placeholder
    if (totalAmountElement) {
        const totalAmountText = totalAmountElement.innerText;
        orderData.total_amount = parseFloat(totalAmountText.replace(/[^0-9.-]+/g," "));
    } else {
        // Fallback: calculate total from items if total element not found
        orderData.total_amount = items.reduce((sum, item) => sum + (item.quantity * item.price), 0);
    }

    // --- Notes ---
    orderData.notes = "Order automatically detected from Facebook Marketplace.";

    return orderData;
}

// Send the extracted data to the background script
(async () => {
    const extractedData = await extractOrderData();
    if (extractedData.items && extractedData.items.length > 0 && extractedData.total_amount > 0) {
        console.log("Detected order data:", extractedData);
        chrome.runtime.sendMessage({ action: "sendOrderData", orderData: extractedData });
    } else {
        console.warn("No valid order data extracted. This might not be a confirmation page or selectors are incorrect.");
    }
})();

// This script runs on the Facebook Marketplace and WooCommerce confirmation pages.

async function extractFacebookOrderData() {
    const orderData = {};

    // --- Customer Information (using dummy data as it's not on the page) ---
    orderData.customer_name = "Facebook User";
    orderData.customer_phone = "+15551234567";

    // --- Item Details ---
    const items = [];
    const itemElements = document.querySelectorAll('.item');
    itemElements.forEach(itemEl => {
        const name = itemEl.querySelector('.item-name').innerText;
        const quantityText = itemEl.querySelector('.item-quantity').innerText;
        const quantity = parseInt(quantityText.replace('x', ''));
        const priceText = itemEl.querySelector('.item-price').innerText;
        const price = parseFloat(priceText.replace(/[^0-9.-]+/g,""));

        if (name && quantity && price) {
            items.push({ name, quantity, price });
        }
    });
    orderData.items = items;

    // --- Total Amount ---
    const totalAmountElement = document.querySelector('._3-97');
    if (totalAmountElement) {
        const totalAmountText = totalAmountElement.innerText;
        orderData.total_amount = parseFloat(totalAmountText.replace(/[^0-9.-]+/g,""));
    } else {
        orderData.total_amount = items.reduce((sum, item) => sum + (item.quantity * item.price), 0);
    }

    // --- Notes ---
    orderData.notes = "Order automatically detected from Facebook Marketplace.";

    return orderData;
}

async function extractWooCommerceOrderData() {
    // NOTE: This function has not been tested as the provided test file was for Facebook.
    // The selectors here are based on a standard WooCommerce installation, but may need to be adjusted.
    const orderData = {};

    // --- Customer Information ---
    // WooCommerce doesn't typically display the customer's name and phone on the confirmation page.
    // We'll rely on the data saved in the extension's options.
    const userData = await new Promise((resolve) => {
        chrome.storage.sync.get(['customerName', 'customerPhone'], (items) => {
            resolve(items);
        });
    });
    orderData.customer_name = userData.customerName || "WooCommerce User";
    orderData.customer_phone = userData.customerPhone || "+15551234567";

    // --- Item Details ---
    const items = [];
    const itemElements = document.querySelectorAll('.woocommerce-table--order-details-cart-item');
    itemElements.forEach(itemEl => {
        const name = itemEl.querySelector('.woocommerce-table__product-name a').innerText;
        const quantity = parseInt(itemEl.querySelector('.product-quantity').innerText.replace('×', ''));
        const priceText = itemEl.querySelector('.woocommerce-Price-amount.amount').innerText;
        const price = parseFloat(priceText.replace(/[^0-9.-]+/g,""));

        if (name && quantity && price) {
            items.push({ name, quantity, price });
        }
    });
    orderData.items = items;

    // --- Total Amount ---
    const totalAmountElement = document.querySelector('.woocommerce-Price-amount.amount');
    if (totalAmountElement) {
        const totalAmountText = totalAmountElement.innerText;
        orderData.total_amount = parseFloat(totalAmountText.replace(/[^0-9.-]+/g,""));
    } else {
        orderData.total_amount = items.reduce((sum, item) => sum + (item.quantity * item.price), 0);
    }

    // --- Notes ---
    orderData.notes = "Order automatically detected from WooCommerce.";

    return orderData;
}

// Main execution logic
(async () => {
    let extractedData;
    if (window.location.href.includes('facebook.com') || document.title.includes('Facebook Marketplace')) {
        extractedData = await extractFacebookOrderData();
    } else if (window.location.href.includes('/checkout/order-received/')) {
        extractedData = await extractWooCommerceOrderData();
    }

    if (extractedData && extractedData.items && extractedData.items.length > 0 && extractedData.total_amount > 0) {
        console.log("Detected order data:", extractedData);
        chrome.runtime.sendMessage({ action: "sendOrderData", orderData: extractedData });
    } else {
        console.warn("No valid order data extracted. This might not be a confirmation page or selectors are incorrect.");
    }
})();
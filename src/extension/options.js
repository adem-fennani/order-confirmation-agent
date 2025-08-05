function saveOptions() {
    const customerName = document.getElementById('customer_name').value;
    const customerPhone = document.getElementById('customer_phone').value;
    const apiKey = document.getElementById('api_key').value;
    const siteId = document.getElementById('site_id').value;

    chrome.storage.sync.set({
        customerName: customerName,
        customerPhone: customerPhone,
        apiKey: apiKey,
        siteId: siteId
    }, () => {
        const status = document.getElementById('status');
        status.textContent = 'Options saved.';
        setTimeout(() => {
            status.textContent = '';
        }, 1500);
    });
}

function restoreOptions() {
    chrome.storage.sync.get(['customerName', 'customerPhone', 'apiKey', 'siteId'], (items) => {
        document.getElementById('customer_name').value = items.customerName || '';
        document.getElementById('customer_phone').value = items.customerPhone || '';
        document.getElementById('api_key').value = items.apiKey || '';
        document.getElementById('site_id').value = items.siteId || '';
    });
}

document.addEventListener('DOMContentLoaded', restoreOptions);
document.getElementById('save').addEventListener('click', saveOptions);

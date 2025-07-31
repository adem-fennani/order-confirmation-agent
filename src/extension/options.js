function saveOptions() {
    const customerName = document.getElementById('customer_name').value;
    const customerPhone = document.getElementById('customer_phone').value;

    chrome.storage.sync.set({
        customerName: customerName,
        customerPhone: customerPhone
    }, () => {
        const status = document.getElementById('status');
        status.textContent = 'Options saved.';
        setTimeout(() => {
            status.textContent = '';
        }, 1500);
    });
}

function restoreOptions() {
    chrome.storage.sync.get(['customerName', 'customerPhone'], (items) => {
        document.getElementById('customer_name').value = items.customerName || '';
        document.getElementById('customer_phone').value = items.customerPhone || '';
    });
}

document.addEventListener('DOMContentLoaded', restoreOptions);
document.getElementById('save').addEventListener('click', saveOptions);

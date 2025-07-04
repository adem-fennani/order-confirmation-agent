const API_BASE = 'http://localhost:8000';
let currentOrderId = null;
let isLoading = false;

// DOM elements
const ordersList = document.getElementById('orders-list');
const chatMessages = document.getElementById('chat-messages');
const chatTitle = document.getElementById('chat-title');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const errorMessage = document.getElementById('error-message');

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    loadOrders();
    setupEventListeners();
    setupAddOrderForm();
});

function setupEventListeners() {
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendButton.addEventListener('click', sendMessage);
}

function setupAddOrderForm() {
    const showBtn = document.getElementById('show-add-order');
    const form = document.getElementById('add-order-form');
    const cancelBtn = document.getElementById('cancel-add-order');
    showBtn.addEventListener('click', function() {
        form.style.display = 'block';
        showBtn.style.display = 'none';
    });
    cancelBtn.addEventListener('click', function() {
        form.style.display = 'none';
        showBtn.style.display = 'block';
        form.reset && form.reset();
    });
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const name = document.getElementById('add-customer-name').value.trim();
        const phone = document.getElementById('add-customer-phone').value.trim();
        const itemsRaw = document.getElementById('add-items').value.trim();
        const total = parseFloat(document.getElementById('add-total-amount').value);
        const notes = document.getElementById('add-notes').value.trim();
        if (!name || !phone || !itemsRaw || isNaN(total)) {
            showError('Veuillez remplir tous les champs obligatoires');
            return;
        }
        // Parse items: format "Pizza x2 12.5; Cola x1 2.5"
        const items = itemsRaw.split(';').map(str => {
            const m = str.trim().match(/^(.+?) x(\d+) ([\d.]+)$/);
            if (!m) return null;
            return { name: m[1].trim(), quantity: parseInt(m[2]), price: parseFloat(m[3]) };
        }).filter(Boolean);
        if (items.length === 0) {
            showError('Format des articles invalide');
            return;
        }
        try {
            const resp = await fetch(`${API_BASE}/orders`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    customer_name: name,
                    customer_phone: phone,
                    items,
                    total_amount: total,
                    notes: notes || undefined
                })
            });
            if (!resp.ok) throw new Error('Erreur API');
            form.style.display = 'none';
            showBtn.style.display = 'block';
            form.reset && form.reset();
            loadOrders();
        } catch (err) {
            showError('Erreur lors de l\'ajout de la commande');
        }
    });
}

async function loadOrders() {
    try {
        showLoading(ordersList);
        const response = await fetch(`${API_BASE}/orders`);
        const data = await response.json();
        
        displayOrders(data.orders);
    } catch (error) {
        console.error('Error loading orders:', error);
        showError('Erreur lors du chargement des commandes');
    }
}

function displayOrders(orders) {
    if (orders.length === 0) {
        ordersList.innerHTML = '<div class="empty-state">Aucune commande trouvée</div>';
        return;
    }

    ordersList.innerHTML = orders.map(order => `
        <div class="order-card" data-order-id="${order.id}">
            <div class="order-header">
                <span class="order-id">${order.id}</span>
                <span class="order-status status-${order.status}">${order.status}</span>
            </div>
            <div class="customer-info">
                <div class="customer-name">${order.customer_name}</div>
                <div class="customer-phone">${order.customer_phone}</div>
            </div>
            <div class="order-items">
                ${order.items.map(item => `
                    <div>• ${item.name} x${item.quantity}</div>
                `).join('')}
            </div>
            <div class="order-total">${order.total_amount}€</div>
            <button class="start-confirmation" onclick="startConfirmation('${order.id}')">
                Démarrer confirmation
            </button>
            <button class="delete-order-btn" data-order-id="${order.id}" style="background:#ff5252;color:#fff;margin-top:8px;width:100%;border:none;border-radius:8px;padding:10px;font-weight:bold;cursor:pointer;">Supprimer</button>
        </div>
    `).join('');

    // Add click listeners to order cards
    document.querySelectorAll('.order-card').forEach(card => {
        card.addEventListener('click', function(e) {
            if (e.target.classList.contains('start-confirmation') || e.target.classList.contains('delete-order-btn')) {
                return; // Let the button handle this
            }
            selectOrder(this.dataset.orderId);
        });
    });

    // Add delete listeners
    document.querySelectorAll('.delete-order-btn').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.stopPropagation();
            const orderId = this.dataset.orderId;
            if (confirm('Voulez-vous vraiment supprimer cette commande ?')) {
                try {
                    const resp = await fetch(`${API_BASE}/orders/${orderId}`, { method: 'DELETE' });
                    if (!resp.ok) throw new Error('Erreur API');
                    loadOrders();
                    if (currentOrderId === orderId) {
                        chatMessages.innerHTML = `<div class="empty-state"><h3>Aucune conversation active</h3><p>Sélectionnez une commande dans la liste de gauche pour démarrer une confirmation.</p></div>`;
                        chatTitle.textContent = 'Sélectionnez une commande pour démarrer';
                        messageInput.disabled = true;
                        sendButton.disabled = true;
                    }
                } catch (err) {
                    showError('Erreur lors de la suppression de la commande');
                }
            }
        });
    });
}

function selectOrder(orderId) {
    currentOrderId = orderId;
    
    // Update UI
    document.querySelectorAll('.order-card').forEach(card => {
        card.classList.remove('selected');
    });
    document.querySelector(`[data-order-id="${orderId}"]`).classList.add('selected');
    
    chatTitle.textContent = `Commande ${orderId}`;
    
    // Load conversation if exists
    loadConversation(orderId);
    
    // Enable chat input
    messageInput.disabled = false;
    sendButton.disabled = false;
}

async function startConfirmation(orderId) {
    try {
        isLoading = true;
        sendButton.disabled = true;
        
        const response = await fetch(`${API_BASE}/orders/${orderId}/confirm`, {
            method: 'POST'
        });
        const data = await response.json();
        
        selectOrder(orderId);
        
        // Add agent's initial message
        addMessage(data.message, 'agent');
        
    } catch (error) {
        console.error('Error starting confirmation:', error);
        showError('Erreur lors du démarrage de la confirmation');
    } finally {
        isLoading = false;
        sendButton.disabled = false;
    }
}

async function loadConversation(orderId) {
    try {
        const response = await fetch(`${API_BASE}/orders/${orderId}/conversation`);
        
        if (response.ok) {
            const data = await response.json();
            displayConversation(data.conversation.messages);
        } else {
            // No conversation yet
            chatMessages.innerHTML = `
                <div class="empty-state">
                    <h3>Prêt à confirmer</h3>
                    <p>Cliquez sur "Démarrer confirmation" pour commencer la conversation avec le client.</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading conversation:', error);
    }
}

function displayConversation(messages) {
    chatMessages.innerHTML = '';
    
    messages.forEach(message => {
        addMessage(message.content, message.role === 'user' ? 'user' : 'agent');
    });
    
    scrollToBottom();
}

function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.innerHTML = `
        <div class="message-bubble">
            ${text}
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

async function sendMessage() {
    if (!currentOrderId || isLoading) return;
    
    const text = messageInput.value.trim();
    if (!text) return;
    
    try {
        isLoading = true;
        sendButton.disabled = true;
        
        // Add user message to UI
        addMessage(text, 'user');
        messageInput.value = '';
        
        // Send to API
        const response = await fetch(`${API_BASE}/orders/${currentOrderId}/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text })
        });
        
        const data = await response.json();
        
        // Add agent response
        addMessage(data.agent_response, 'agent');
        
    } catch (error) {
        console.error('Error sending message:', error);
        showError('Erreur lors de l\'envoi du message');
    } finally {
        isLoading = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showLoading(element) {
    element.innerHTML = '<div class="loading">Chargement...</div>';
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}
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
        </div>
    `).join('');

    // Add click listeners to order cards
    document.querySelectorAll('.order-card').forEach(card => {
        card.addEventListener('click', function(e) {
            if (e.target.classList.contains('start-confirmation')) {
                return; // Let the button handle this
            }
            selectOrder(this.dataset.orderId);
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
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

    // Twilio test button handler
    const testBtn = document.getElementById('twilio-test-btn');
    if (testBtn) {
        testBtn.addEventListener('click', async () => {
            try {
                const resp = await fetch(`${API_BASE}/test-sms`, { method: 'POST' });
                if (!resp.ok) throw new Error('API error');
                showSuccess('SMS envoyé !');
            } catch (err) {
                showError('Erreur envoi SMS');
            }
        });
    }

    // Prevent accidental form submission in chat input area
    document.querySelectorAll('.chat-input input, .chat-input button').forEach(el => {
        el.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
            }
        });
    });
});

function setupEventListeners() {
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendButton.addEventListener('click', function(e) {
        e.preventDefault();
        sendMessage();
    });
}

function setupAddOrderForm() {
    const showBtn = document.getElementById('show-add-order');
    const form = document.getElementById('add-order-form');
    const cancelBtn = document.getElementById('cancel-add-order');
    
    showBtn.addEventListener('click', function(e) {
        e.preventDefault();
        form.style.display = 'block';
        showBtn.style.display = 'none';
    });
    
    cancelBtn.addEventListener('click', function(e) {
        e.preventDefault();
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

    ordersList.innerHTML = orders.map(order => {
        // Translate status for display
        let statusLabel = order.status;
        if (statusLabel === "pending") statusLabel = "en attente";
        if (statusLabel === "confirmed") statusLabel = "confirmé";
        if (statusLabel === "cancelled") statusLabel = "annulé";
        return `
        <div class="order-card" data-order-id="${order.id}">
            <div class="order-header">
                <span class="order-id">${order.id}</span>
                <span class="order-status status-${order.status}">${statusLabel}</span>
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
            <div class="order-actions" style="flex-direction:column;gap:6px;">
                <button class="start-confirmation order-action-btn" type="button" style="width:100%;font-size:1rem;font-weight:700;" title="Démarrer conversation" data-order-id="${order.id}">
                    Démarrer conversation
                </button>
                <div style="display:flex;gap:8px;">
                    <button class="reset-conversation-btn order-action-btn" type="button" data-order-id="${order.id}" title="Réinitialiser">
                        <span>🔄</span>
                    </button>
                    <button class="update-order-btn order-action-btn" type="button" data-order-id="${order.id}" title="Mettre à jour">
                        <span>✏️</span>
                    </button>
                    <button class="delete-order-btn order-action-btn" type="button" data-order-id="${order.id}" title="Supprimer">
                        <span>🗑️</span>
                    </button>
                </div>
            </div>
        </div>
        `;
    }).join('');

    // Add click listeners to order cards
    document.querySelectorAll('.order-card').forEach(card => {
        card.addEventListener('click', function(e) {
            if (
                e.target.classList.contains('start-confirmation') ||
                e.target.classList.contains('delete-order-btn') ||
                e.target.classList.contains('update-order-btn') ||
                e.target.classList.contains('reset-conversation-btn') ||
                e.target.closest('button')
            ) {
                e.preventDefault();
                e.stopPropagation();
                return;
            }
            selectOrder(this.dataset.orderId);
        });
    });

    // Add start confirmation listeners
    document.querySelectorAll('.order-card .start-confirmation').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const orderId = this.dataset.orderId;
            startConfirmation(orderId);
        });
    });

    // Add delete listeners
    document.querySelectorAll('.delete-order-btn').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
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

    // Add update listeners
    document.querySelectorAll('.update-order-btn').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            e.stopPropagation();
            const orderId = this.dataset.orderId;
            
            // Fetch order details
            let order = null;
            try {
                const resp = await fetch(`${API_BASE}/orders/${orderId}`);
                if (!resp.ok) throw new Error('Erreur API');
                const data = await resp.json();
                order = data.order;
            } catch (err) {
                showError('Erreur lors du chargement de la commande');
                return;
            }
            
            // Show prompt for each field
            const customer_name = prompt('Nom du client:', order.customer_name);
            if (customer_name === null) return;
            const customer_phone = prompt('Téléphone:', order.customer_phone);
            if (customer_phone === null) return;
            const itemsRaw = prompt('Articles (ex: Pizza x2 12.5; Cola x1 2.5):', order.items.map(i => `${i.name} x${i.quantity} ${i.price}`).join('; '));
            if (itemsRaw === null) return;
            const total_amount = prompt('Total (€):', order.total_amount);
            if (total_amount === null) return;
            const notes = prompt('Notes (optionnel):', order.notes || '');
            if (notes === null) return;
            
            // Parse items
            const items = itemsRaw.split(';').map(str => {
                const m = str.trim().match(/^(.+?) x(\d+) ([\d.]+)$/);
                if (!m) return null;
                return { name: m[1].trim(), quantity: parseInt(m[2]), price: parseFloat(m[3]) };
            }).filter(Boolean);
            
            if (items.length === 0) {
                showError('Format des articles invalide');
                return;
            }
            
            // Send update
            try {
                const resp = await fetch(`${API_BASE}/orders/${orderId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        customer_name,
                        customer_phone,
                        items,
                        total_amount: parseFloat(total_amount),
                        notes: notes || undefined
                    })
                });
                if (!resp.ok) throw new Error('Erreur API');
                loadOrders();
            } catch (err) {
                showError('Erreur lors de la mise à jour de la commande');
            }
        });
    });

    // In the reset button click handler:
    document.querySelectorAll('.reset-conversation-btn').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            e.stopPropagation();
            const orderId = this.dataset.orderId;
            if (confirm('Voulez-vous vraiment réinitialiser cette conversation ?')) {
                try {
                    isLoading = true;
                    btn.disabled = true;
                    
                    // Clear the chat UI immediately
                    if (currentOrderId === orderId) {
                        chatMessages.innerHTML = '<div class="loading">Réinitialisation...</div>';
                    }
                    
                    const resp = await fetch(`${API_BASE}/orders/${orderId}/reset`, { 
                        method: 'POST' 
                    });
                    
                    if (!resp.ok) {
                        const error = await resp.json();
                        throw new Error(error.detail || 'Erreur API');
                    }
                    
                    const data = await resp.json();
                    
                    // If this is the currently selected order, update the chat
                    if (currentOrderId === orderId) {
                        chatMessages.innerHTML = '';
                        addMessage(data.user_message, 'user');
                        addMessage(data.agent_response, 'agent');
                        
                        // Update status visually to "en attente"
                        const orderCard = document.querySelector(`[data-order-id="${orderId}"]`);
                        if (orderCard) {
                            const statusElement = orderCard.querySelector('.order-status');
                            statusElement.textContent = "en attente";
                            statusElement.className = "order-status status-pending";
                        }
                    }
                    
                    showSuccess('Conversation réinitialisée avec succès');
                } catch (err) {
                    console.error('Reset error:', err);
                    showError(err.message || 'Erreur lors de la réinitialisation');
                } finally {
                    isLoading = false;
                    btn.disabled = false;
                }
            }
        });
    });
}

async function sendMessageAutomatically(message) {
    if (!currentOrderId || isLoading) return;
    
    try {
        isLoading = true;
        sendButton.disabled = true;
        
        // Add user message to UI
        addMessage(message, 'user');
        
        // Send to API
        const response = await fetch(`${API_BASE}/orders/${currentOrderId}/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: message })
        });
        
        const data = await response.json();
        
        // Add agent response
        addMessage(data.agent_response, 'agent');
        
    } catch (error) {
        console.error('Error sending automatic message:', error);
    } finally {
        isLoading = false;
        sendButton.disabled = false;
    }
}

async function sendInitialMessage(orderId) {
    try {
        const response = await fetch(`${API_BASE}/orders/${orderId}/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: "Bonjour" })
        });
        const data = await response.json();
        addMessage(data.agent_response, 'agent');
    } catch (error) {
        console.error('Error sending initial message:', error);
    }
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
        
        // Refresh orders if conversation reached final confirmation
        if (data.agent_response.includes("confirmée") || 
            data.agent_response.includes("annulée")) {
            // Small delay for better UX
            setTimeout(() => {
                loadOrders();
                
                // Update current order card status visually
                const orderCard = document.querySelector(`[data-order-id="${currentOrderId}"]`);
                if (orderCard) {
                    const statusElement = orderCard.querySelector('.order-status');
                    if (data.agent_response.includes("confirmée")) {
                        statusElement.textContent = "confirmé";  // Changed to French
                        statusElement.className = "order-status status-confirmed";
                    } else if (data.agent_response.includes("annulée")) {
                        statusElement.textContent = "annulé";    // Changed to French
                        statusElement.className = "order-status status-cancelled";
                    }
                }
            }, 500);
        }
        
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
    const errorElement = document.getElementById('error-message');
    const successElement = document.getElementById('success-message');
    
    errorElement.textContent = message;
    errorElement.style.display = 'block';
    successElement.style.display = 'none';
    
    setTimeout(() => {
        errorElement.style.display = 'none';
    }, 5000);
}

function showSuccess(message) {
    const errorElement = document.getElementById('error-message');
    const successElement = document.getElementById('success-message');
    
    successElement.textContent = message;
    successElement.style.display = 'block';
    errorElement.style.display = 'none';
    
    setTimeout(() => {
        successElement.style.display = 'none';
    }, 5000);
}
document.addEventListener('DOMContentLoaded', () => {
    const agent = new Agent();
});

class Agent {
    constructor() {
        this.mode = 'auto'; // 'auto' or 'manual'
        this.orders = [];
        this.selectedOrder = null;
        this.currentPage = 1;
        this.itemsPerPage = 3;
        this.totalOrders = 0;
        this.init();
    }

    init() {
        // this.initModeSelector();
        this.initEventListeners();
        this.loadOrders();
    }

    initModeSelector() {
        const autoBtn = document.getElementById('mode-auto');
        const manualBtn = document.getElementById('mode-manual');
        const addOrderForm = document.getElementById('add-order-form');

        autoBtn.addEventListener('click', () => {
            this.mode = 'auto';
            autoBtn.classList.add('active');
            manualBtn.classList.remove('active');
            addOrderForm.style.display = 'none';
        });

        manualBtn.addEventListener('click', () => {
            this.mode = 'manual';
            manualBtn.classList.add('active');
            autoBtn.classList.remove('active');
            addOrderForm.style.display = 'block';
        });
    }

    initEventListeners() {
        document.getElementById('add-order-form').addEventListener('submit', this.addOrder.bind(this));
        document.getElementById('chat-input').addEventListener('submit', this.sendMessage.bind(this));
        document.getElementById('prev-page').addEventListener('click', this.prevPage.bind(this));
        document.getElementById('next-page').addEventListener('click', this.nextPage.bind(this));
    }

    async loadOrders() {
        const skip = (this.currentPage - 1) * this.itemsPerPage;
        try {
            const response = await fetch(`/orders?skip=${skip}&limit=${this.itemsPerPage}`);
            const data = await response.json();
            this.orders = data.orders;
            this.totalOrders = data.total_count;
            this.renderOrders();
            this.renderPagination();
        } catch (error) {
            console.error('Error loading orders:', error);
        }
    }

    renderOrders() {
        const ordersList = document.getElementById('orders-list');
        ordersList.innerHTML = ''; // Clear existing orders

        this.orders.forEach(order => {
            const orderCard = this.createOrderCard(order);
            ordersList.appendChild(orderCard);
        });
    }

    renderPagination() {
        const pageInfo = document.getElementById('page-info');
        const totalPages = Math.ceil(this.totalOrders / this.itemsPerPage);
        pageInfo.textContent = `Page ${this.currentPage} of ${totalPages}`;

        document.getElementById('prev-page').disabled = this.currentPage === 1;
        document.getElementById('next-page').disabled = this.currentPage === totalPages;
    }

    prevPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.loadOrders();
        }
    }

    nextPage() {
        const totalPages = Math.ceil(this.totalOrders / this.itemsPerPage);
        if (this.currentPage < totalPages) {
            this.currentPage++;
            this.loadOrders();
        }
    }

    createOrderCard(order) {
        const card = document.createElement('div');
        card.className = 'order-card';
        card.dataset.orderId = order.id;
        card.innerHTML = `
            <div class="order-header">
                <div class="order-id">Order #${order.id}</div>
                <div class="order-status status-${order.status.toLowerCase()}">${order.status}</div>
            </div>
            <div class="customer-info">
                <div class="customer-name">${order.customer_name}</div>
                <div class="customer-phone">${order.customer_phone}</div>
            </div>
            <div class="order-total">${order.total_amount.toFixed(2)}</div>
        `;
        card.addEventListener('click', () => this.selectOrder(order.id));
        return card;
    }

    selectOrder(orderId) {
        this.selectedOrder = this.orders.find(o => o.id === orderId);
        this.renderSelectedOrder();
    }

    renderSelectedOrder() {
        // Highlight selected order card
        document.querySelectorAll('.order-card').forEach(card => {
            card.classList.toggle('selected', card.dataset.orderId == this.selectedOrder.id);
        });

        const chatMessages = document.querySelector('.chat-messages');
        chatMessages.innerHTML = ''; // Clear messages

        this.selectedOrder.conversation.forEach(msg => {
            const messageEl = this.createMessageElement(msg);
            chatMessages.appendChild(messageEl);
        });
    }

    createMessageElement(message) {
        const el = document.createElement('div');
        el.className = `message ${message.role}`;
        el.innerHTML = `<div class="message-bubble">${message.content}</div>`;
        return el;
    }

    async addOrder(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        const orderData = Object.fromEntries(formData.entries());

        try {
            const response = await fetch('/api/orders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(orderData)
            });
            const newOrder = await response.json();
            this.orders.push(newOrder);
            this.renderOrders();
            event.target.reset();
        } catch (error) {
            console.error('Error adding order:', error);
        }
    }

    async sendMessage(event) {
        event.preventDefault();
        const input = event.target.querySelector('input');
        const content = input.value.trim();
        if (!content || !this.selectedOrder) return;

        const message = { role: 'user', content };
        this.selectedOrder.conversation.push(message);
        this.renderSelectedOrder();
        input.value = '';

        try {
            await fetch(`/api/orders/${this.selectedOrder.id}/conversation`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(message)
            });
        } catch (error) {
            console.error('Error sending message:', error);
        }
    }
}
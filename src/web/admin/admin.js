class AdminApp {
    constructor() {
        this.loginForm = document.getElementById('login-form');
        this.loginContainer = document.getElementById('login-container');
        this.dashboardContainer = document.getElementById('dashboard-container');
        this.logoutButton = document.getElementById('logout-button');
        this.ordersTableBody = document.querySelector('#orders-table tbody');
        this.modal = document.getElementById('order-details-modal');
        this.modalContent = document.getElementById('modal-order-details');
        this.closeButton = document.querySelector('.close-button');

        this.loginForm.addEventListener('submit', this.handleLogin.bind(this));
        this.logoutButton.addEventListener('click', this.handleLogout.bind(this));
        this.closeButton.addEventListener('click', () => this.modal.style.display = 'none');
        this.ordersTableBody.addEventListener('click', this.handleOrderClick.bind(this));

        this.checkAuth();
    }

    async checkAuth() {
        const token = localStorage.getItem('token');
        if (token) {
            this.showDashboard();
            this.fetchOrders();
            this.fetchApiKey();
        } else {
            this.showLogin();
        }
    }

    async handleLogin(event) {
        event.preventDefault();
        const username = event.target.username.value;
        const password = event.target.password.value;

        try {
            const response = await fetch('/api/business/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `grant_type=password&username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('token', data.token);
                this.showDashboard();
                this.fetchOrders();
                this.fetchApiKey();
            } else {
                alert('Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            alert('An error occurred during login.');
        }
    }

    handleLogout() {
        localStorage.removeItem('token');
        this.showLogin();
    }

    showLogin() {
        this.loginContainer.style.display = 'block';
        this.dashboardContainer.style.display = 'none';
    }

    showDashboard() {
        this.loginContainer.style.display = 'none';
        this.dashboardContainer.style.display = 'block';
    }

    async fetchOrders() {
        const token = localStorage.getItem('token');
        try {
            const response = await fetch('/api/business/orders', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const orders = await response.json();
                this.renderOrders(orders);
            } else {
                console.error('Failed to fetch orders');
            }
        } catch (error) {
            console.error('Error fetching orders:', error);
        }
    }

    renderOrders(orders) {
        this.ordersTableBody.innerHTML = '';
        orders.forEach(order => {
            const row = document.createElement('tr');
            row.dataset.orderId = order.id;
            row.innerHTML = `
                <td>${order.id}</td>
                <td>${order.customer_name}</td>
                <td>${order.total_amount}</td>
                <td>${order.site_url}</td>
            `;
            this.ordersTableBody.appendChild(row);
        });
    }

    async handleOrderClick(event) {
        const orderId = event.target.closest('tr').dataset.orderId;
        if (!orderId) return;

        const token = localStorage.getItem('token');
        try {
            const response = await fetch(`/api/business/orders/${orderId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const order = await response.json();
                this.showOrderDetails(order);
            } else {
                console.error('Failed to fetch order details');
            }
        } catch (error) {
            console.error('Error fetching order details:', error);
        }
    }

    showOrderDetails(order) {
        this.modalContent.innerHTML = `
            <p><strong>Order ID:</strong> ${order.id}</p>
            <p><strong>Customer:</strong> ${order.customer_name}</p>
            <p><strong>Phone:</strong> ${order.customer_phone}</p>
            <p><strong>Total:</strong> ${order.total_amount}</p>
            <p><strong>Site:</strong> ${order.site_url}</p>
            <p><strong>Status:</strong> ${order.status}</p>
            <hr>
            <h3>Conversation:</h3>
            <ul>
                ${order.conversation.map(msg => `<li><strong>${msg.role}:</strong> ${msg.content}</li>`).join('')}
            </ul>
        `;
        this.modal.style.display = 'block';
    }

    async fetchApiKey() {
        const token = localStorage.getItem('token');
        try {
            const response = await fetch('/api/business/api-key', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                this.displayApiKey(data.api_key);
            } else {
                console.error('Failed to fetch API key');
            }
        } catch (error) {
            console.error('Error fetching API key:', error);
        }
    }

    displayApiKey(apiKey) {
        const apiKeyElement = document.createElement('div');
        apiKeyElement.innerHTML = `
            <h2>API Key</h2>
            <input type="text" value="${apiKey}" readonly>
            <button id="copy-api-key">Copy</button>
        `;
        this.dashboardContainer.appendChild(apiKeyElement);

        document.getElementById('copy-api-key').addEventListener('click', () => {
            navigator.clipboard.writeText(apiKey);
            alert('API Key copied to clipboard');
        });
    }
}

new AdminApp();
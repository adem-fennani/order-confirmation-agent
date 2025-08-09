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
        this.apiKeyInput = document.getElementById('api-key-input');
        this.copyButton = document.getElementById('copy-api-key');
        this.apiKeySection = document.getElementById('api-key-section');
        this.dashboardUsernameElement = document.getElementById('dashboard-username');
        this.passwordField = document.getElementById('password');
        this.passwordToggle = document.getElementById('password-toggle');

        this.bindEvents();
        this.showLogin(); // Always show login page first
    }

    bindEvents() {
        this.loginForm.addEventListener('submit', this.handleLogin.bind(this));
        this.logoutButton.addEventListener('click', this.handleLogout.bind(this));
        this.closeButton.addEventListener('click', () => this.modal.style.display = 'none');
        this.ordersTableBody.addEventListener('click', this.handleOrderClick.bind(this));
        this.copyButton.addEventListener('click', this.copyApiKey.bind(this));
        this.passwordToggle.addEventListener('click', this.togglePasswordVisibility.bind(this));
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
                this.showDashboard(data.username);
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

    async handleLogout() {
        try {
            const response = await fetch('/api/business/logout', { method: 'POST' });
            if (response.ok) {
                this.showLogin();
            } else {
                alert('Logout failed');
            }
        } catch (error) {
            console.error('Logout error:', error);
            alert('An error occurred during logout.');
        }
    }

    showLogin() {
        this.loginContainer.style.display = 'block';
        this.dashboardContainer.style.display = 'none';
    }

    showDashboard(username) {
        this.loginContainer.style.display = 'none';
        this.dashboardContainer.style.display = 'block';
        if (username) {
            this.dashboardUsernameElement.textContent = `Welcome, ${username}`;
        }
    }

    async fetchOrders() {
        try {
            const response = await fetch('/api/business/orders');

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
            const formattedAmount = parseFloat(order.total_amount).toFixed(3);
            row.innerHTML = `
                <td>${order.id}</td>
                <td>${order.customer_name}</td>
                <td>${formattedAmount}</td>
                <td>${order.site_url}</td>
                <td><span class="status-badge">${order.status}</span></td>
            `;
            this.ordersTableBody.appendChild(row);
        });
    }

    async handleOrderClick(event) {
        const orderId = event.target.closest('tr').dataset.orderId;
        if (!orderId) return;

        try {
            const response = await fetch(`/api/business/orders/${orderId}`);

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
        try {
            const response = await fetch('/api/business/api-key');

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
        this.apiKeyInput.value = apiKey;
        this.apiKeySection.style.display = 'block';
    }

    async copyApiKey() {
        try {
            await navigator.clipboard.writeText(this.apiKeyInput.value);
            alert('API Key copied to clipboard!');
        } catch (err) {
            console.error('Failed to copy API key:', err);
            alert('Failed to copy API Key.');
        }
    }

    togglePasswordVisibility() {
        if (this.passwordField.type === 'password') {
            this.passwordField.type = 'text';
            this.passwordToggle.textContent = '🙈'; // Closed eye
        } else {
            this.passwordField.type = 'password';
            this.passwordToggle.textContent = '👁️'; // Open eye
        }
    }
}

new AdminApp();
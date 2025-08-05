class AdminApp {
    constructor() {
        this.loginForm = document.getElementById('login-form');
        this.loginContainer = document.getElementById('login-container');
        this.dashboardContainer = document.getElementById('dashboard-container');
        this.logoutButton = document.getElementById('logout-button');
        this.ordersTableBody = document.querySelector('#orders-table tbody');

        this.loginForm.addEventListener('submit', this.handleLogin.bind(this));
        this.logoutButton.addEventListener('click', this.handleLogout.bind(this));

        this.checkAuth();
    }

    async checkAuth() {
        const token = localStorage.getItem('token');
        if (token) {
            this.showDashboard();
            this.fetchOrders();
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
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('token', data.token);
                this.showDashboard();
                this.fetchOrders();
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
            row.innerHTML = `
                <td>${order.id}</td>
                <td>${order.customer_name}</td>
                <td>${order.total_amount}</td>
                <td>${order.site_url}</td>
            `;
            this.ordersTableBody.appendChild(row);
        });
    }
}

new AdminApp();

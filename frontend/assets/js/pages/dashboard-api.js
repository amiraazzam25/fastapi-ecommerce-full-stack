(function () {
    "use strict";

    const TOKEN_KEY = "mnu_access_token";
    const API_BASE_KEY = "mnu_api_base";
    const DEFAULT_API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";
    const API_BASE = (window.MNU_API_BASE || localStorage.getItem(API_BASE_KEY) || DEFAULT_API_BASE).replace(/\/$/, "");
    const AUTH_URL = "auth-gate";
    const USER_HOME_URL = "home";

    const state = {
        users: [],
        categories: [],
        products: [],
        orders: [],
        productStock: new Map(),
        currentUser: null,
        currentRole: null,
        usersRestricted: false,
        ordersRestricted: false,
        showAllOrders: false,
    };

    const $ = (selector) => document.querySelector(selector);

    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function setToken(token) {
        localStorage.setItem(TOKEN_KEY, token);
    }

    function clearToken() {
        localStorage.removeItem(TOKEN_KEY);
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatNumber(value) {
        return Number.isFinite(Number(value)) ? Number(value).toLocaleString() : "--";
    }

    function formatMoney(value) {
        const amount = Number(value || 0);
        return amount.toLocaleString(undefined, { style: "currency", currency: "USD" });
    }

    function endpoint(path) {
        return `${API_BASE}${path}`;
    }

    function getErrorMessage(payload, fallback) {
        if (!payload) return fallback;
        if (Array.isArray(payload.detail)) {
            return payload.detail.map((item) => item.msg || JSON.stringify(item)).join(", ");
        }
        return payload.detail || payload.message || payload.messege || fallback;
    }

    async function api(path, options = {}) {
        const { auth = true, json, ...fetchOptions } = options;
        const headers = new Headers(fetchOptions.headers || {});
        const token = getToken();

        if (auth && token) {
            headers.set("Authorization", `Bearer ${token}`);
        }

        if (json !== undefined) {
            headers.set("Content-Type", "application/json");
            fetchOptions.body = JSON.stringify(json);
        }

        const response = await fetch(endpoint(path), { ...fetchOptions, headers });
        const contentType = response.headers.get("content-type") || "";
        const payload = contentType.includes("application/json") ? await response.json() : await response.text();

        if (!response.ok) {
            const error = new Error(getErrorMessage(payload, `Request failed with ${response.status}`));
            error.status = response.status;
            throw error;
        }

        return payload;
    }

    async function safeApi(path, options = {}) {
        const { notFoundValue = null, ...requestOptions } = options;
        try {
            return await api(path, requestOptions);
        } catch (error) {
            if (error.status === 404) {
                return notFoundValue;
            }
            if (error.status === 401 || error.status === 403) {
                return null;
            }
            throw error;
        }
    }

    async function safeProductPages(path, options = {}) {
        try {
            return await fetchProductPages(path, options);
        } catch (error) {
            if (error.status === 404) return [];
            if (error.status === 401 || error.status === 403) return null;
            throw error;
        }
    }

    async function fetchProductPages(path, options = {}) {
        const all = [];
        for (let page = 1; page <= 25; page += 1) {
            const separator = path.includes("?") ? "&" : "?";
            const batch = await api(`${path}${separator}page=${page}&page_size=100`, options);
            all.push(...batch);
            if (batch.length < 100) break;
        }
        return all;
    }

    function showAlert(message, type = "info") {
        const alert = $("#dashboardAlert");
        if (!alert) return;
        alert.className = `alert alert-${type} mt-3 mb-0`;
        alert.textContent = message;
    }

    function hideAlert() {
        const alert = $("#dashboardAlert");
        if (!alert) return;
        alert.className = "alert d-none mt-3 mb-0";
        alert.textContent = "";
    }

    function setBusy(button, busy, busyText) {
        if (!button) return;
        if (busy) {
            button.dataset.originalHtml = button.innerHTML;
            button.disabled = true;
            button.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>${busyText || "Loading"}`;
            return;
        }
        button.disabled = false;
        if (button.dataset.originalHtml) {
            button.innerHTML = button.dataset.originalHtml;
            delete button.dataset.originalHtml;
        }
    }

    function setText(selector, value) {
        const element = $(selector);
        if (element) element.textContent = value;
    }

    function setTableLoading(selector, columns) {
        const table = $(selector);
        if (!table) return;
        table.innerHTML = `<tr><td colspan="${columns}" class="text-center text-muted py-4">Loading...</td></tr>`;
    }

    function emptyRow(columns, message) {
        return `<tr><td colspan="${columns}" class="text-center text-muted py-4">${escapeHtml(message)}</td></tr>`;
    }

    function categoryName(categoryId) {
        const category = state.categories.find((item) => Number(item.id) === Number(categoryId));
        return category ? category.name : `Category #${categoryId || "--"}`;
    }

    function productName(productId) {
        const product = state.products.find((item) => Number(item.id) === Number(productId));
        return product ? product.name : `Product #${productId}`;
    }

    function userName(userId) {
        const user = state.users.find((item) => Number(item.id) === Number(userId));
        return user ? user.username : `User #${userId}`;
    }

    function stockBadge(product) {
        const stockCount = state.productStock.get(Number(product.id));
        const hasCount = stockCount !== undefined;
        const inStock = hasCount ? stockCount > 0 : product.stock === "in-stock";
        const text = hasCount
            ? `${inStock ? "In Stock" : "Out of Stock"} (${stockCount})`
            : (inStock ? "In Stock" : "Out of Stock");
        const tone = inStock ? "success" : "danger";
        return `<span class="badge bg-${tone}-subtle text-${tone}">${text}</span>`;
    }

    function orderStatusBadge(status) {
        const normalized = String(status || "pending").toLowerCase();
        if (normalized === "shipped") {
            return '<span class="badge bg-success-subtle text-success p-1"><i class="ti ti-truck me-1"></i>Shipped</span>';
        }
        if (normalized === "canceled" || normalized === "cancelled") {
            return '<span class="badge bg-danger-subtle text-danger p-1"><i class="ti ti-x me-1"></i>Cancelled</span>';
        }
        return '<span class="badge bg-warning-subtle text-warning p-1"><i class="ti ti-loader me-1"></i>Pending</span>';
    }

    function paymentBadge(status) {
        const canceled = String(status || "").toLowerCase().startsWith("cancel");
        return canceled
            ? '<span class="badge text-danger border border-danger-subtle fs-11 p-1">Unpaid</span>'
            : '<span class="badge text-success border border-success-subtle fs-11 p-1">Paid</span>';
    }

    function populateCategorySelects() {
        const options = state.categories.length
            ? state.categories.map((category) => `<option value="${category.id}">${escapeHtml(category.name)}</option>`).join("")
            : '<option value="">No categories</option>';

        ["#productCatInput", "#editProductCat"].forEach((selector) => {
            const select = $(selector);
            if (select) select.innerHTML = options;
        });
    }

    function renderCounts() {
        setText("#totalCategoriesCount", formatNumber(state.categories.length));
        setText("#totalProductsCount", formatNumber(state.products.length));
        setText("#totalUsersCount", state.usersRestricted ? "--" : formatNumber(state.users.length));
        setText("#totalOrdersCount", state.ordersRestricted ? "--" : formatNumber(state.orders.length));
    }

    function renderCategories() {
        const tbody = $("#categoriesTableBody");
        if (!tbody) return;

        if (!state.categories.length) {
            tbody.innerHTML = emptyRow(3, "No categories found.");
            return;
        }

        tbody.innerHTML = state.categories.map((category) => `
            <tr>
                <td class="fw-semibold">${escapeHtml(category.name)}</td>
                <td class="text-muted">${escapeHtml(category.description || "--")}</td>
                <td class="text-center">
                    <div class="d-flex gap-1 justify-content-center">
                        <button type="button" class="btn btn-soft-info btn-sm btn-icon rounded-circle" data-action="edit-category" data-id="${category.id}" title="Edit category"><i class="ti ti-edit"></i></button>
                        <button type="button" class="btn btn-soft-danger btn-sm btn-icon rounded-circle" data-action="delete-category" data-id="${category.id}" title="Delete category"><i class="ti ti-trash"></i></button>
                    </div>
                </td>
            </tr>
        `).join("");
    }

    function renderUsers() {
        const tbody = $("#usersTableBody");
        if (!tbody) return;

        if (!getToken()) {
            tbody.innerHTML = emptyRow(4, "Login to load users.");
            return;
        }

        if (state.usersRestricted) {
            tbody.innerHTML = emptyRow(4, "Admin token is required to load users.");
            return;
        }

        if (!state.users.length) {
            tbody.innerHTML = emptyRow(4, "No users found.");
            return;
        }

        tbody.innerHTML = state.users.map((user, index) => {
            const isCurrentUser = state.currentUser && Number(state.currentUser.id) === Number(user.id);
            const role = state.currentRole && Number(state.currentRole.user_id) === Number(user.id) ? state.currentRole.role : "user";
            const roleTone = role === "admin" ? "primary" : "secondary";
            const editDisabled = isCurrentUser ? "" : "disabled";
            const editTitle = isCurrentUser ? "Edit user" : "Only the logged-in user can be edited from this API";
            const avatarNumber = (index % 9) + 1;

            return `
                <tr>
                    <td>
                        <div class="d-flex align-items-center">
                            <img src="assets/images/users/avatar-${avatarNumber}.jpg" alt="" class="rounded-circle avatar-sm me-2">
                            <h5 class="m-0 fs-14">${escapeHtml(user.username)}</h5>
                        </div>
                    </td>
                    <td>${escapeHtml(user.email)}</td>
                    <td><span class="badge bg-${roleTone}-subtle text-${roleTone}">${role === "admin" ? "Admin" : "Customer"}</span></td>
                    <td class="text-center">
                        <div class="d-flex gap-2 justify-content-center">
                            <button type="button" class="btn btn-soft-info btn-sm btn-icon rounded-circle" data-action="edit-user" data-id="${user.id}" title="${editTitle}" ${editDisabled}><i class="ti ti-edit"></i></button>
                            <button type="button" class="btn btn-soft-danger btn-sm btn-icon rounded-circle" data-action="delete-user" data-id="${user.id}"><i class="ti ti-trash"></i></button>
                        </div>
                    </td>
                </tr>
            `;
        }).join("");
    }

    function renderProducts() {
        const tbody = $("#productsTableBody");
        if (!tbody) return;

        if (!state.products.length) {
            tbody.innerHTML = emptyRow(5, "No products found.");
            return;
        }

        tbody.innerHTML = state.products.map((product) => `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="avatar-sm bg-light rounded d-flex align-items-center justify-content-center me-2">
                            <i class="ti ti-package fs-20 text-muted"></i>
                        </div>
                        <h5 class="m-0 fs-14">${escapeHtml(product.name)}</h5>
                    </div>
                </td>
                <td>${escapeHtml(categoryName(product.category_id))}</td>
                <td>${formatMoney(product.price)}</td>
                <td>${stockBadge(product)}</td>
                <td class="text-center">
                    <div class="d-flex gap-2 justify-content-center">
                        <button type="button" class="btn btn-soft-info btn-sm btn-icon rounded-circle" data-action="edit-product" data-id="${product.id}"><i class="ti ti-edit"></i></button>
                        <button type="button" class="btn btn-soft-danger btn-sm btn-icon rounded-circle" data-action="delete-product" data-id="${product.id}"><i class="ti ti-trash"></i></button>
                    </div>
                </td>
            </tr>
        `).join("");
    }

    function renderOrders() {
        const tbody = $("#ordersTableBody");
        if (!tbody) return;
        const viewAllButton = $("#viewAllOrdersBtn");
        if (viewAllButton) {
            viewAllButton.textContent = state.showAllOrders ? "Pending Only" : "View All";
        }

        if (!getToken()) {
            tbody.innerHTML = emptyRow(7, "Login to load orders.");
            return;
        }

        if (state.ordersRestricted) {
            tbody.innerHTML = emptyRow(7, "Admin token is required to load orders.");
            return;
        }

        const sortedOrders = [...state.orders].sort((first, second) => Number(first.id) - Number(second.id));
        const visibleOrders = state.showAllOrders
            ? sortedOrders
            : sortedOrders.filter((order) => String(order.status || "pending").toLowerCase() === "pending");

        if (!visibleOrders.length) {
            tbody.innerHTML = emptyRow(7, state.showAllOrders ? "No orders found." : "No pending orders found.");
            return;
        }

        tbody.innerHTML = visibleOrders.map((order, index) => {
            const status = String(order.status || "pending").toLowerCase();
            const canChange = status === "pending";
            const products = (order.items || [])
                .map((item) => `${escapeHtml(productName(item.product_id))} x ${escapeHtml(item.quantity)}`)
                .join(", ") || "--";
            const avatarNumber = ((index + 4) % 9) + 1;

            return `
                <tr>
                    <td><a href="#" class="text-muted fw-medium">#ORD-${escapeHtml(order.id)}</a></td>
                    <td>
                        <div class="d-flex align-items-center">
                            <img src="assets/images/users/avatar-${avatarNumber}.jpg" alt="" class="rounded-circle avatar-xs me-2">
                            <h5 class="m-0 fs-14">${escapeHtml(userName(order.user_id))}</h5>
                        </div>
                    </td>
                    <td>${products}</td>
                    <td>${formatMoney(order.total_price)}</td>
                    <td>${paymentBadge(status)}</td>
                    <td>${orderStatusBadge(status)}</td>
                    <td class="text-center">
                        <div class="d-flex gap-2 justify-content-center">
                            <button class="btn btn-soft-success btn-sm" data-action="ship-order" data-id="${order.id}" ${canChange ? "" : "disabled"}><i class="ti ti-truck me-1"></i> Ship</button>
                            <button class="btn btn-soft-danger btn-sm" data-action="cancel-order" data-id="${order.id}" ${canChange ? "" : "disabled"}><i class="ti ti-x me-1"></i> Cancel</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join("");
    }

    function renderAll() {
        renderCounts();
        renderCategories();
        renderUsers();
        renderProducts();
        renderOrders();
    }

    async function loadDashboard() {
        const refreshButton = $("#refreshDashboardBtn");
        setBusy(refreshButton, true, "Refresh");
        hideAlert();
        setTableLoading("#usersTableBody", 4);
        setTableLoading("#categoriesTableBody", 3);
        setTableLoading("#productsTableBody", 5);
        setTableLoading("#ordersTableBody", 7);

        state.usersRestricted = false;
        state.ordersRestricted = false;
        state.productStock = new Map();

        try {
            const [categories, products] = await Promise.all([
                api("/api/v1/categories/getall", { auth: false }),
                fetchProductPages("/api/v1/products", { auth: false }),
            ]);

            state.categories = categories || [];
            state.products = products || [];
            populateCategorySelects();

            if (getToken()) {
                const [currentUser, currentRole] = await Promise.all([
                    safeApi("/api/v1/users/me"),
                    safeApi("/api/v1/users/me/role"),
                ]);

                state.currentUser = currentUser;
                state.currentRole = currentRole;

                if (!currentUser || !currentRole) {
                    clearToken();
                    window.location.href = AUTH_URL;
                    return;
                }

                if (currentRole.role !== "admin") {
                    window.location.href = USER_HOME_URL;
                    return;
                }

                if (currentUser) {
                    setText("#dashboardUserName", currentUser.username);
                }

                const [users, orders, stockRows] = await Promise.all([
                    safeApi("/api/v1/users/"),
                    safeApi("/api/v1/orders/get_all_orders", { notFoundValue: [] }),
                    safeProductPages("/api/v1/products/admin/stock"),
                ]);

                state.usersRestricted = users === null;
                state.ordersRestricted = orders === null;
                state.users = users || [];
                state.orders = orders || [];

                if (Array.isArray(stockRows)) {
                    state.productStock = new Map(stockRows.map((product) => [Number(product.id), product.stock]));
                }

                if (currentRole && currentRole.role !== "admin") {
                    showAlert("Logged in user is not admin, so users and orders admin data may be restricted.", "warning");
                }
            } else {
                window.location.href = AUTH_URL;
                return;
            }

            renderAll();
        } catch (error) {
            renderAll();
            showAlert(`${error.message || "Cannot load dashboard data."} Make sure the backend is running.`, "danger");
        } finally {
            setBusy(refreshButton, false);
        }
    }

    function requireToken() {
        if (getToken()) return true;
        window.location.href = AUTH_URL;
        return false;
    }

    function hideModal(selector) {
        const modal = $(selector);
        if (window.bootstrap && modal) {
            window.bootstrap.Modal.getOrCreateInstance(modal).hide();
        }
    }

    function resetCategoryForm() {
        $("#categoryForm")?.reset();
        if ($("#categoryId")) $("#categoryId").value = "";
        setText("#categoryCardTitle", "Add New Category");
        const saveButton = $("#saveCategoryBtn");
        if (saveButton) {
            saveButton.className = "btn btn-success btn-category-save";
            saveButton.innerHTML = '<i class="ti ti-device-floppy me-1"></i> Save Category';
        }
        const cancelButton = $("#cancelCategoryEditBtn");
        if (cancelButton) {
            cancelButton.className = "btn btn-danger d-none";
        }
    }

    async function handleCategorySave(event) {
        event.preventDefault();
        if (!requireToken()) return;

        const categoryId = $("#categoryId").value;
        const name = $("#categoryName").value.trim();
        const description = $("#categoryDescription").value.trim();

        if (!name) {
            showAlert("Category name is required.", "warning");
            return;
        }

        const button = event.submitter || $("#categoryForm button[type='submit']");
        let saved = false;
        setBusy(button, true, "Saving");
        try {
            const path = categoryId ? `/api/v1/categories/${categoryId}` : "/api/v1/categories/add";
            const method = categoryId ? "PUT" : "POST";

            await api(path, {
                method,
                json: { name, description: description || null },
            });
            showAlert(categoryId ? "Category updated successfully." : "Category saved successfully.", "success");
            await loadDashboard();
            saved = true;
        } catch (error) {
            showAlert(error.message || "Category could not be saved.", "danger");
        } finally {
            setBusy(button, false);
            if (saved) resetCategoryForm();
        }
    }

    async function deleteCategory(categoryId) {
        if (!requireToken()) return;
        if (!confirm("Are you sure you want to delete this category?")) return;

        try {
            await api(`/api/v1/categories/${categoryId}`, { method: "DELETE" });
            resetCategoryForm();
            showAlert("Category deleted successfully.", "success");
            await loadDashboard();
        } catch (error) {
            showAlert(error.message || "Category could not be deleted.", "danger");
        }
    }

    async function handleEditUserSave() {
        if (!requireToken()) return;

        const button = $("#saveEditUserBtn");
        const userId = Number($("#editUserId").value);
        if (!state.currentUser || Number(state.currentUser.id) !== userId) {
            showAlert("This backend endpoint edits the logged-in user only.", "warning");
            return;
        }

        const username = $("#editUserName").value.trim();
        const email = $("#editUserEmail").value.trim();

        setBusy(button, true, "Saving");
        try {
            await api("/api/v1/users/edit", {
                method: "PUT",
                json: { username, email },
            });
            hideModal("#editUserModal");
            showAlert("User updated successfully.", "success");
            await loadDashboard();
        } catch (error) {
            showAlert(error.message || "User could not be updated.", "danger");
        } finally {
            setBusy(button, false);
        }
    }

    async function handleProductSave() {
        if (!requireToken()) return;

        const button = $("#saveProductBtn");
        const categoryId = Number($("#productCatInput").value);
        const payload = {
            name: $("#productNameInput").value.trim(),
            description: $("#productDescriptionInput").value.trim() || null,
            price: Number($("#productPriceInput").value),
            stock: Number($("#productStockInput").value || 0),
            category_id: categoryId,
        };

        if (!payload.name || !payload.price || !payload.category_id) {
            showAlert("Product name, price, and category are required.", "warning");
            return;
        }

        setBusy(button, true, "Saving");
        try {
            await api("/api/v1/products", {
                method: "POST",
                json: payload,
            });
            $("#addProductForm").reset();
            hideModal("#addProductModal");
            showAlert("Product saved successfully.", "success");
            await loadDashboard();
        } catch (error) {
            showAlert(error.message || "Product could not be saved.", "danger");
        } finally {
            setBusy(button, false);
        }
    }

    async function handleEditProductSave() {
        if (!requireToken()) return;

        const button = $("#saveEditProductBtn");
        const productId = $("#editProductId").value;
        const payload = {
            name: $("#editProductName").value.trim(),
            description: $("#editProductDescription").value.trim() || null,
            price: Number($("#editProductPrice").value),
            category_id: Number($("#editProductCat").value),
        };

        const stockValue = $("#editProductStock").value;
        if (stockValue !== "") {
            payload.stock = Number(stockValue);
        }

        if (!payload.name || !payload.price || !payload.category_id) {
            showAlert("Product name, price, and category are required.", "warning");
            return;
        }

        setBusy(button, true, "Saving");
        try {
            await api(`/api/v1/products/${productId}`, {
                method: "PUT",
                json: payload,
            });
            hideModal("#editProductModal");
            showAlert("Product updated successfully.", "success");
            await loadDashboard();
        } catch (error) {
            showAlert(error.message || "Product could not be updated.", "danger");
        } finally {
            setBusy(button, false);
        }
    }

    async function deleteUser(userId) {
        if (!requireToken()) return;
        if (!confirm("Are you sure you want to delete this user?")) return;

        try {
            await api(`/api/v1/users/${userId}`, { method: "DELETE" });
            showAlert("User deleted successfully.", "success");
            await loadDashboard();
        } catch (error) {
            showAlert(error.message || "User could not be deleted.", "danger");
        }
    }

    async function deleteProduct(productId) {
        if (!requireToken()) return;
        if (!confirm("Are you sure you want to delete this product?")) return;

        try {
            await api(`/api/v1/products/${productId}`, { method: "DELETE" });
            showAlert("Product deleted successfully.", "success");
            await loadDashboard();
        } catch (error) {
            showAlert(error.message || "Product could not be deleted.", "danger");
        }
    }

    async function shipOrder(orderId) {
        if (!requireToken()) return;
        try {
            await api(`/api/v1/orders/put/ship/${orderId}`, { method: "PUT" });
            showAlert("Order shipped successfully.", "success");
            await loadDashboard();
        } catch (error) {
            showAlert(error.message || "Order could not be shipped.", "danger");
        }
    }

    async function cancelOrder(orderId) {
        if (!requireToken()) return;
        if (!confirm("Are you sure you want to cancel this order?")) return;

        try {
            await api(`/api/v1/orders/cancel/${orderId}`, { method: "DELETE" });
            showAlert("Order cancelled successfully.", "success");
            await loadDashboard();
        } catch (error) {
            showAlert(error.message || "Order could not be cancelled.", "danger");
        }
    }

    function fillEditUser(userId) {
        const user = state.users.find((item) => Number(item.id) === Number(userId));
        if (!user) return;
        $("#editUserId").value = user.id;
        $("#editUserName").value = user.username;
        $("#editUserEmail").value = user.email;
        const modal = $("#editUserModal");
        if (window.bootstrap && modal) {
            window.bootstrap.Modal.getOrCreateInstance(modal).show();
        }
    }

    function fillEditProduct(productId) {
        const product = state.products.find((item) => Number(item.id) === Number(productId));
        if (!product) return;
        $("#editProductId").value = product.id;
        $("#editProductName").value = product.name;
        $("#editProductDescription").value = product.description || "";
        $("#editProductPrice").value = product.price;
        $("#editProductCat").value = product.category_id || "";
        $("#editProductStock").value = state.productStock.get(Number(product.id)) ?? "";
        const modal = $("#editProductModal");
        if (window.bootstrap && modal) {
            window.bootstrap.Modal.getOrCreateInstance(modal).show();
        }
    }

    function fillEditCategory(categoryId) {
        const category = state.categories.find((item) => Number(item.id) === Number(categoryId));
        if (!category) return;

        $("#categoryId").value = category.id;
        $("#categoryName").value = category.name;
        $("#categoryDescription").value = category.description || "";
        setText("#categoryCardTitle", "Edit Category");
        const saveButton = $("#saveCategoryBtn");
        if (saveButton) {
            saveButton.className = "btn btn-primary btn-category-update";
            saveButton.innerHTML = '<i class="ti ti-device-floppy me-1"></i> Update Category';
        }
        const cancelButton = $("#cancelCategoryEditBtn");
        if (cancelButton) {
            cancelButton.className = "btn btn-danger";
        }
        $("#categoryName").focus();
    }

    function handleTableClick(event) {
        const button = event.target.closest("[data-action]");
        if (!button) return;

        const action = button.dataset.action;
        const id = button.dataset.id;

        if (action === "edit-user") fillEditUser(id);
        if (action === "delete-user") deleteUser(id);
        if (action === "edit-category") fillEditCategory(id);
        if (action === "delete-category") deleteCategory(id);
        if (action === "edit-product") fillEditProduct(id);
        if (action === "delete-product") deleteProduct(id);
        if (action === "ship-order") shipOrder(id);
        if (action === "cancel-order") cancelOrder(id);
    }

    function init() {
        $("#refreshDashboardBtn")?.addEventListener("click", loadDashboard);
        $("#viewAllOrdersBtn")?.addEventListener("click", (event) => {
            event.preventDefault();
            state.showAllOrders = !state.showAllOrders;
            renderOrders();
        });
        $("#dashboardLogoutBtn")?.addEventListener("click", () => {
            clearToken();
            state.currentUser = null;
            state.currentRole = null;
            window.location.href = AUTH_URL;
        });
        $("#categoryForm")?.addEventListener("submit", handleCategorySave);
        $("#cancelCategoryEditBtn")?.addEventListener("click", resetCategoryForm);
        $("#saveEditUserBtn")?.addEventListener("click", handleEditUserSave);
        $("#saveProductBtn")?.addEventListener("click", handleProductSave);
        $("#saveEditProductBtn")?.addEventListener("click", handleEditProductSave);
        $("#usersTableBody")?.addEventListener("click", handleTableClick);
        $("#categoriesTableBody")?.addEventListener("click", handleTableClick);
        $("#productsTableBody")?.addEventListener("click", handleTableClick);
        $("#ordersTableBody")?.addEventListener("click", handleTableClick);

        loadDashboard();
    }

    document.addEventListener("DOMContentLoaded", init);
})();

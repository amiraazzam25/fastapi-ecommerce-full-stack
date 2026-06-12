(function () {
    "use strict";

    const TOKEN_KEY = "mnu_access_token";
    const API_BASE_KEY = "mnu_api_base";
    const DEFAULT_API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";
    const API_BASE = (window.MNU_API_BASE || localStorage.getItem(API_BASE_KEY) || DEFAULT_API_BASE).replace(/\/$/, "");
    const AUTH_URL = "auth-gate";
    const HOME_PAGE_SIZE = 8;

    const state = {
        page: document.body.dataset.storePage || "home",
        currentPage: 1,
        productsPage: 1,
        productsPerPage: 20,
        categories: [],
        products: [],
        productMap: new Map(),
        currentUser: null,
        currentRole: null,
        cart: null,
        cartAvailable: true,
        searchRequestId: 0,
    };

    const $ = (selector) => document.querySelector(selector);
    const $$ = (selector) => Array.from(document.querySelectorAll(selector));

    function token() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function clearToken() {
        localStorage.removeItem(TOKEN_KEY);
    }

    function endpoint(path) {
        return `${API_BASE}${path}`;
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function money(value) {
        return Number(value || 0).toLocaleString(undefined, { style: "currency", currency: "USD" });
    }

    function formatDate(value) {
        if (!value) return "--";
        return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
    }

    function errorMessage(payload, fallback) {
        if (!payload) return fallback;
        if (Array.isArray(payload.detail)) {
            return payload.detail.map((item) => item.msg || JSON.stringify(item)).join(", ");
        }
        return payload.detail || payload.message || payload.messege || fallback;
    }

    async function api(path, options = {}) {
        const { auth = true, json, ...fetchOptions } = options;
        const headers = new Headers(fetchOptions.headers || {});

        if (auth && token()) {
            headers.set("Authorization", `Bearer ${token()}`);
        }

        if (json !== undefined) {
            headers.set("Content-Type", "application/json");
            fetchOptions.body = JSON.stringify(json);
        }

        const response = await fetch(endpoint(path), { ...fetchOptions, headers });
        const contentType = response.headers.get("content-type") || "";
        const payload = contentType.includes("application/json") ? await response.json() : await response.text();

        if (!response.ok) {
            const error = new Error(errorMessage(payload, `Request failed with ${response.status}`));
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
            if (error.status === 404) return notFoundValue;
            throw error;
        }
    }

    function showAlert(message, type = "info") {
        const alert = $("#storeAlert");
        if (!alert) return;
        alert.className = `alert alert-${type} store-alert`;
        alert.textContent = message;
    }

    function hideAlert() {
        const alert = $("#storeAlert");
        if (!alert) return;
        alert.className = "alert d-none store-alert";
        alert.textContent = "";
    }

    function setBusy(button, busy, text) {
        if (!button) return;
        if (busy) {
            button.dataset.originalHtml = button.innerHTML;
            button.disabled = true;
            button.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>${text || "Loading"}`;
            return;
        }
        button.disabled = false;
        if (button.dataset.originalHtml) {
            button.innerHTML = button.dataset.originalHtml;
            delete button.dataset.originalHtml;
        }
    }

    function emptyState(columns, message) {
        return `<tr><td colspan="${columns}" class="text-center text-muted py-4">${escapeHtml(message)}</td></tr>`;
    }

    function productImage(product) {
        const index = ((Number(product.id) || 1) % 14) + 1;
        return `assets/images/products/p-${index}.png`;
    }

    function categoryName(categoryId) {
        const category = state.categories.find((item) => Number(item.id) === Number(categoryId));
        return category ? category.name : "Uncategorized";
    }

    function statusBadge(status) {
        const normalized = String(status || "pending").toLowerCase();
        if (normalized === "shipped") {
            return '<span class="badge bg-success-subtle text-success"><i class="ti ti-truck me-1"></i>Shipped</span>';
        }
        if (normalized === "canceled" || normalized === "cancelled") {
            return '<span class="badge bg-danger-subtle text-danger"><i class="ti ti-x me-1"></i>Canceled</span>';
        }
        return '<span class="badge bg-warning-subtle text-warning"><i class="ti ti-loader me-1"></i>Pending</span>';
    }

    function salePercent(product, index = 0) {
        const discounts = [18, 8, 12, 15, 10, 20];
        const seed = Number(product?.id || index + 1);
        return discounts[Math.abs(seed + index) % discounts.length];
    }

    function dealMeta(product, index = 0) {
        const discount = salePercent(product, index);
        const price = Number(product?.price || 0);
        return {
            discount,
            oldPrice: price * (1 + discount / 100),
        };
    }

    function renderStars() {
        return '<div class="store-stars" aria-label="Five star rating">' +
            Array.from({ length: 5 }, () => '<i class="ti ti-star-filled"></i>').join("") +
            '</div>';
    }

    function pickDealProducts(count, offset = 0) {
        const sorted = [...state.products].sort((first, second) => Number(second.price || 0) - Number(first.price || 0));
        const inStock = sorted.filter((product) => product.stock === "in-stock");
        const source = inStock.length ? inStock : sorted;
        if (!source.length) return [];
        return Array.from({ length: Math.min(count, source.length) }, (_, index) => source[(offset + index) % source.length]);
    }

    async function fetchProductPages(path) {
        const all = [];
        for (let page = 1; page <= 25; page += 1) {
            const separator = path.includes("?") ? "&" : "?";
            const batch = await api(`${path}${separator}page=${page}&page_size=100`, { auth: false });
            all.push(...batch);
            if (batch.length < 100) break;
        }
        return all;
    }

    async function loadCategories() {
        state.categories = await api("/api/v1/categories/getall", { auth: false });
        const categorySelect = $("#categoryFilter");
        if (categorySelect) {
            categorySelect.innerHTML = '<option value="">All Categories</option>' +
                state.categories.map((category) => `<option value="${category.id}">${escapeHtml(category.name)}</option>`).join("");
        }
        const searchCategorySelect = $("#searchCategoryFilter");
        if (searchCategorySelect) {
            searchCategorySelect.innerHTML = '<option value="">All Categories</option>' +
                state.categories.map((category) => `<option value="${category.id}">${escapeHtml(category.name)}</option>`).join("");
        }
        renderProductsCategoryFilters();
    }

    async function loadAllProducts() {
        state.products = await fetchProductPages("/api/v1/products");
        state.productMap = new Map(state.products.map((product) => [Number(product.id), product]));
    }

    async function ensureCategoriesLoaded() {
        if (!state.categories.length) {
            await loadCategories();
            return;
        }
        renderProductsCategoryFilters();
    }

    async function ensureProductsLoaded() {
        if (!state.products.length) {
            await loadAllProducts();
        }
    }

    async function ensureCatalogLoaded() {
        await ensureCategoriesLoaded();
        await ensureProductsLoaded();
    }

    async function loadCommon() {
        if (!token()) {
            window.location.href = AUTH_URL;
            return false;
        }

        try {
            const [me, role] = await Promise.all([
                api("/api/v1/users/me"),
                api("/api/v1/users/me/role"),
            ]);
            state.currentUser = me;
            state.currentRole = role;
            $$(".store-user-name").forEach((element) => {
                element.textContent = me.username;
            });
        } catch (error) {
            clearToken();
            window.location.href = AUTH_URL;
            return false;
        }

        await refreshCartBadge();
        return true;
    }

    async function refreshCartBadge() {
        const badge = $("#cartCountBadge");
        try {
            state.cart = await api("/api/v1/cart/");
            state.cartAvailable = true;
            if (badge) {
                const count = (state.cart.items || []).reduce((sum, item) => sum + Number(item.quantity || 0), 0);
                badge.textContent = count;
            }
        } catch (error) {
            state.cartAvailable = false;
            if (badge) badge.textContent = "0";
        }
    }

    function productCardMarkup(product, index = 0) {
        const inStock = product.stock === "in-stock";
        const deal = dealMeta(product, index);
        return `
            <div class="col">
                <div class="card store-product-card">
                    <div class="card-body d-flex flex-column">
                        <div class="store-product-media">
                            <span class="store-sale-badge">${deal.discount}%</span>
                            <img src="${productImage(product)}" alt="${escapeHtml(product.name)}" class="store-product-img">
                        </div>
                        ${renderStars()}
                        <div class="d-flex justify-content-between align-items-start gap-2 mb-1">
                            <h5 class="fs-15 mb-0">${escapeHtml(product.name)}</h5>
                            <span class="badge ${inStock ? "bg-success-subtle text-success" : "bg-danger-subtle text-danger"}">${inStock ? "In stock" : "Out"}</span>
                        </div>
                        <p class="text-muted small store-product-description mb-2">${escapeHtml(product.description || "No description available.")}</p>
                        <div class="d-flex justify-content-between align-items-end gap-2 mb-3">
                            <span class="text-muted small">${escapeHtml(categoryName(product.category_id))}</span>
                            <div class="text-end">
                                <span class="store-old-price d-block">${money(deal.oldPrice)}</span>
                                <strong class="store-sale-price">${money(product.price)}</strong>
                            </div>
                        </div>
                        <div class="d-flex gap-2 mt-auto store-product-actions">
                            <button type="button" class="btn btn-primary flex-grow-1" data-action="add-cart" data-id="${product.id}" ${inStock ? "" : "disabled"}>
                                <i class="ti ti-shopping-cart me-1"></i> Add
                            </button>
                            <button type="button" class="btn btn-soft-primary btn-icon" data-action="view-product" data-id="${product.id}" title="View details">
                                <i class="ti ti-eye"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>`;
    }

    function renderProductGrid(products, emptyMessage = "No products found.") {
        const grid = $("#productsGrid");
        if (!grid) return;

        if (!products.length) {
            grid.innerHTML = `
                <div class="col-12">
                    <div class="card store-empty d-flex align-items-center justify-content-center">
                        <div class="text-center text-muted">${escapeHtml(emptyMessage)}</div>
                    </div>
                </div>`;
            return;
        }

        grid.innerHTML = products.map((product, index) => productCardMarkup(product, index)).join("");
    }

    function renderHomeDeals() {
        const list = $("#homeDealsList");
        if (!list) return;
        const deals = pickDealProducts(3);
        if (!deals.length) {
            list.innerHTML = '<div class="text-muted text-center py-4">No offers available yet.</div>';
            return;
        }
        list.innerHTML = deals.map((product, index) => {
            const inStock = product.stock === "in-stock";
            const deal = dealMeta(product, index);
            return `
                <div class="store-deal-item">
                    <button type="button" class="store-deal-thumb" data-action="view-product" data-id="${product.id}" aria-label="View ${escapeHtml(product.name)}">
                        <img src="${productImage(product)}" alt="${escapeHtml(product.name)}">
                    </button>
                    <div class="min-w-0">
                        ${renderStars()}
                        <button type="button" class="store-deal-title" data-action="view-product" data-id="${product.id}">${escapeHtml(product.name)}</button>
                        <div class="store-deal-buy mt-1">
                            <div class="store-price-row store-deal-prices">
                                <span class="store-old-stack">
                                    <span class="store-old-price">${money(deal.oldPrice)}</span>
                                    <span class="badge ${inStock ? "bg-success-subtle text-success" : "bg-danger-subtle text-danger"}">${inStock ? "In stock" : "Out"}</span>
                                </span>
                                <span class="store-sale-price">${money(product.price)}</span>
                            </div>
                            <button type="button" class="btn btn-primary btn-sm store-deal-add" data-action="add-cart" data-id="${product.id}" ${inStock ? "" : "disabled"}>Add</button>
                        </div>
                    </div>
                </div>`;
        }).join("");
    }

    function renderWeeklyDeal() {
        const target = $("#weeklyDealBody");
        if (!target) return;
        const product = pickDealProducts(1, 3)[0];
        if (!product) {
            target.innerHTML = '<div class="text-muted text-center py-4">No weekly deal available yet.</div>';
            return;
        }
        const inStock = product.stock === "in-stock";
        const deal = dealMeta(product, 3);
        target.innerHTML = `
            <div class="row g-3 align-items-center">
                <div class="col-md-auto text-center">
                    <div class="store-product-media mb-0">
                        <span class="store-sale-badge">${deal.discount}%</span>
                        <img src="${productImage(product)}" alt="${escapeHtml(product.name)}" class="store-weekly-img">
                    </div>
                </div>
                <div class="col-md">
                    <span class="store-kicker text-danger">Timed Special Offer</span>
                    <h4 class="fw-bold mb-2">${escapeHtml(product.name)}</h4>
                    <p class="text-muted mb-2">${escapeHtml(product.description || "Limited deal from the current catalog.")}</p>
                    ${renderStars()}
                    <div class="store-price-row mt-2">
                        <span class="store-old-price">${money(deal.oldPrice)}</span>
                        <span class="store-sale-price fs-20">${money(product.price)}</span>
                    </div>
                    <div class="store-deal-meter mt-3"><span></span></div>
                    <div class="d-flex justify-content-between mt-1 small text-muted">
                        <span>Available: ${escapeHtml(product.stock)}</span>
                        <span>Sold: ${24 + Number(product.id || 1)}</span>
                    </div>
                </div>
                <div class="col-md-auto text-md-end">
                    <button type="button" class="btn btn-primary mb-2 w-100" data-action="add-cart" data-id="${product.id}" ${inStock ? "" : "disabled"}>
                        <i class="ti ti-shopping-cart me-1"></i> Add to Cart
                    </button>
                    <button type="button" class="btn btn-soft-primary w-100" data-action="view-product" data-id="${product.id}">
                        <i class="ti ti-eye me-1"></i> View Details
                    </button>
                </div>
            </div>`;
    }

    function renderLatestDeals() {
        const grid = $("#latestDealsGrid");
        if (!grid) return;
        const products = pickDealProducts(4, 4);
        if (!products.length) {
            grid.innerHTML = `
                <div class="col-12">
                    <div class="store-empty d-flex align-items-center justify-content-center">
                        <div class="text-center text-muted">No recommendations available yet.</div>
                    </div>
                </div>`;
            return;
        }
        grid.innerHTML = products.map((product, index) => productCardMarkup(product, index + 4)).join("");
    }

    function renderHomeMarketing() {
        renderHomeDeals();
        renderWeeklyDeal();
        renderLatestDeals();
    }

    function renderProductsCategoryFilters() {
        const wrapper = $("#productsCategoryFilters");
        if (!wrapper) return;
        if (!state.categories.length) {
            wrapper.innerHTML = '<div class="text-muted small">No categories available.</div>';
            return;
        }
        wrapper.innerHTML = state.categories.map((category) => `
            <div class="store-category-check">
                <input class="form-check-input" type="checkbox" value="${category.id}" id="productsCategory${category.id}" data-products-category>
                <label for="productsCategory${category.id}">${escapeHtml(category.name)}</label>
            </div>`).join("");
    }

    function getProductsFilterValues() {
        const minRaw = $("#productsMinPrice")?.value;
        const maxRaw = $("#productsMaxPrice")?.value;
        return {
            query: ($("#productsTextFilter")?.value || "").trim().toLowerCase(),
            categories: $$("[data-products-category]:checked").map((input) => Number(input.value)),
            minPrice: minRaw === "" || minRaw === undefined ? null : Number(minRaw),
            maxPrice: maxRaw === "" || maxRaw === undefined ? null : Number(maxRaw),
            sort: $("#productsSort")?.value || "featured",
            inStockOnly: $("#productsInStockOnly")?.checked || false,
        };
    }

    function filteredProductsForCatalog() {
        const filters = getProductsFilterValues();
        let products = [...state.products];

        if (filters.query) {
            products = products.filter((product) => {
                const name = String(product.name || "").toLowerCase();
                const description = String(product.description || "").toLowerCase();
                return name.includes(filters.query) || description.includes(filters.query);
            });
        }

        if (filters.categories.length) {
            products = products.filter((product) => filters.categories.includes(Number(product.category_id)));
        }

        if (filters.minPrice !== null && !Number.isNaN(filters.minPrice)) {
            products = products.filter((product) => Number(product.price || 0) >= filters.minPrice);
        }

        if (filters.maxPrice !== null && !Number.isNaN(filters.maxPrice)) {
            products = products.filter((product) => Number(product.price || 0) <= filters.maxPrice);
        }

        if (filters.inStockOnly) {
            products = products.filter((product) => product.stock === "in-stock");
        }

        products.sort((first, second) => {
            if (filters.sort === "price-asc") return Number(first.price || 0) - Number(second.price || 0);
            if (filters.sort === "price-desc") return Number(second.price || 0) - Number(first.price || 0);
            if (filters.sort === "name-asc") return String(first.name || "").localeCompare(String(second.name || ""));
            return Number(first.id || 0) - Number(second.id || 0);
        });

        return products;
    }

    function renderProductsPagination(totalPages) {
        const pagination = $("#productsPagination");
        if (!pagination) return;
        const page = state.productsPage;
        const makeButton = (label, targetPage, active = false, disabled = false) => `
            <button type="button" class="btn btn-sm ${active ? "btn-primary" : "btn-soft-primary"}" data-action="products-page" data-page="${targetPage}" ${disabled ? "disabled" : ""}>
                ${label}
            </button>`;

        const pages = [];
        const start = Math.max(1, page - 2);
        const end = Math.min(totalPages, page + 2);

        pages.push(makeButton('<i class="ti ti-chevron-left"></i>', page - 1, false, page === 1));
        if (start > 1) {
            pages.push(makeButton("1", 1, page === 1));
            if (start > 2) pages.push('<span class="px-1 text-muted">...</span>');
        }
        for (let current = start; current <= end; current += 1) {
            pages.push(makeButton(String(current), current, current === page));
        }
        if (end < totalPages) {
            if (end < totalPages - 1) pages.push('<span class="px-1 text-muted">...</span>');
            pages.push(makeButton(String(totalPages), totalPages, page === totalPages));
        }
        pages.push(makeButton('<i class="ti ti-chevron-right"></i>', page + 1, false, page === totalPages));
        pagination.innerHTML = pages.join("");
    }

    function renderProductsCatalog() {
        const perPage = Number($("#productsPerPage")?.value || state.productsPerPage || 20);
        state.productsPerPage = perPage;
        const products = filteredProductsForCatalog();
        const totalPages = Math.max(1, Math.ceil(products.length / perPage));
        state.productsPage = Math.min(Math.max(state.productsPage, 1), totalPages);

        const start = (state.productsPage - 1) * perPage;
        const visible = products.slice(start, start + perPage);
        renderProductGrid(visible, "No products match your filters.");

        const resultInfo = $("#productsResultInfo");
        const pageInfo = $("#productsPageInfo");
        if (resultInfo) {
            if (!products.length) {
                resultInfo.textContent = "No products found.";
            } else {
                resultInfo.textContent = `Showing ${start + 1}-${Math.min(start + perPage, products.length)} of ${products.length} products`;
            }
        }
        if (pageInfo) pageInfo.textContent = `Page ${state.productsPage} of ${totalPages}`;
        renderProductsPagination(totalPages);
    }

    function resetProductsFilters() {
        $("#productsTextFilter") && ($("#productsTextFilter").value = "");
        $("#productsMinPrice") && ($("#productsMinPrice").value = "");
        $("#productsMaxPrice") && ($("#productsMaxPrice").value = "");
        $("#productsSort") && ($("#productsSort").value = "featured");
        $("#productsPerPage") && ($("#productsPerPage").value = "20");
        $("#productsInStockOnly") && ($("#productsInStockOnly").checked = false);
        $$("[data-products-category]").forEach((input) => {
            input.checked = false;
        });
        state.productsPage = 1;
        state.productsPerPage = 20;
        renderProductsCatalog();
    }

    function bindProductsFilters() {
        const rerender = () => {
            state.productsPage = 1;
            renderProductsCatalog();
        };
        const debouncedRender = debounce(rerender, 180);
        $("#productsTextFilter")?.addEventListener("input", debouncedRender);
        $("#productsMinPrice")?.addEventListener("input", debouncedRender);
        $("#productsMaxPrice")?.addEventListener("input", debouncedRender);
        $("#productsSort")?.addEventListener("change", rerender);
        $("#productsPerPage")?.addEventListener("change", rerender);
        $("#productsInStockOnly")?.addEventListener("change", rerender);
        $("#productsCategoryFilters")?.addEventListener("change", (event) => {
            if (event.target.matches("[data-products-category]")) rerender();
        });
        $("#resetProductsFiltersBtn")?.addEventListener("click", resetProductsFilters);
    }

    function debounce(callback, delay = 250) {
        let timer;
        return (...args) => {
            window.clearTimeout(timer);
            timer = window.setTimeout(() => callback(...args), delay);
        };
    }

    function matchingProducts(query, limit = 6) {
        const normalized = query.trim().toLowerCase();
        if (!normalized) return [];
        const results = state.products.filter((product) => {
            const name = String(product.name || "").toLowerCase();
            const description = String(product.description || "").toLowerCase();
            const category = categoryName(product.category_id).toLowerCase();
            return name.includes(normalized) || description.includes(normalized) || category.includes(normalized);
        });
        return typeof limit === "number" ? results.slice(0, limit) : results;
    }

    function hideTopbarSearchResults() {
        const results = $("#topbarSearchResults");
        if (!results) return;
        results.classList.add("d-none");
        results.innerHTML = "";
    }

    function renderTopbarSearchResults(query) {
        const results = $("#topbarSearchResults");
        if (!results) return;
        const trimmed = query.trim();
        if (!trimmed) {
            hideTopbarSearchResults();
            return;
        }

        const matches = matchingProducts(trimmed, 6);
        results.classList.remove("d-none");
        if (!matches.length) {
            results.innerHTML = `<div class="store-live-empty">No products found.</div>`;
            return;
        }

        results.innerHTML = matches.map((product) => `
            <button type="button" class="store-live-result" data-action="view-product" data-id="${product.id}">
                <img src="${productImage(product)}" alt="${escapeHtml(product.name)}">
                <span class="min-w-0">
                    <strong>${escapeHtml(product.name)}</strong>
                    <span>${escapeHtml(categoryName(product.category_id))}</span>
                </span>
                <strong class="store-sale-price">${money(product.price)}</strong>
            </button>`).join("") +
            `<a class="store-live-all" href="products?q=${encodeURIComponent(trimmed)}">View all results</a>`;
    }

    function bindTopbarSearch() {
        const form = $("#topbarSearchForm");
        const input = $("#topbarSearchInput");
        if (!form || !input || form.dataset.bound === "true") return;
        form.dataset.bound = "true";

        input.addEventListener("input", () => renderTopbarSearchResults(input.value));
        input.addEventListener("focus", () => renderTopbarSearchResults(input.value));
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            const query = input.value.trim();
            window.location.href = query ? `products?q=${encodeURIComponent(query)}` : "products";
        });
        document.addEventListener("click", (event) => {
            if (!form.contains(event.target)) hideTopbarSearchResults();
        });
    }

    async function loadHomeProducts() {
        const grid = $("#productsGrid");
        if (grid) {
            grid.innerHTML = '<div class="col-12"><div class="card h-100"><div class="card-body d-flex align-items-center justify-content-center text-muted py-5">Loading products...</div></div></div>';
        }

        const products = await fetchProductPages(`/api/v1/products?hide_out_of_stock=false`);
        const shuffled = [...products].sort(() => 0.5 - Math.random());
        const visible = shuffled.slice(0, 4);
        renderProductGrid(visible);
    }

    async function addToCart(productId, button) {
        if (!state.cartAvailable) {
            showAlert("Cart service is not available. Start Redis for cart and checkout features.", "warning");
            return;
        }
        setBusy(button, true, "Adding");
        try {
            await api("/api/v1/cart/", {
                method: "POST",
                json: { product_id: Number(productId), quantity: 1 },
            });
            await refreshCartBadge();
            showAlert("Product added to cart.", "success");
        } catch (error) {
            showAlert(error.message || "Could not add product to cart.", "danger");
        } finally {
            setBusy(button, false);
        }
    }

    function showProductDetails(productId) {
        const product = state.productMap.get(Number(productId));
        if (!product) return;
        const title = $("#productDetailsTitle");
        const body = $("#productDetailsBody");
        const addButton = $("#productDetailsAddBtn");
        const modal = $("#productDetailsModal");
        if (!title || !body || !addButton || !modal) {
            window.location.href = `products?q=${encodeURIComponent(product.name)}`;
            return;
        }
        title.textContent = product.name;
        body.innerHTML = `
            <div class="text-center bg-light-subtle rounded mb-3 py-3">
                <img src="${productImage(product)}" alt="${escapeHtml(product.name)}" class="store-product-img">
            </div>
            <p class="text-muted">${escapeHtml(product.description || "No description available.")}</p>
            <div class="d-flex justify-content-between border-top pt-3">
                <span>${escapeHtml(categoryName(product.category_id))}</span>
                <strong>${money(product.price)}</strong>
            </div>
        `;
        addButton.dataset.id = product.id;
        addButton.disabled = product.stock !== "in-stock";
        if (window.bootstrap) {
            window.bootstrap.Modal.getOrCreateInstance(modal).show();
        }
    }

    async function initHome() {
        await ensureCatalogLoaded();
        renderHomeMarketing();
        await loadHomeProducts();
        $("#categoryFilter")?.addEventListener("change", () => {
            state.currentPage = 1;
            loadHomeProducts();
        });
        $("#hideOutOfStock")?.addEventListener("change", () => {
            state.currentPage = 1;
            loadHomeProducts();
        });
        $("#prevProductsBtn")?.addEventListener("click", () => {
            if (state.currentPage > 1) {
                state.currentPage -= 1;
                loadHomeProducts();
            }
        });
        $("#nextProductsBtn")?.addEventListener("click", () => {
            state.currentPage += 1;
            loadHomeProducts();
        });
    }

    async function initSearch() {
        await ensureCatalogLoaded();
        const params = new URLSearchParams(window.location.search);
        const query = params.get("q") || "";
        const searchInput = $("#searchInput");
        if (searchInput) searchInput.value = query;
        if (query) {
            await performSearch(query);
        } else {
            renderProductGrid([], "Start typing to search products.");
        }

        $("#searchForm")?.addEventListener("submit", (event) => {
            event.preventDefault();
            performSearch($("#searchInput").value.trim());
        });
        const liveSearch = debounce(() => performSearch($("#searchInput").value.trim()), 220);
        $("#searchInput")?.addEventListener("input", liveSearch);
        $("#searchCategoryFilter")?.addEventListener("change", () => performSearch($("#searchInput").value.trim()));
        $("#searchHideOutOfStock")?.addEventListener("change", () => performSearch($("#searchInput").value.trim()));
    }

    async function initProducts() {
        await ensureCatalogLoaded();
        renderProductsCatalog();
        bindProductsFilters();
    }

    async function performSearch(query) {
        const requestId = ++state.searchRequestId;
        if (!query) {
            hideAlert();
            renderProductGrid([], "Start typing to search products.");
            history.replaceState(null, "", "products");
            return;
        }

        hideAlert();
        const products = await api(`/api/v1/products/search?name=${encodeURIComponent(query)}&page=1&page_size=100`, { auth: false });
        if (requestId !== state.searchRequestId) return;
        const categoryId = $("#searchCategoryFilter")?.value;
        const hideOut = $("#searchHideOutOfStock")?.checked;
        const filtered = products.filter((product) => {
            const categoryOk = !categoryId || Number(product.category_id) === Number(categoryId);
            const stockOk = !hideOut || product.stock === "in-stock";
            return categoryOk && stockOk;
        });
        renderProductGrid(filtered, `No products found for "${query}".`);
        history.replaceState(null, "", `products?q=${encodeURIComponent(query)}`);
    }

    async function initCart() {
        await loadCartPage();
        $("#clearCartBtn")?.addEventListener("click", clearCart);
        $("#checkoutBtn")?.addEventListener("click", checkout);
    }

    async function loadCartPage() {
        const tbody = $("#cartTableBody");
        if (!tbody) return;
        tbody.innerHTML = emptyState(5, "Loading cart...");
        try {
            const cart = await api("/api/v1/cart/");
            state.cartAvailable = true;
            renderCart(cart);
            await refreshCartBadge();
        } catch (error) {
            state.cartAvailable = false;
            tbody.innerHTML = emptyState(5, "Cart service is not available. Start Redis for cart features.");
            $("#cartTotal").textContent = money(0);
            showAlert("Cart backend needs Redis at redis:6379 before cart and checkout can work.", "warning");
        }
    }

    function renderCart(cart) {
        const tbody = $("#cartTableBody");
        if (!tbody) return;
        if (!cart.items.length) {
            tbody.innerHTML = emptyState(5, "Your cart is empty.");
        } else {
            tbody.innerHTML = cart.items.map((item) => `
                <tr>
                    <td class="store-table-product">
                        <div class="fw-semibold">${escapeHtml(item.product_name)}</div>
                        <div class="text-muted small">#${escapeHtml(item.product_id)}</div>
                    </td>
                    <td>${money(item.price)}</td>
                    <td>
                        <input type="number" class="form-control form-control-sm store-qty-input" min="1" value="${item.quantity}" data-action="cart-qty" data-id="${item.product_id}">
                    </td>
                    <td class="fw-semibold">${money(item.subtotal)}</td>
                    <td class="text-end">
                        <button type="button" class="btn btn-soft-danger btn-sm btn-icon rounded-circle" data-action="cart-remove" data-id="${item.product_id}">
                            <i class="ti ti-trash"></i>
                        </button>
                    </td>
                </tr>`).join("");
        }
        $("#cartTotal").textContent = money(cart.total_price);
    }

    async function updateCartItem(productId, quantity) {
        try {
            const cart = await api(`/api/v1/cart/${productId}`, {
                method: "PUT",
                json: { quantity: Number(quantity) },
            });
            renderCart(cart);
            await refreshCartBadge();
        } catch (error) {
            showAlert(error.message || "Could not update cart.", "danger");
        }
    }

    async function removeCartItem(productId) {
        try {
            const cart = await api(`/api/v1/cart/${productId}`, { method: "DELETE" });
            renderCart(cart);
            await refreshCartBadge();
            showAlert("Item removed from cart.", "success");
        } catch (error) {
            showAlert(error.message || "Could not remove item.", "danger");
        }
    }

    async function clearCart() {
        if (!confirm("Clear all cart items?")) return;
        try {
            await api("/api/v1/cart/clear", { method: "DELETE" });
            await loadCartPage();
            showAlert("Cart cleared.", "success");
        } catch (error) {
            showAlert(error.message || "Could not clear cart.", "danger");
        }
    }

    async function checkout(event) {
        const button = event.currentTarget;
        setBusy(button, true, "Checkout");
        try {
            const order = await api("/api/v1/orders/create", { method: "POST" });
            await loadCartPage();
            showAlert(`Order #${order.id} created successfully.`, "success");
        } catch (error) {
            showAlert(error.message || "Could not create order.", "danger");
        } finally {
            setBusy(button, false);
        }
    }

    async function initOrders() {
        await ensureProductsLoaded();
        await loadOrders();
    }

    async function loadOrders() {
        const tbody = $("#ordersTableBody");
        if (!tbody) return;
        tbody.innerHTML = emptyState(6, "Loading orders...");
        try {
            const orders = await safeApi("/api/v1/orders/get/my_orders", { notFoundValue: [] });
            if (!orders.length) {
                tbody.innerHTML = emptyState(6, "No orders yet.");
                return;
            }
            const sorted = [...orders].sort((first, second) => Number(second.id) - Number(first.id));
            tbody.innerHTML = sorted.map((order) => {
                const status = String(order.status || "pending").toLowerCase();
                const products = (order.items || []).map((item) => {
                    const product = state.productMap.get(Number(item.product_id));
                    return `${escapeHtml(product ? product.name : `Product #${item.product_id}`)} x ${escapeHtml(item.quantity)}`;
                }).join(", ");
                return `
                    <tr>
                        <td class="fw-semibold">#ORD-${escapeHtml(order.id)}</td>
                        <td>${products || "--"}</td>
                        <td>${money(order.total_price)}</td>
                        <td>${formatDate(order.created_at)}</td>
                        <td>${statusBadge(status)}</td>
                        <td class="text-end">
                            <button type="button" class="btn btn-soft-danger btn-sm" data-action="cancel-order" data-id="${order.id}" ${status === "pending" ? "" : "disabled"}>
                                <i class="ti ti-x me-1"></i> Cancel
                            </button>
                        </td>
                    </tr>`;
            }).join("");
        } catch (error) {
            showAlert(error.message || "Could not load orders.", "danger");
            tbody.innerHTML = emptyState(6, "Could not load orders.");
        }
    }

    async function cancelOrder(orderId) {
        if (!confirm("Cancel this order?")) return;
        try {
            await api(`/api/v1/orders/cancel/${orderId}`, { method: "DELETE" });
            showAlert("Order canceled.", "success");
            await loadOrders();
        } catch (error) {
            showAlert(error.message || "Could not cancel order.", "danger");
        }
    }

    async function initProfile() {
        if (!state.currentUser) return;
        $("#profileName").value = state.currentUser.username;
        $("#profileEmail").value = state.currentUser.email;
        $("#profileRole").textContent = state.currentRole.role;
        $("#profileCreatedAt").textContent = formatDate(state.currentUser.created_at);
        $("#profileForm")?.addEventListener("submit", updateProfile);
    }

    async function updateProfile(event) {
        event.preventDefault();
        const button = event.submitter;
        const payload = {
            username: $("#profileName").value.trim(),
            email: $("#profileEmail").value.trim(),
        };
        const oldPassword = $("#oldPassword").value;
        const password = $("#newPassword").value;
        const confirmPassword = $("#confirmPassword").value;
        if (password || confirmPassword || oldPassword) {
            payload.old_password = oldPassword;
            payload.password = password;
            payload.confirm_password = confirmPassword;
        }
        setBusy(button, true, "Saving");
        try {
            const updated = await api("/api/v1/users/edit", {
                method: "PUT",
                json: payload,
            });
            state.currentUser = updated;
            $$(".store-user-name").forEach((element) => {
                element.textContent = updated.username;
            });
            $("#oldPassword").value = "";
            $("#newPassword").value = "";
            $("#confirmPassword").value = "";
            showAlert("Profile updated.", "success");
        } catch (error) {
            showAlert(error.message || "Could not update profile.", "danger");
        } finally {
            setBusy(button, false);
        }
    }

    function handleClick(event) {
        const button = event.target.closest("[data-action]");
        if (!button) return;
        const action = button.dataset.action;
        const id = button.dataset.id;
        if (action === "add-cart") addToCart(id, button);
        if (action === "view-product") {
            showProductDetails(id);
            hideTopbarSearchResults();
        }
        if (action === "cart-remove") removeCartItem(id);
        if (action === "cancel-order") cancelOrder(id);
        if (action === "products-page") {
            state.productsPage = Number(button.dataset.page || 1);
            renderProductsCatalog();
            $("#productsGrid")?.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

    function handleChange(event) {
        const input = event.target.closest("[data-action='cart-qty']");
        if (input) {
            updateCartItem(input.dataset.id, input.value);
        }
    }

    function bindCommonEvents() {
        document.addEventListener("click", handleClick);
        document.addEventListener("change", handleChange);
        $("#logoutBtn")?.addEventListener("click", () => {
            clearToken();
            window.location.href = AUTH_URL;
        });
        $("#productDetailsAddBtn")?.addEventListener("click", (event) => {
            addToCart(event.currentTarget.dataset.id, event.currentTarget);
        });
    }

    async function init() {
        bindCommonEvents();
        const allowed = await loadCommon();
        if (!allowed) return;

        try {
            if ($("#topbarSearchForm")) {
                await ensureCatalogLoaded();
                bindTopbarSearch();
            }
            if (state.page === "home") await initHome();
            if (state.page === "search") await initSearch();
            if (state.page === "products") await initProducts();
            if (state.page === "cart") await initCart();
            if (state.page === "orders") await initOrders();
            if (state.page === "profile") await initProfile();
        } catch (error) {
            showAlert(error.message || "Store page could not load.", "danger");
        }
    }

    document.addEventListener("DOMContentLoaded", init);
})();

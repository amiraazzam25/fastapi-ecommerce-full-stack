(function () {
    "use strict";

    const TOKEN_KEY = "mnu_access_token";
    const API_BASE_KEY = "mnu_api_base";
    const DEFAULT_API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";
    const API_BASE = (window.MNU_API_BASE || localStorage.getItem(API_BASE_KEY) || DEFAULT_API_BASE).replace(/\/$/, "");
    const ADMIN_URL = "dashboard";
    const USER_URL = "home";

    const $ = (selector) => document.querySelector(selector);

    function endpoint(path) {
        return `${API_BASE}${path}`;
    }

    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function setToken(token) {
        localStorage.setItem(TOKEN_KEY, token);
    }

    function clearToken() {
        localStorage.removeItem(TOKEN_KEY);
    }

    function setStatus(message, type = "info") {
        const status = $("#authStatus");
        if (!status) return;
        status.textContent = message;
        status.className = `auth-status is-${type}`;
    }

    function showAuthCard() {
        $("#authCard")?.classList.remove("d-none");
    }

    function hideAuthCard() {
        $("#authCard")?.classList.add("d-none");
    }

    function errorMessage(payload, fallback) {
        if (!payload) return fallback;
        if (Array.isArray(payload.detail)) {
            return payload.detail.map((item) => item.msg || JSON.stringify(item)).join(", ");
        }
        return payload.detail || payload.message || fallback;
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
            const error = new Error(errorMessage(payload, `Request failed with ${response.status}`));
            error.status = response.status;
            throw error;
        }

        return payload;
    }

    function redirectByRole(role) {
        window.location.href = role === "admin" ? ADMIN_URL : USER_URL;
    }

    async function routeCurrentUser() {
        const token = getToken();
        if (!token) {
            setStatus("Please log in or create a new account.", "info");
            showAuthCard();
            return;
        }

        hideAuthCard();
        setStatus("Checking your session...", "info");

        try {
            const roleData = await api("/api/v1/users/me/role");
            redirectByRole(roleData.role);
        } catch (error) {
            clearToken();
            setStatus("Session expired. Please log in again.", "error");
            showAuthCard();
        }
    }

    async function login(email, password) {
        const body = new URLSearchParams();
        body.set("username", email);
        body.set("password", password);

        const token = await api("/api/v1/users/login", {
            method: "POST",
            auth: false,
            body,
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
        });

        setToken(token.access_token);
        const roleData = await api("/api/v1/users/me/role");
        redirectByRole(roleData.role);
    }

    async function signup(username, email, password) {
        await api("/api/v1/users/register", {
            method: "POST",
            auth: false,
            json: {
                username,
                email,
                password,
                role: "user",
            },
        });

        await login(email, password);
    }

    function setButtonBusy(button, busy, text) {
        if (!button) return;
        if (busy) {
            button.dataset.originalText = button.textContent;
            button.textContent = text;
            button.disabled = true;
            return;
        }
        button.textContent = button.dataset.originalText || button.textContent;
        button.disabled = false;
        delete button.dataset.originalText;
    }

    function initForms() {
        $("#loginForm")?.addEventListener("submit", async (event) => {
            event.preventDefault();
            const button = event.submitter;
            const email = $("#loginEmail").value.trim();
            const password = $("#loginPassword").value;

            if (!email || !password) {
                setStatus("Email and password are required.", "error");
                return;
            }

            setButtonBusy(button, true, "Wait...");
            setStatus("Logging in...", "info");

            try {
                await login(email, password);
            } catch (error) {
                clearToken();
                setStatus(error.message || "Login failed.", "error");
                setButtonBusy(button, false);
            }
        });

        $("#signupForm")?.addEventListener("submit", async (event) => {
            event.preventDefault();
            const button = event.submitter;
            const username = $("#signupName").value.trim();
            const email = $("#signupEmail").value.trim();
            const password = $("#signupPassword").value;

            if (!username || !email || !password) {
                setStatus("Name, email, and password are required.", "error");
                return;
            }

            setButtonBusy(button, true, "Wait...");
            setStatus("Creating your account...", "info");

            try {
                await signup(username, email, password);
            } catch (error) {
                clearToken();
                setStatus(error.message || "Sign up failed.", "error");
                setButtonBusy(button, false);
            }
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        initForms();
        routeCurrentUser();
    });
})();

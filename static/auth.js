"use strict";

const loginTab = document.getElementById("loginTab");
const registerTab = document.getElementById("registerTab");
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const loginMessage = document.getElementById("loginMessage");
const registerMessage = document.getElementById("registerMessage");

loginTab.addEventListener("click", () => {
    loginForm.hidden = false;
    registerForm.hidden = true;
    loginTab.classList.add("active");
    registerTab.classList.remove("active");
});

registerTab.addEventListener("click", () => {
    registerForm.hidden = false;
    loginForm.hidden = true;
    registerTab.classList.add("active");
    loginTab.classList.remove("active");
});

function showMessage(element, message, type = "") {
    element.textContent = message;
    element.className = `auth-message ${type}`.trim();
}

loginForm.addEventListener("submit", async event => {
    event.preventDefault();

    const employee_id = document.getElementById("loginId").value.trim();
    const password = document.getElementById("loginPassword").value;

    showMessage(loginMessage, "Signing in...");

    try {
        const response = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ employee_id, password })
        });

        const data = await response.json();

        if (!response.ok) {
            showMessage(loginMessage, data.error || "Login failed.", "error");
            return;
        }

        window.location.href = "/";

    } catch {
        showMessage(loginMessage, "Unable to connect. Please try again.", "error");
    }
});

registerForm.addEventListener("submit", async event => {
    event.preventDefault();

    const employee_id = document.getElementById("registerId").value.trim();
    const department = document.getElementById("registerDepartment").value;
    const password = document.getElementById("registerPassword").value;
    const confirm = document.getElementById("registerConfirm").value;

    if (password !== confirm) {
        showMessage(registerMessage, "Passwords do not match.", "error");
        return;
    }

    showMessage(registerMessage, "Creating account...");

    try {
        const response = await fetch("/api/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ employee_id, password, department })
        });

        const data = await response.json();

        if (!response.ok) {
            showMessage(registerMessage, data.error || "Registration failed.", "error");
            return;
        }

        showMessage(registerMessage, "Account created. You can now sign in.", "success");
        registerForm.reset();

    } catch {
        showMessage(registerMessage, "Unable to connect. Please try again.", "error");
    }
});

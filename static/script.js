"use strict";

const API_URL = "/api/tickets";

let tickets = [];

// --------------------------------------------------
// UTILITIES
// --------------------------------------------------

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[character]);
}

function normaliseStatus(status) {
    const value = String(status || "Open").toLowerCase();
    if (value === "in progress" || value === "in-progress") return "In Progress";
    if (value === "resolved" || value === "closed") return "Resolved";
    return "Open";
}

async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        credentials: "include", // Crucial for Flask session cookies
        headers: { "Content-Type": "application/json", ...(options.headers || {}) }
    });

    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json")
        ? await response.json()
        : {};

    if (!response.ok) {
        throw new Error(data.error || `Request failed (${response.status}).`);
    }

    return data;
}

function showMessage(element, message, type = "") {
    element.textContent = message;
    element.className = element.id === "formMessage"
        ? `form-message ${type}`.trim()
        : `tickets-message ${type}`.trim();
}

function setLoginMessage(id, message, type) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = message;
    el.className = `login-message ${type}`.trim();
}

// Tab switching
document.getElementById("tabSignIn").addEventListener("click", () => {
    document.getElementById("signInForm").hidden  = false;
    document.getElementById("registerForm").hidden = true;
    document.getElementById("tabSignIn").classList.add("active");
    document.getElementById("tabRegister").classList.remove("active");
});

document.getElementById("tabRegister").addEventListener("click", () => {
    document.getElementById("registerForm").hidden = false;
    document.getElementById("signInForm").hidden   = true;
    document.getElementById("tabRegister").classList.add("active");
    document.getElementById("tabSignIn").classList.remove("active");
});

// Register (Calls backend API)
document.getElementById("registerForm").addEventListener("submit", async event => {
    event.preventDefault();

    const employee_id = document.getElementById("regEmployeeId").value.trim();
    const department  = document.getElementById("regDepartment").value;
    const password    = document.getElementById("regPassword").value;
    const confirm     = document.getElementById("regConfirm").value;

    if (!employee_id || !department || !password) {
        setLoginMessage("registerMessage", "Please complete all fields.", "error");
        return;
    }

    if (password !== confirm) {
        setLoginMessage("registerMessage", "Passwords do not match.", "error");
        return;
    }

    try {
        await apiRequest("/api/register", {
            method: "POST",
            body: JSON.stringify({ employee_id, password, department })
        });

        setLoginMessage("registerMessage", "Account created. You can now sign in.", "success");
        event.target.reset();
    } catch (error) {
        setLoginMessage("registerMessage", error.message || "Registration failed.", "error");
    }
});

// Sign in (Calls backend API)
document.getElementById("signInForm").addEventListener("submit", async event => {
    event.preventDefault();

    const employee_id = document.getElementById("loginEmployeeId").value.trim();
    const password    = document.getElementById("loginPassword").value;

    if (!employee_id || !password) {
        setLoginMessage("signInMessage", "Please enter Employee ID and password.", "error");
        return;
    }

    try {
        const data = await apiRequest("/api/login", {
            method: "POST",
            body: JSON.stringify({ employee_id, password })
        });

        showDashboard(data.employee);
    } catch (error) {
        setLoginMessage("signInMessage", error.message || "Invalid Employee ID or password.", "error");
    }
});

// --------------------------------------------------
// DASHBOARD — only initialised after login
// --------------------------------------------------

function showDashboard(user) {
    document.getElementById("loginScreen").hidden = true;
    document.getElementById("dashboard").hidden   = false;

    document.getElementById("userAvatar").textContent = user.employee_id.slice(0, 2).toUpperCase();
    document.getElementById("userId").textContent     = user.employee_id;
    document.getElementById("userRole").textContent   = user.department || user.role;

    initialiseDashboard();
    loadTickets();
}

function initialiseDashboard() {
    const elements = {
        form:                 document.getElementById("ticketForm"),
        requester:            document.getElementById("requester"),
        employeeDepartment: document.getElementById("employeeDepartment"),
        subject:              document.getElementById("subject"),
        description:          document.getElementById("description"),
        formMessage:          document.getElementById("formMessage"),
        routingPreview:       document.getElementById("routingPreview"),
        submitButton:         document.getElementById("submitTicketButton"),
        newTicketButton:      document.getElementById("newTicketButton"),
        exportButton:         document.getElementById("exportButton"),
        searchInput:          document.getElementById("searchInput"),
        departmentFilter:     document.getElementById("departmentFilter"),
        statusFilter:         document.getElementById("statusFilter"),
        ticketsTableBody:     document.getElementById("ticketsTableBody"),
        ticketsMessage:       document.getElementById("ticketsMessage"),
        ticketCountLabel:     document.getElementById("ticketCountLabel"),
        departmentBreakdown: document.getElementById("departmentBreakdown"),
        totalTickets:         document.getElementById("totalTickets"),
        openTickets:          document.getElementById("openTickets"),
        inProgressTickets:    document.getElementById("inProgressTickets"),
        resolvedTickets:      document.getElementById("resolvedTickets")
    };

    window._el = elements;

    elements.form.addEventListener("submit", submitTicket);
    elements.subject.addEventListener("input", updateRoutingPreview);
    elements.description.addEventListener("input", updateRoutingPreview);
    elements.searchInput.addEventListener("input", renderTickets);
    elements.departmentFilter.addEventListener("change", renderTickets);
    elements.statusFilter.addEventListener("change", renderTickets);

    elements.newTicketButton.addEventListener("click", () => {
        elements.form.scrollIntoView({ behavior: "smooth", block: "start" });
        elements.requester.focus({ preventScroll: true });
    });

    elements.exportButton.addEventListener("click", () => {
        window.location.href = `${API_URL}/export`;
    });

    elements.ticketsTableBody.addEventListener("change", event => {
        const select = event.target.closest(".status-select");
        if (!select) return;
        updateTicketStatus(select.dataset.ticketId, select.value);
    });

    document.getElementById("logoutButton").addEventListener("click", async () => {
        try {
            await apiRequest("/api/logout", { method: "POST" });
        } catch (e) {
            // ignore logout error
        }
        document.getElementById("dashboard").hidden   = true;
        document.getElementById("loginScreen").hidden = false;
        document.getElementById("signInForm").reset();
        setLoginMessage("signInMessage", "", "");
        tickets = [];
    });
}

// --------------------------------------------------
// TICKETS
// --------------------------------------------------

async function loadTickets() {
    const el = window._el;

    try {
        const data = await apiRequest(API_URL);
        tickets = Array.isArray(data.tickets) ? data.tickets : [];
        tickets = tickets.map(t => ({ ...t, status: normaliseStatus(t.status) }));

        renderDashboard();
        renderDepartmentFilter();
        renderTickets();
    } catch (error) {
        console.error("Unable to load tickets:", error);

        el.ticketsTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">
                    Could not load tickets. ${escapeHTML(error.message)}
                </td>
            </tr>`;

        showMessage(el.ticketsMessage,
            "Check that Flask and the database are running, then refresh.", "error");
    }
}

function renderDashboard() {
    const el = window._el;
    el.totalTickets.textContent     = tickets.length;
    el.openTickets.textContent      = tickets.filter(t => t.status === "Open").length;
    el.inProgressTickets.textContent= tickets.filter(t => t.status === "In Progress").length;
    el.resolvedTickets.textContent  = tickets.filter(t => t.status === "Resolved").length;
    renderDepartmentBreakdown();
}

function renderDepartmentBreakdown() {
    const el = window._el;
    const counts = {};

    tickets.forEach(ticket => {
        const dept = ticket.department || "Unassigned";
        counts[dept] = (counts[dept] || 0) + 1;
    });

    const depts = Object.entries(counts).sort((a, b) => b[1] - a[1]);

    if (depts.length === 0) {
        el.departmentBreakdown.innerHTML = `<p class="muted">No tickets have been submitted yet.</p>`;
        return;
    }

    el.departmentBreakdown.innerHTML = depts.map(([dept, count]) => {
        const pct = tickets.length ? Math.round((count / tickets.length) * 100) : 0;
        return `
            <div class="department-row">
                <div class="department-row-top">
                    <span class="department-name">${escapeHTML(dept)}</span>
                    <span class="department-count">${count} ${count === 1 ? "ticket" : "tickets"}</span>
                </div>
                <div class="progress-track">
                    <div class="progress-fill" style="width:${pct}%"></div>
                </div>
            </div>`;
    }).join("");
}

function renderDepartmentFilter() {
    const el = window._el;
    const current = el.departmentFilter.value;
    const depts = [...new Set(tickets.map(t => t.department || "Unassigned"))].sort();

    el.departmentFilter.innerHTML =
        '<option value="">All departments</option>' +
        depts.map(d => `<option value="${escapeHTML(d)}">${escapeHTML(d)}</option>`).join("");

    if (depts.includes(current)) el.departmentFilter.value = current;
}

function getFilteredTickets() {
    const el = window._el;
    const search = el.searchInput.value.trim().toLowerCase();
    const dept   = el.departmentFilter.value;
    const status = el.statusFilter.value;

    return tickets.filter(ticket => {
        const text = [
            ticket.ticket_number, ticket.requester, ticket.employee_department,
            ticket.subject, ticket.description, ticket.department, ticket.status
        ].join(" ").toLowerCase();

        return (
            (!search || text.includes(search)) &&
            (!dept   || ticket.department === dept) &&
            (!status || ticket.status === status)
        );
    });
}

function renderTickets() {
    const el = window._el;
    const filtered = getFilteredTickets();

    if (filtered.length === 0) {
        el.ticketsTableBody.innerHTML = `
            <tr><td colspan="6" class="empty-state">No matching tickets found.</td></tr>`;
    } else {
        el.ticketsTableBody.innerHTML = filtered.map(ticket => {
            const status      = normaliseStatus(ticket.status);
            const statusClass = status.toLowerCase().replace(/\s+/g, "-");
            const options     = ["Open", "In Progress", "Resolved"].map(o =>
                `<option value="${o}" ${status === o ? "selected" : ""}>${o}</option>`
            ).join("");

            return `
                <tr>
                    <td><span class="ticket-id">${escapeHTML(ticket.ticket_number || `CC-${ticket.id ?? "New"}`)}</span></td>
                    <td>
                        <span class="cell-main">${escapeHTML(ticket.requester || "Not provided")}</span>
                        <span class="cell-sub">${escapeHTML(ticket.employee_department || "")}</span>
                    </td>
                    <td>
                        <span class="cell-main">${escapeHTML(ticket.subject || "Support request")}</span>
                        <span class="cell-sub">${escapeHTML(ticket.description || "")}</span>
                    </td>
                    <td>${escapeHTML(ticket.department || "Unassigned")}</td>
                    <td><span class="status-badge status-${statusClass}">${escapeHTML(status)}</span></td>
                    <td>
                        ${ticket.id == null
                            ? '<span class="muted">Unavailable</span>'
                            : `<select class="status-select"
                                       data-ticket-id="${escapeHTML(ticket.id)}"
                                       aria-label="Change status for ${escapeHTML(ticket.ticket_number)}">
                                    ${options}
                               </select>`}
                    </td>
                </tr>`;
        }).join("");
    }

    el.ticketCountLabel.textContent =
        `${filtered.length} of ${tickets.length} ${tickets.length === 1 ? "ticket" : "tickets"}`;
}

function suggestDepartment(text) {
    const msg   = text.toLowerCase();
    const rules = [
        { department: "IT Support",      keywords: ["computer","laptop","password","login","internet","network","software","printer","email","system","technical","wifi","wi-fi"] },
        { department: "Human Resources",  keywords: ["leave","payroll query","recruitment","employment","grievance","hr","human resources","employee benefits","payslip"] },
        { department: "Finance",          keywords: ["invoice","payment","reimbursement","budget","expense claim","purchase order","financial","supplier payment"] },
        { department: "Operations",       keywords: ["office","facilities","building","maintenance","equipment","access card","cleaning","workspace"] }
    ];
    const match = rules.find(r => r.keywords.some(k => msg.includes(k)));
    return match ? match.department : "The classifier will determine the best department when submitted.";
}

function updateRoutingPreview() {
    const el  = window._el;
    const text = `${el.subject.value} ${el.description.value}`.trim();
    el.routingPreview.textContent = text
        ? `Suggested department: ${suggestDepartment(text)}. Final routing is handled by the backend classifier.`
        : "Add an issue description to prepare your request.";
}

async function submitTicket(event) {
    event.preventDefault();
    const el = window._el;

    const ticketData = {
        requester:           el.requester.value.trim(),
        employee_department: el.employeeDepartment.value,
        subject:             el.subject.value.trim(),
        description:         el.description.value.trim()
    };

    if (!Object.values(ticketData).every(Boolean)) {
        showMessage(el.formMessage, "Please complete all fields.", "error");
        return;
    }

    el.submitButton.disabled    = true;
    el.submitButton.textContent = "Submitting...";
    showMessage(el.formMessage, "");

    try {
        const data = await apiRequest(API_URL, { method: "POST", body: JSON.stringify(ticketData) });
        showMessage(el.formMessage, `Ticket ${data.ticket?.ticket_number || ""} submitted successfully.`, "success");
        el.form.reset();
        updateRoutingPreview();
        await loadTickets();
    } catch (error) {
        console.error("Unable to submit ticket:", error);
        showMessage(el.formMessage, error.message || "Unable to submit ticket. Please try again.", "error");
    } finally {
        el.submitButton.disabled    = false;
        el.submitButton.textContent = "Submit ticket";
    }
}

async function updateTicketStatus(ticketId, status) {
    const el = window._el;
    try {
        await apiRequest(`${API_URL}/${encodeURIComponent(ticketId)}`, {
            method: "PATCH",
            body: JSON.stringify({ status })
        });
        showMessage(el.ticketsMessage, "Ticket status updated.");
        await loadTickets();
    } catch (error) {
        console.error("Unable to update ticket:", error);
        showMessage(el.ticketsMessage, error.message || "Could not update ticket status.", "error");
        await loadTickets();
    }
}

// --------------------------------------------------
// ON LOAD — check backend session
// --------------------------------------------------

async function checkActiveSession() {
    try {
        const data = await apiRequest("/api/session");
        if (data.authenticated && data.employee) {
            showDashboard(data.employee);
        }
    } catch (e) {
        // Not logged in, stay on login screen
    }
}

checkActiveSession();
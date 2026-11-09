"use strict";

const API_URL = "/api/tickets";
const TONES = ["Formal", "Friendly", "Urgent"];

let tickets = [];
let currentUser = null;
let dashboardReady = false;

// Ticket ids (as strings) whose reply panel is open. Staff / admin only.
const expandedTickets = new Set();

// What each staff member is working on, per ticket:
// { text, tone, message, messageType }
const replyState = {};

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

function setAccountMessage(message, type = "") {
    const el = document.getElementById("accountMessage");
    el.textContent = message;
    el.className = `account-message ${type}`.trim();
}

function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
}

const isEmployee = () => currentUser?.role === "Employee";
const isStaff    = () => currentUser?.role === "Support Staff";
const isAdmin    = () => currentUser?.role === "Admin";

function getReplyState(ticketId) {
    const key = String(ticketId);
    replyState[key] = replyState[key] || {};
    return replyState[key];
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
    currentUser = user;

    document.getElementById("loginScreen").hidden = true;
    document.getElementById("dashboard").hidden   = false;

    document.getElementById("userAvatar").textContent = user.employee_id.slice(0, 2).toUpperCase();
    document.getElementById("userId").textContent     = user.employee_id;
    document.getElementById("userRole").textContent   =
        user.account_type || user.department || user.role;

    initialiseDashboard();
    applyRoleLayout();
    loadTickets();

    if (isAdmin()) loadAccounts();
}

// What each kind of account sees.
function applyRoleLayout() {
    const $ = id => document.getElementById(id);
    const employee = isEmployee();
    const staff    = isStaff();
    const admin    = isAdmin();

    $("newTicketButton").hidden = !employee;
    $("routingPanel").hidden    = !employee;
    $("overviewGrid").hidden    = staff;
    $("analyticsSection").hidden = employee;
    $("overviewGrid").classList.toggle("single", !employee);
    $("accountsSection").hidden = !admin;
    $("exportButton").hidden    = employee;
    $("actionHeader").textContent = employee ? "Priority" : "Action";

    if (employee) {
        $("pageEyebrow").textContent     = "MY SUPPORT";
        $("pageTitle").textContent       = "My support workspace";
        $("pageDescription").textContent =
            "Submit a request and follow the replies from our support teams.";
        $("ticketsTitle").textContent    = "My support tickets";
        $("ticketsDescription").textContent =
            "Your requests. Replies from support appear underneath each ticket.";
    } else if (staff) {
        const department = currentUser.department || "Support";
        $("pageEyebrow").textContent     = `${department.toUpperCase()} TEAM`;
        $("pageTitle").textContent       = `${department} support workspace`;
        $("pageDescription").textContent =
            "Review the requests sent to your team, draft a reply with AI in the " +
            "tone you choose, and send it to the employee.";
        $("ticketsTitle").textContent    = `${department} tickets`;
        $("ticketsDescription").textContent =
            "Open a ticket with Reply to write back to the employee.";
    } else {
        $("pageEyebrow").textContent     = "ADMINISTRATOR";
        $("pageTitle").textContent       = "Administration";
        $("pageDescription").textContent =
            "See every ticket, reply to employees and manage accounts.";
        $("ticketsTitle").textContent    = "All support tickets";
        $("ticketsDescription").textContent =
            "Review requests from every department and reply to employees.";
    }
}

function initialiseDashboard() {
    // The dashboard can be shown again after sign-out and sign-in, so
    // only attach the listeners once.
    if (dashboardReady) return;
    dashboardReady = true;

    const analyticsPeriod = document.getElementById("analyticsPeriod");
    if (analyticsPeriod) {
        analyticsPeriod.addEventListener("change", loadAnalytics);
    }

    const elements = {
        form:                 document.getElementById("ticketForm"),
        requester:            document.getElementById("requester"),
        employeeDepartment:   document.getElementById("employeeDepartment"),
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
        departmentBreakdown:  document.getElementById("departmentBreakdown"),
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

    // Status dropdown and tone dropdown
    elements.ticketsTableBody.addEventListener("change", event => {
        const statusSelect = event.target.closest(".status-select");
        if (statusSelect) {
            updateTicketStatus(statusSelect.dataset.ticketId, statusSelect.value);
            return;
        }

        const toneSelect = event.target.closest(".tone-select");
        if (toneSelect) {
            getReplyState(toneSelect.dataset.ticketId).tone = toneSelect.value;
        }
    });

    // Keep what staff are typing, so a refresh of the table never loses it.
    elements.ticketsTableBody.addEventListener("input", event => {
        const box = event.target.closest(".reply-text");
        if (box) getReplyState(box.dataset.ticketId).text = box.value;
    });

    // Reply / Generate / Send buttons
    elements.ticketsTableBody.addEventListener("click", event => {
        const toggle = event.target.closest(".reply-toggle");
        if (toggle) {
            toggleReplyPanel(toggle.dataset.ticketId);
            return;
        }

        const generate = event.target.closest(".generate-draft");
        if (generate) {
            generateDraft(generate.dataset.ticketId, generate);
            return;
        }

        const send = event.target.closest(".send-reply");
        if (send) {
            sendReply(send.dataset.ticketId, send.dataset.responseId, send);
        }
    });

    // Administrator: accounts
    document.getElementById("accountForm").addEventListener("submit", createAccount);
    document.getElementById("accountsTableBody").addEventListener("click", event => {
        const button = event.target.closest(".account-toggle");
        if (!button) return;
        setAccountActive(button.dataset.employeeId, button.dataset.active !== "true");
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

        currentUser = null;
        tickets = [];
        expandedTickets.clear();
        Object.keys(replyState).forEach(key => delete replyState[key]);

        elements.ticketsTableBody.innerHTML =
            '<tr><td colspan="6" class="empty-state">Loading tickets...</td></tr>';
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

        showMessage(el.ticketsMessage, "");
        renderDashboard();
        renderDepartmentFilter();
        renderTickets();
        if (!isEmployee()) loadAnalytics();
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


// --------------------------------------------------
// DATA TRACKING & ANALYTICS
// --------------------------------------------------

const analyticsCharts = {};

function destroyAnalyticsChart(id) {
    if (analyticsCharts[id]) {
        analyticsCharts[id].destroy();
        delete analyticsCharts[id];
    }
}

function drawAnalyticsChart(id, type, labels, datasets, options = {}) {
    const canvas = document.getElementById(id);
    if (!canvas || typeof Chart === "undefined") return;

    destroyAnalyticsChart(id);
    analyticsCharts[id] = new Chart(canvas, {
        type,
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: type === "doughnut", position: "bottom" }
            },
            scales: type === "doughnut" ? {} : {
                y: { beginAtZero: true, ticks: { precision: 0 } }
            },
            ...options
        }
    });
}

function formatResponseTime(minutes) {
    if (minutes === null || minutes === undefined) return "—";
    if (minutes < 60) return `${Math.round(minutes)} min`;
    const hours = minutes / 60;
    if (hours < 24) return `${hours.toFixed(1)} hrs`;
    return `${(hours / 24).toFixed(1)} days`;
}

async function loadAnalytics() {
    if (isEmployee()) return;

    const period = document.getElementById("analyticsPeriod")?.value || "7";
    const message = document.getElementById("analyticsMessage");
    if (message) {
        message.textContent = "Updating analytics...";
        message.className = "tickets-message";
    }

    try {
        const data = await apiRequest(`/api/analytics?days=${encodeURIComponent(period)}`);
        const summary = data.summary || {};

        document.getElementById("analyticsScope").textContent =
            data.department_scope === "All departments"
                ? "Organisation-wide support performance."
                : `Performance for ${data.department_scope} support only.`;

        document.getElementById("analyticsTotal").textContent = summary.total ?? 0;
        document.getElementById("analyticsOpen").textContent = summary.open ?? 0;
        document.getElementById("analyticsResolved").textContent = summary.resolved ?? 0;
        document.getElementById("analyticsResponse").textContent =
            formatResponseTime(summary.average_response_minutes);
        document.getElementById("analyticsResponseNote").textContent =
            `${summary.tickets_with_response || 0} ticket(s) with a sent reply`;

        const daily = data.daily || [];
        drawAnalyticsChart(
            "ticketTrendChart",
            "line",
            daily.map(item => new Date(`${item.date}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" })),
            [{
                label: "Tickets",
                data: daily.map(item => item.count),
                borderColor: "#246b66",
                backgroundColor: "rgba(36, 107, 102, 0.12)",
                fill: true,
                tension: 0.3
            }]
        );
        

const departments = data.departments || [];

const departmentColors = {
    "Finance": "#58A58B",
    "Operations": "#477DB5",
    "IT Support": "#E5B54A",
    "Human Resources": "#D98C9A"
};

drawAnalyticsChart(
    "departmentChart",
    "bar",
    departments.map(item => item.department),
    [{
        label: "Tickets",
        data: departments.map(item => item.count),
        backgroundColor: departments.map(item =>
            departmentColors[item.department] || "#A0A0A0"
        ),
        borderRadius: 6
    }]
);

        const statuses = data.statuses || [];
        drawAnalyticsChart(
            "statusChart",
            "doughnut",
            statuses.map(item => item.status),
            [{
                data: statuses.map(item => item.count),
                backgroundColor: ["#e6a23c", "#5485b8", "#3b9870"],
                borderWidth: 0
            }]
        );

        const responseData = data.response_by_department || [];
        drawAnalyticsChart(
            "responseChart",
            "bar",
            responseData.map(item => item.department),
            [{
                label: "Average minutes",
                data: responseData.map(item => item.minutes),
                backgroundColor: "#5485b8",
                borderRadius: 6
            }],
            {
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: "Minutes" }
                    }
                }
            }
        );

        const insights = document.getElementById("weeklyInsights");
        insights.innerHTML = (data.insights || ["No insights available."])
            .map(item => `<li>${escapeHTML(item)}</li>`).join("");
        document.getElementById("insightsPeriodLabel").textContent =
            `Summary for the last ${data.period_days} days.`;

        if (message) message.textContent = "";
    } catch (error) {
        console.error("Unable to load analytics:", error);
        if (message) {
            message.textContent = `Analytics could not be loaded: ${error.message}`;
            message.className = "tickets-message error";
        }
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

// ---------- one message (acknowledgement or reply) ----------

function messageHTML(response, ticket) {
    const isAck  = response.response_type === "Acknowledgement";
    const label  = isAck
        ? "Automatic acknowledgement"
        : `Reply from ${ticket.department} support`;
    const sender = !isAck && response.sent_by ? ` · sent by ${response.sent_by}` : "";
    const when   = formatDate(response.sent_at);

    return `
        <div class="message ${isAck ? "message-auto" : "message-reply"}">
            <div class="message-meta">
                <strong>${escapeHTML(label)}</strong>${escapeHTML(sender)}${when ? ` · ${escapeHTML(when)}` : ""}
            </div>
            <div class="message-body">${escapeHTML(response.text)}</div>
        </div>`;
}

// Messages that have actually been sent to the employee.
function sentMessages(ticket) {
    return (ticket.responses || []).filter(
        r => r.status === undefined || r.status === "Sent"
    );
}

// ---------- employee: messages directly underneath the ticket ----------

function messagesRowHTML(ticket) {
    const messages = sentMessages(ticket);
    if (messages.length === 0) return "";

    const hasReply = messages.some(m => m.response_type !== "Acknowledgement");

    return `
        <tr class="messages-row">
            <td colspan="6">
                <div class="message-list">
                    ${messages.map(m => messageHTML(m, ticket)).join("")}
                    ${hasReply ? "" : `<p class="message-waiting">
                        A support team member will review your request and reply here.
                    </p>`}
                </div>
            </td>
        </tr>`;
}

// ---------- staff / admin: reply panel ----------

function replyPanelHTML(ticket) {
    const id        = escapeHTML(ticket.id);
    const responses = ticket.responses || [];
    const sent      = sentMessages(ticket);
    const draft     = [...responses].reverse().find(
        r => r.status === "Draft" && r.response_type === "Reply"
    );

    const state = getReplyState(ticket.id);
    const tone  = state.tone || draft?.tone || "Formal";
    const text  = state.text != null ? state.text : (draft ? draft.text : "");

    const toneOptions = TONES.map(t =>
        `<option value="${t}" ${t === tone ? "selected" : ""}>${t}</option>`
    ).join("");

    let draftNote = "";
    if (draft) {
        draftNote = draft.ai_generated
            ? `Draft written by AI in the ${draft.tone || "chosen"} tone. Please review and edit it before sending.`
            : "Template draft (the AI was unavailable). Please review and edit it before sending.";
    }

    return `
        <tr class="detail-row">
            <td colspan="6">
                <div class="reply-panel">
                    ${ticket.priority === "Urgent" ? `
                        <p class="urgent-note">
                            Urgent ticket. A person must review this before any reply is sent.
                        </p>` : ""}

                    <div class="reply-request">
                        <strong>${escapeHTML(ticket.subject)}</strong>
                        <p>${escapeHTML(ticket.description)}</p>
                    </div>

                    ${sent.length ? `
                        <div class="message-list">
                            ${sent.map(m => messageHTML(m, ticket)).join("")}
                        </div>` : ""}

                    <div class="reply-controls">
                        <label for="tone-${id}">Tone for the AI draft</label>
                        <select class="tone-select" id="tone-${id}" data-ticket-id="${id}">
                            ${toneOptions}
                        </select>
                        <button type="button" class="button button-secondary generate-draft"
                                data-ticket-id="${id}">
                            ${draft ? "Generate again" : "Generate AI draft"}
                        </button>
                    </div>

                    ${draftNote ? `<p class="draft-note">${escapeHTML(draftNote)}</p>` : ""}

                    <label for="reply-${id}">Reply to the employee</label>
                    <textarea class="reply-text" id="reply-${id}" data-ticket-id="${id}" rows="6"
                              placeholder="Generate an AI draft, or type your own reply...">${escapeHTML(text)}</textarea>

                    <p class="reply-message ${escapeHTML(state.messageType || "")}" role="status">${escapeHTML(state.message || "")}</p>

                    <div class="reply-actions">
                        <button type="button" class="button button-primary send-reply"
                                data-ticket-id="${id}"
                                data-response-id="${draft ? escapeHTML(draft.response_id) : ""}">
                            Send to employee
                        </button>
                    </div>
                </div>
            </td>
        </tr>`;
}

function ticketRowHTML(ticket) {
    const status      = normaliseStatus(ticket.status);
    const statusClass = status.toLowerCase().replace(/\s+/g, "-");
    const priority    = ticket.priority || "Medium";
    const priorityKey = String(priority).toLowerCase();
    const open        = expandedTickets.has(String(ticket.id));

    let actionCell;

    if (isEmployee()) {
        actionCell = `<span class="priority-badge priority-${escapeHTML(priorityKey)}">${escapeHTML(priority)}</span>`;
    } else if (ticket.id == null) {
        actionCell = '<span class="muted">Unavailable</span>';
    } else {
        const options = ["Open", "In Progress", "Resolved"].map(o =>
            `<option value="${o}" ${status === o ? "selected" : ""}>${o}</option>`
        ).join("");

        actionCell = `
            <div class="action-stack">
                <select class="status-select"
                        data-ticket-id="${escapeHTML(ticket.id)}"
                        aria-label="Change status for ${escapeHTML(ticket.ticket_number)}">
                    ${options}
                </select>
                <button type="button" class="button button-secondary button-sm reply-toggle"
                        data-ticket-id="${escapeHTML(ticket.id)}">
                    ${open ? "Close" : "Reply"}
                </button>
            </div>`;
    }

    const departmentCell = isEmployee()
        ? escapeHTML(ticket.department || "Unassigned")
        : `${escapeHTML(ticket.department || "Unassigned")}
           <span class="cell-sub priority-line priority-${escapeHTML(priorityKey)}">Priority: ${escapeHTML(priority)}</span>`;

    let html = `
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
            <td>${departmentCell}</td>
            <td><span class="status-badge status-${statusClass}">${escapeHTML(status)}</span></td>
            <td>${actionCell}</td>
        </tr>`;

    if (isEmployee()) {
        html += messagesRowHTML(ticket);
    } else if (open && ticket.id != null) {
        html += replyPanelHTML(ticket);
    }

    return html;
}

function renderTickets() {
    const el = window._el;
    const filtered = getFilteredTickets();

    if (filtered.length === 0) {
        el.ticketsTableBody.innerHTML = `
            <tr><td colspan="6" class="empty-state">No matching tickets found.</td></tr>`;
    } else {
        el.ticketsTableBody.innerHTML = filtered.map(ticketRowHTML).join("");
    }

    el.ticketCountLabel.textContent =
        `${filtered.length} of ${tickets.length} ${tickets.length === 1 ? "ticket" : "tickets"}`;

    syncWrapWidth();
}

// Tell the stylesheet how wide the visible table area is, so replies
// stay readable on a phone instead of scrolling sideways with the table.
function syncWrapWidth() {
    const wrap = document.querySelector("#ticketsSection .table-wrap");
    if (wrap && wrap.clientWidth > 0) {
        document.documentElement.style.setProperty("--wrap-width", `${wrap.clientWidth}px`);
    }
}

window.addEventListener("resize", syncWrapWidth);

function toggleReplyPanel(ticketId) {
    const key = String(ticketId);

    if (expandedTickets.has(key)) {
        expandedTickets.delete(key);
    } else {
        expandedTickets.add(key);
    }

    renderTickets();
}

// Staff pick a tone and Gemini writes a draft in it.
async function generateDraft(ticketId, button) {
    const state = getReplyState(ticketId);
    const toneBox = document.getElementById(`tone-${ticketId}`);
    const tone = toneBox ? toneBox.value : (state.tone || "Formal");

    state.tone = tone;
    button.disabled = true;
    button.textContent = "Generating... this can take a minute if Google is busy";

    try {
        const data = await apiRequest(`${API_URL}/${encodeURIComponent(ticketId)}/draft`, {
            method: "POST",
            body: JSON.stringify({ tone })
        });

        state.text        = null; // show the new draft
        state.message     = data.warning || "Draft ready. Review it, edit it and send it.";
        state.messageType = data.warning ? "warning" : "success";
    } catch (error) {
        state.message     = error.message || "Could not create a draft.";
        state.messageType = "error";
    }

    await loadTickets();
}

// Send the reply (edited draft, or one typed from scratch).
async function sendReply(ticketId, responseId, button) {
    const state = getReplyState(ticketId);
    const box = document.getElementById(`reply-${ticketId}`);
    const finalText = box ? box.value.trim() : "";

    if (!finalText) {
        state.message     = "Write a reply or generate a draft first.";
        state.messageType = "error";
        renderTickets();
        return;
    }

    button.disabled = true;
    button.textContent = "Sending...";

    const body = { final_text: finalText };
    if (responseId) body.response_id = Number(responseId);

    try {
        await apiRequest(`${API_URL}/${encodeURIComponent(ticketId)}/reply`, {
            method: "POST",
            body: JSON.stringify(body)
        });

        replyState[String(ticketId)] = {
            tone:        state.tone,
            message:     "Reply sent. The employee can now see it under their ticket.",
            messageType: "success"
        };
    } catch (error) {
        state.message     = error.message || "Could not send the reply.";
        state.messageType = "error";
    }

    await loadTickets();
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
        showMessage(
            el.formMessage,
            `Ticket ${data.ticket?.ticket_number || ""} submitted. ` +
            "Your acknowledgement is shown underneath the ticket below.",
            "success"
        );
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
// ADMINISTRATOR: ACCOUNTS
// --------------------------------------------------

async function loadAccounts() {
    const body = document.getElementById("accountsTableBody");

    try {
        const data = await apiRequest("/api/admin/accounts");
        renderAccounts(Array.isArray(data.accounts) ? data.accounts : []);
    } catch (error) {
        body.innerHTML = `
            <tr><td colspan="4" class="empty-state">
                Could not load accounts. ${escapeHTML(error.message)}
            </td></tr>`;
    }
}

function renderAccounts(accounts) {
    const body = document.getElementById("accountsTableBody");

    if (accounts.length === 0) {
        body.innerHTML = '<tr><td colspan="4" class="empty-state">No accounts yet.</td></tr>';
        return;
    }

    body.innerHTML = accounts.map(account => {
        const active = Boolean(account.is_active);
        const isYou  = account.employee_id === currentUser?.employee_id;

        return `
            <tr>
                <td><span class="cell-main">${escapeHTML(account.employee_id)}</span></td>
                <td>${escapeHTML(account.account_type || account.role)}</td>
                <td><span class="account-status ${active ? "active" : "inactive"}">${active ? "Active" : "Deactivated"}</span></td>
                <td>
                    ${isYou
                        ? '<span class="muted">This is you</span>'
                        : `<button type="button" class="button button-secondary button-sm account-toggle"
                                   data-employee-id="${escapeHTML(account.employee_id)}"
                                   data-active="${active}">
                               ${active ? "Deactivate" : "Reactivate"}
                           </button>`}
                </td>
            </tr>`;
    }).join("");
}

async function createAccount(event) {
    event.preventDefault();

    const idBox   = document.getElementById("accountId");
    const typeBox = document.getElementById("accountType");
    const pwBox   = document.getElementById("accountPassword");

    setAccountMessage("");

    try {
        const data = await apiRequest("/api/admin/accounts", {
            method: "POST",
            body: JSON.stringify({
                employee_id:  idBox.value.trim(),
                password:     pwBox.value,
                account_type: typeBox.value
            })
        });

        setAccountMessage(
            `Account ${data.account.employee_id} created (${data.account.account_type}).`,
            "success"
        );
        idBox.value = "";
        pwBox.value = "";
        await loadAccounts();
    } catch (error) {
        setAccountMessage(error.message || "Could not create the account.", "error");
    }
}

async function setAccountActive(employeeId, active) {
    setAccountMessage("");

    try {
        await apiRequest(`/api/admin/accounts/${encodeURIComponent(employeeId)}`, {
            method: "PATCH",
            body: JSON.stringify({ is_active: active })
        });

        setAccountMessage(
            `Account ${employeeId} ${active ? "reactivated" : "deactivated"}.`,
            "success"
        );
    } catch (error) {
        setAccountMessage(error.message || "Could not update the account.", "error");
    }

    await loadAccounts();
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

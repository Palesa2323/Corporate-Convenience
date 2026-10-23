
"use strict";

const API_URL = "/api/tickets";

let tickets = [];

const elements = {
    form: document.getElementById("ticketForm"),
    requester: document.getElementById("requester"),
    employeeDepartment: document.getElementById("employeeDepartment"),
    subject: document.getElementById("subject"),
    description: document.getElementById("description"),
    formMessage: document.getElementById("formMessage"),
    routingPreview: document.getElementById("routingPreview"),
    submitButton: document.getElementById("submitTicketButton"),
    newTicketButton: document.getElementById("newTicketButton"),
    exportButton: document.getElementById("exportButton"),
    searchInput: document.getElementById("searchInput"),
    departmentFilter: document.getElementById("departmentFilter"),
    statusFilter: document.getElementById("statusFilter"),
    ticketsTableBody: document.getElementById("ticketsTableBody"),
    ticketsMessage: document.getElementById("ticketsMessage"),
    ticketCountLabel: document.getElementById("ticketCountLabel"),
    departmentBreakdown: document.getElementById("departmentBreakdown"),
    totalTickets: document.getElementById("totalTickets"),
    openTickets: document.getElementById("openTickets"),
    inProgressTickets: document.getElementById("inProgressTickets"),
    resolvedTickets: document.getElementById("resolvedTickets")
};

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

    if (value === "in progress" || value === "in-progress") {
        return "In Progress";
    }

    if (value === "resolved" || value === "closed") {
        return "Resolved";
    }

    return "Open";
}

async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
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

async function loadTickets() {
    try {
        const data = await apiRequest(API_URL);
        tickets = Array.isArray(data.tickets) ? data.tickets : [];

        tickets = tickets.map(ticket => ({
            ...ticket,
            status: normaliseStatus(ticket.status)
        }));

        renderDashboard();
        renderDepartmentFilter();
        renderTickets();
    } catch (error) {
        console.error("Unable to load tickets:", error);

        elements.ticketsTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">
                    Could not load tickets. ${escapeHTML(error.message)}
                </td>
            </tr>`;

        showMessage(
            elements.ticketsMessage,
            "Check that Flask and the database are running, then refresh.",
            "error"
        );
    }
}

function renderDashboard() {
    elements.totalTickets.textContent = tickets.length;

    elements.openTickets.textContent = tickets.filter(
        ticket => ticket.status === "Open"
    ).length;

    elements.inProgressTickets.textContent = tickets.filter(
        ticket => ticket.status === "In Progress"
    ).length;

    elements.resolvedTickets.textContent = tickets.filter(
        ticket => ticket.status === "Resolved"
    ).length;

    renderDepartmentBreakdown();
}

function renderDepartmentBreakdown() {
    const counts = {};

    tickets.forEach(ticket => {
        const department = ticket.department || "Unassigned";
        counts[department] = (counts[department] || 0) + 1;
    });

    const departments = Object.entries(counts)
        .sort((first, second) => second[1] - first[1]);

    if (departments.length === 0) {
        elements.departmentBreakdown.innerHTML = `
            <p class="muted">No tickets have been submitted yet.</p>`;
        return;
    }

    elements.departmentBreakdown.innerHTML = departments.map(
        ([department, count]) => {
            const percentage = tickets.length
                ? Math.round((count / tickets.length) * 100)
                : 0;

            return `
                <div class="department-row">
                    <div class="department-row-top">
                        <span class="department-name">
                            ${escapeHTML(department)}
                        </span>
                        <span class="department-count">
                            ${count} ${count === 1 ? "ticket" : "tickets"}
                        </span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill"
                             style="width: ${percentage}%"></div>
                    </div>
                </div>`;
        }
    ).join("");
}

function renderDepartmentFilter() {
    const currentValue = elements.departmentFilter.value;

    const departments = [...new Set(
        tickets.map(ticket => ticket.department || "Unassigned")
    )].sort();

    elements.departmentFilter.innerHTML =
        '<option value="">All departments</option>' +
        departments.map(department => `
            <option value="${escapeHTML(department)}">
                ${escapeHTML(department)}
            </option>`
        ).join("");

    if (departments.includes(currentValue)) {
        elements.departmentFilter.value = currentValue;
    }
}

function getFilteredTickets() {
    const search = elements.searchInput.value.trim().toLowerCase();
    const department = elements.departmentFilter.value;
    const status = elements.statusFilter.value;

    return tickets.filter(ticket => {
        const searchableText = [
            ticket.ticket_number,
            ticket.requester,
            ticket.employee_department,
            ticket.subject,
            ticket.description,
            ticket.department,
            ticket.status
        ].join(" ").toLowerCase();

        return (
            (!search || searchableText.includes(search)) &&
            (!department || ticket.department === department) &&
            (!status || ticket.status === status)
        );
    });
}

function renderTickets() {
    const filteredTickets = getFilteredTickets();

    if (filteredTickets.length === 0) {
        elements.ticketsTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">
                    No matching tickets found.
                </td>
            </tr>`;
    } else {
        elements.ticketsTableBody.innerHTML = filteredTickets.map(ticket => {
            const status = normaliseStatus(ticket.status);
            const statusClass = status.toLowerCase().replace(/\s+/g, "-");

            const options = ["Open", "In Progress", "Resolved"].map(option => `
                <option value="${option}"
                    ${status === option ? "selected" : ""}>
                    ${option}
                </option>`
            ).join("");

            return `
                <tr>
                    <td>
                        <span class="ticket-id">
                            ${escapeHTML(ticket.ticket_number || `CC-${ticket.id ?? "New"}`)}
                        </span>
                    </td>
                    <td>
                        <span class="cell-main">
                            ${escapeHTML(ticket.requester || "Not provided")}
                        </span>
                        <span class="cell-sub">
                            ${escapeHTML(ticket.employee_department || "")}
                        </span>
                    </td>
                    <td>
                        <span class="cell-main">
                            ${escapeHTML(ticket.subject || "Support request")}
                        </span>
                        <span class="cell-sub">
                            ${escapeHTML(ticket.description || "")}
                        </span>
                    </td>
                    <td>${escapeHTML(ticket.department || "Unassigned")}</td>
                    <td>
                        <span class="status-badge status-${statusClass}">
                            ${escapeHTML(status)}
                        </span>
                    </td>
                    <td>
                        ${
                            ticket.id == null
                                ? '<span class="muted">Unavailable</span>'
                                : `<select class="status-select"
                                           data-ticket-id="${escapeHTML(ticket.id)}"
                                           aria-label="Change status for ${escapeHTML(ticket.ticket_number)}">
                                        ${options}
                                   </select>`
                        }
                    </td>
                </tr>`;
        }).join("");
    }

    elements.ticketCountLabel.textContent =
        `${filteredTickets.length} of ${tickets.length} ${
            tickets.length === 1 ? "ticket" : "tickets"
        }`;
}

function suggestDepartment(text) {
    const message = text.toLowerCase();

    const rules = [
        {
            department: "IT",
            keywords: [
                "computer", "laptop", "password", "login", "internet",
                "network", "software", "printer", "email", "system",
                "technical", "wifi", "wi-fi"
            ]
        },
        {
            department: "Human Resources",
            keywords: [
                "leave", "payroll query", "recruitment", "employment",
                "grievance", "hr", "human resources", "employee benefits",
                "payslip", "payslip query"
            ]
        },
        {
            department: "Finance",
            keywords: [
                "invoice", "payment", "reimbursement", "budget",
                "expense claim", "purchase order", "financial",
                "supplier payment"
            ]
        },
        {
            department: "Operations",
            keywords: [
                "office", "facilities", "building", "maintenance",
                "equipment", "access card", "cleaning", "workspace"
            ]
        }
    ];

    const match = rules.find(rule =>
        rule.keywords.some(keyword => message.includes(keyword))
    );

    return match
        ? match.department
        : "The classifier will determine the best department when submitted.";
}

function updateRoutingPreview() {
    const text = `${elements.subject.value} ${elements.description.value}`.trim();

    elements.routingPreview.textContent = text
        ? `Suggested department: ${suggestDepartment(text)}. Final routing is handled by the backend classifier.`
        : "Add an issue description to prepare your request.";
}

async function submitTicket(event) {
    event.preventDefault();

    const ticketData = {
        requester: elements.requester.value.trim(),
        employee_department: elements.employeeDepartment.value,
        subject: elements.subject.value.trim(),
        description: elements.description.value.trim()
    };

    if (!Object.values(ticketData).every(Boolean)) {
        showMessage(elements.formMessage, "Please complete all fields.", "error");
        return;
    }

    elements.submitButton.disabled = true;
    elements.submitButton.textContent = "Submitting...";

    showMessage(elements.formMessage, "");

    try {
        const data = await apiRequest(API_URL, {
            method: "POST",
            body: JSON.stringify(ticketData)
        });

        showMessage(
            elements.formMessage,
            `Ticket ${data.ticket?.ticket_number || ""} submitted successfully.`,
            "success"
        );

        elements.form.reset();
        updateRoutingPreview();

        await loadTickets();

    } catch (error) {
        console.error("Unable to submit ticket:", error);

        showMessage(
            elements.formMessage,
            error.message || "Unable to submit ticket. Please try again.",
            "error"
        );
    } finally {
        elements.submitButton.disabled = false;
        elements.submitButton.textContent = "Submit ticket";
    }
}

async function updateTicketStatus(ticketId, status) {
    try {
        await apiRequest(`${API_URL}/${encodeURIComponent(ticketId)}`, {
            method: "PATCH",
            body: JSON.stringify({ status })
        });

        showMessage(elements.ticketsMessage, "Ticket status updated.");
        await loadTickets();

    } catch (error) {
        console.error("Unable to update ticket:", error);

        showMessage(
            elements.ticketsMessage,
            error.message || "Could not update ticket status.",
            "error"
        );

        await loadTickets();
    }
}

function exportTickets() {
    window.location.href = `${API_URL}/export`;
}

elements.form.addEventListener("submit", submitTicket);

elements.subject.addEventListener("input", updateRoutingPreview);
elements.description.addEventListener("input", updateRoutingPreview);

elements.searchInput.addEventListener("input", renderTickets);
elements.departmentFilter.addEventListener("change", renderTickets);
elements.statusFilter.addEventListener("change", renderTickets);

elements.newTicketButton.addEventListener("click", () => {
    elements.form.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

    elements.requester.focus({ preventScroll: true });
});

elements.exportButton.addEventListener("click", exportTickets);

elements.ticketsTableBody.addEventListener("change", event => {
    const select = event.target.closest(".status-select");

    if (!select) {
        return;
    }

    updateTicketStatus(select.dataset.ticketId, select.value);
});

loadTickets();

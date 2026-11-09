const $ = (selector) => document.querySelector(selector);
const form = $("#ticketForm");
const subjectInput = $("#subject");
const descriptionInput = $("#description");
const tableBody = $("#ticketTableBody");
const toneInput = $("#tone");

const departments = [
    { name: "Finance", icon: "$", fillClass: "finance-fill", iconBackground: "#DDF6EB", iconColor: "#21845B" },
    { name: "Operations", icon: "⚙", fillClass: "operations-fill", iconBackground: "#E7F0FF", iconColor: "#3478D4" },
    { name: "IT Support", icon: "IT", fillClass: "it-fill", iconBackground: "#FFF2D6", iconColor: "#9A640D" },
    { name: "Human Resources", icon: "HR", fillClass: "hr-fill", iconBackground: "#EAF4F2", iconColor: "#2C625E" }
];

let tickets = [];
let ticketSequence = 1000;
let currentSuggestion = null;
let toastTimer;

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
}
function showToast(message) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.classList.remove("show"); }, 2800);
}
function nextTicketId() { ticketSequence += 1; return `CC-${ticketSequence}`; }

const routingRules = [
    { department: "IT Support", keywords: ["wifi","wi-fi","wireless network","internet connection","network connection","computer","laptop","desktop","printer","keyboard","mouse not working","monitor","server","vpn","software installation","technical support","system error","application error","email not working","outlook not working","password reset","locked out of my account","cannot log in","can't log in","login problem","access denied","account locked","forgot my password","it support","computer not working","screen not working","technical issue"] },
    { department: "Finance", keywords: ["salary","payroll","salary payment","incorrect salary","salary is incorrect","underpaid","overpaid","expense claim","expense reimbursement","reimbursement","invoice","invoicing","purchase order","supplier payment","payment processing","financial report","budget allocation","budget approval","accounts payable","accounts receivable","tax deduction","tax certificate","financial statement","incorrect payment","payment is missing","missing payment","finance department","travel claim","travel reimbursement","bank reconciliation","full pay","missing pay","pay not received","not paid","incorrect pay","wages","salary not received","short payment","short-paid"] },
    { department: "Human Resources", keywords: ["annual leave","sick leave","maternity leave","paternity leave","leave application","leave balance","leave request","human resources","hr department","employment contract","employment letter","job application","recruitment","onboarding","employee benefits","medical aid","performance review","workplace grievance","harassment complaint","disciplinary hearing","staff policy","payslip","training request","employee wellness","resignation","retirement benefits","hr policy","employment verification","personnel records"] },
    { department: "Operations", keywords: ["meeting room","conference room","projector","office equipment","office supplies","building maintenance","broken desk","broken chair","air conditioning","air conditioner","office cleaning","access card","office access","security guard","delivery delay","logistics","facilities","room booking","vehicle booking","fleet management","equipment maintenance","office relocation","power outage","electricity outage","leaking pipe","plumbing","fire alarm","physical office"] }
];

function containsPhrase(text, phrase) {
    const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const pattern = escaped.replace(/\s+/g, "\\s+");
    return new RegExp(`(^|[^a-z0-9])${pattern}(?=$|[^a-z0-9])`, "i").test(text);
}
function detectDepartment(subject, description) {
    const text = `${subject} ${description}`.toLowerCase().replace(/wi[\s-]?fi/g, "wifi").replace(/can't/g, "cannot").replace(/won't/g, "will not");
    const scores = routingRules.map(rule => {
        let score = 0; const matchedKeywords = [];
        for (const keyword of rule.keywords) {
            if (containsPhrase(text, keyword)) { matchedKeywords.push(keyword); score += keyword.includes(" ") ? 3 : 2; }
        }
        return { department: rule.department, score, matchedKeywords };
    });
    scores.sort((a, b) => b.score - a.score);
    const best = scores[0]; const second = scores[1];
    if (!best || best.score === 0) return { department: null, confidence: "Needs review", reason: "We could not confidently identify the correct department." };
    if (second && second.score > 0 && best.score - second.score < 2) return { department: null, confidence: "Needs review", reason: "Your message may concern multiple departments. Please review it." };
    return { department: best.department, confidence: "Suggested", reason: `Your message appears to belong to ${best.department}.`, matchedKeywords: best.matchedKeywords };
}
function detectPriority(subject, description) {
    const text = `${subject} ${description}`.toLowerCase();
    const highPriorityTerms = ["business critical","business is stopped","entire office is down","all employees affected","major outage","security breach","data breach","ransomware","urgent","critical issue","cannot work at all"];
    const mediumPriorityTerms = ["deadline","error","failed","failure","multiple employees","intermittent","delayed","not working"];
    if (highPriorityTerms.some(term => containsPhrase(text, term))) return "High";
    if (mediumPriorityTerms.some(term => containsPhrase(text, term))) return "Medium";
    return "Low";
}
function updateRoutingPreview() {
    const subject = subjectInput.value.trim(); const description = descriptionInput.value.trim();
    $("#charCount").textContent = `${descriptionInput.value.length} / 3000`;
    const title = $("#routingTitle"); const message = $("#routingMessage"); const badge = $("#routingBadge"); const reviewNotice = $("#reviewNotice");
    if (!subject && !description) { currentSuggestion = null; title.textContent = "Smart department routing"; message.textContent = "Your recommended department will appear here as you describe your issue."; badge.textContent = "Waiting"; badge.className = "routing-badge"; reviewNotice.hidden = true; return; }
    if (description.length < 5 && subject.length < 5) { currentSuggestion = null; title.textContent = "Tell us a little more"; message.textContent = "Add more detail so we can identify the right department."; badge.textContent = "Incomplete"; badge.className = "routing-badge"; reviewNotice.hidden = true; return; }
    currentSuggestion = detectDepartment(subject, description);
    if (currentSuggestion.department) { title.textContent = `Suggested department: ${currentSuggestion.department}`; message.textContent = currentSuggestion.reason; badge.textContent = "Suggested"; badge.className = "routing-badge detected"; reviewNotice.hidden = true; }
    else { title.textContent = "Department needs review"; message.textContent = currentSuggestion.reason; badge.textContent = "Review"; badge.className = "routing-badge review"; reviewNotice.hidden = false; }
}
subjectInput.addEventListener("input", updateRoutingPreview);
descriptionInput.addEventListener("input", updateRoutingPreview);

function renderDepartmentBreakdown() {
    const container = $("#departmentBreakdown");
    container.innerHTML = departments.map(department => {
        const count = tickets.filter(ticket => ticket.department === department.name).length;
        const totalAssigned = tickets.filter(ticket => ticket.department !== null).length;
        const width = totalAssigned ? (count / totalAssigned) * 100 : 0;
        return `<div class="department-row"><div class="department-label"><span class="department-icon" style="background:${department.iconBackground}; color:${department.iconColor}">${department.icon}</span><span class="department-name">${department.name}</span><span class="department-count">${count}</span></div><div class="department-track"><div class="department-fill ${department.fillClass}" style="width:${width}%"></div></div></div>`;
    }).join("");
}
function updateStatistics() {
    $("#totalCount").textContent = tickets.length;
    $("#openCount").textContent = tickets.filter(t => t.status === "Open").length;
    $("#progressCount").textContent = tickets.filter(t => t.status === "In Progress").length;
    $("#resolvedCount").textContent = tickets.filter(t => t.status === "Resolved").length;
}
function getFilteredTickets() {
    const query = $("#searchInput").value.trim().toLowerCase();
    const department = $("#departmentFilter").value;
    const status = $("#statusFilter").value;
    return tickets.filter(ticket => {
        const searchable = [ticket.id, ticket.requester, ticket.subject, ticket.description, ticket.employeeDepartment, ticket.department || "Needs Review", ticket.priority, ticket.status].join(" ").toLowerCase();
        const matchesSearch = searchable.includes(query);
        const matchesDepartment = department === "All" || (department === "Needs Review" && !ticket.department) || ticket.department === department;
        const matchesStatus = status === "All" || ticket.status === status;
        return matchesSearch && matchesDepartment && matchesStatus;
    });
}
function renderTickets() {
    const filtered = getFilteredTickets();
    tableBody.innerHTML = filtered.map(ticket => {
        const assignedDepartment = ticket.department ? escapeHTML(ticket.department) : "Needs review";
        const statusAction = ticket.status === "Open" ? "Start" : ticket.status === "In Progress" ? "Resolve" : "Reopen";
        return `<tr><td><span class="ticket-id">${escapeHTML(ticket.id)}</span><span class="ticket-requester">${escapeHTML(ticket.requester)}</span></td><td><div class="ticket-subject" title="${escapeHTML(ticket.subject)}">${escapeHTML(ticket.subject)}</div><small>${escapeHTML(ticket.tone || '')} tone</small></td><td><span class="badge ${ticket.department ? "status-open" : "status-review"}">${assignedDepartment}</span></td><td><span class="badge priority-${ticket.priority.toLowerCase()}">${ticket.priority}</span></td><td><span class="badge status-${ticket.status.toLowerCase().replace(/\s+/g, "-")}">${ticket.status}</span></td><td><button type="button" class="row-action" data-action="status" data-id="${escapeHTML(ticket.id)}">${statusAction}</button></td></tr>`;
    }).join("");
    $("#emptyState").hidden = filtered.length !== 0;
    $("#ticketCountLabel").textContent = `${filtered.length} of ${tickets.length} tickets`;
}
function refreshDashboard() { updateStatistics(); renderDepartmentBreakdown(); renderTickets(); }

// Member 4: Tone-based AI Response Generation
function generateAIResponse(tone, department, subject, requester) {
    const dept = department || "support team";
    if (tone === "Formal") {
        return `Dear ${requester},\n\nThank you for submitting your ticket regarding "${subject}". Your request has been classified under ${dept} and has been assigned priority attention.\n\nOur team will review your concern and provide a formal update within the designated service level timeframe.\n\nKind regards,\nCorporate Convenience Support`;
    }
    if (tone === "Urgent") {
        return `Hi ${requester} - ACKNOWLEDGED URGENT.\n\nYour ticket "${subject}" is routed to ${dept} as HIGH PRIORITY. We are escalating this immediately.\n\nExpect an update within 1 hour. If this is business-critical, please also alert ${dept} directly.\n\n- CC Support Team`;
    }
    return `Hi ${requester}! 👋\n\nThanks for reaching out about "${subject}". We've got it! It's been sent to our awesome ${dept} team.\n\nThey'll jump on it soon and keep you posted. Let us know if you need anything else in the meantime!\n\nCheers,\nCorporate Convenience Team`;
}
function showClassificationResult(ticket) {
    document.getElementById('classification-result').textContent = ticket.department || "Needs Review";
    document.getElementById('confidence-result').textContent = ticket.routingReason || "";
    document.getElementById('tone-used').textContent = ticket.tone;
    document.getElementById('ai-response-box').textContent = ticket.ai_response;
    document.getElementById('result-container').style.display = 'block';
    document.getElementById('result-container').scrollIntoView({behavior: 'smooth'});
}

form.addEventListener("submit", event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const requester = $("#requester").value.trim();
    const employeeDepartment = $("#employeeDepartment").value;
    const subject = subjectInput.value.trim();
    const description = descriptionInput.value.trim();
    const tone = $("#tone").value || "Friendly";

    if (!requester || !employeeDepartment || !subject || description.length < 5 || !tone) {
        showToast("Please complete all required fields including tone.");
        return;
    }
    const routing = detectDepartment(subject, description);
    const priority = detectPriority(subject, description);

    const ticket = {
        id: nextTicketId(),
        requester,
        employeeDepartment,
        subject,
        description,
        department: routing.department,
        routingReason: routing.reason,
        priority,
        status: "Open",
        tone: tone,
        ai_response: generateAIResponse(tone, routing.department, subject, requester),
        createdAt: new Date().toISOString()
    };
    tickets.unshift(ticket);
    showClassificationResult(ticket);
    refreshDashboard();
    $("#searchInput").value = ""; $("#departmentFilter").value = "All"; $("#statusFilter").value = "All";
    refreshDashboard();
    if (ticket.department) showToast(`${ticket.id} submitted and routed to ${ticket.department} with ${tone} tone.`);
    else showToast(`${ticket.id} submitted for manual review with ${tone} tone.`);
});

form.addEventListener("reset", () => {
    currentSuggestion = null;
    const rc = document.getElementById('result-container');
    if (rc) rc.style.display = 'none';
    setTimeout(() => { updateRoutingPreview(); }, 0);
});

tableBody.addEventListener("click", event => {
    const button = event.target.closest("[data-action='status']");
    if (!button) return;
    const ticket = tickets.find(item => item.id === button.dataset.id);
    if (!ticket) return;
    if (ticket.status === "Open") ticket.status = "In Progress";
    else if (ticket.status === "In Progress") ticket.status = "Resolved";
    else ticket.status = "Open";
    refreshDashboard();
    showToast(`${ticket.id} status updated to ${ticket.status}.`);
});

$("#searchInput").addEventListener("input", renderTickets);
$("#departmentFilter").addEventListener("change", renderTickets);
$("#statusFilter").addEventListener("change", renderTickets);
$("#createTicketBtn").addEventListener("click", () => { $("#new-ticket").scrollIntoView({ behavior: "smooth", block: "start" }); setTimeout(() => $("#requester").focus(), 350); });
document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", () => {
        document.querySelectorAll(".nav-link").forEach(item => { item.classList.remove("active"); });
        link.classList.add("active");
    });
});
$("#exportBtn").addEventListener("click", () => {
    const rows = getFilteredTickets();
    if (!rows.length) { showToast("There are no tickets to export."); return; }
    const columns = ["Ticket ID","Employee","Employee Department","Subject","Description","Assigned Department","Priority","Status","Tone","AI Response","Created At"];
    function csvCell(value) { let text = String(value ?? ""); if (/^[\s]*[=+\-@]/.test(text)) text = "'" + text; return `"${text.replace(/"/g, '""')}"`; }
    const values = rows.map(ticket => [ticket.id, ticket.requester, ticket.employeeDepartment, ticket.subject, ticket.description, ticket.department || "Needs review", ticket.priority, ticket.status, ticket.tone || "", ticket.ai_response || "", ticket.createdAt]);
    const csv = [columns, ...values].map(row => row.map(csvCell).join(",")).join("\r\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob); const link = document.createElement("a");
    link.href = url; link.download = "corporate-convenience-tickets.csv"; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
    showToast("Ticket report exported.");
});
refreshDashboard();
updateRoutingPreview();
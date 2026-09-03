const alertBox = document.getElementById("alert-box");
const tabs = document.getElementById("tabs");
const panels = {
  overview: document.getElementById("panel-overview"),
  requests: document.getElementById("panel-requests"),
  users: document.getElementById("panel-users"),
  food: document.getElementById("panel-food"),
  announcements: document.getElementById("panel-announcements"),
  issues: document.getElementById("panel-issues"),
  rent: document.getElementById("panel-rent"),
  documents: document.getElementById("panel-documents"),
  settings: document.getElementById("panel-settings"),
};

function switchTab(name) {
  Object.entries(panels).forEach(([key, el]) => { el.hidden = key !== name; });
  [...tabs.children].forEach((a) => a.classList.toggle("active", a.dataset.tab === name));
  clearAlert(alertBox);
}

tabs.addEventListener("click", (e) => {
  const link = e.target.closest("a[data-tab]");
  if (!link) return;
  e.preventDefault();
  switchTab(link.dataset.tab);
  loadTab(link.dataset.tab);
});

document.querySelectorAll("[data-tab-link]").forEach((el) => {
  el.addEventListener("click", (e) => {
    e.preventDefault();
    const tab = el.dataset.tabLink;
    switchTab(tab);
    loadTab(tab);
  });
});

const loaded = new Set();

async function loadTab(name, force = false) {
  if (loaded.has(name) && !force) return;
  loaded.add(name);
  try {
    if (name === "overview") await loadOverview();
    if (name === "requests") await loadRequests();
    if (name === "users") await loadUsers();
    if (name === "food") await loadFood();
    if (name === "announcements") await loadAnnouncements();
    if (name === "issues") await loadIssues();
    if (name === "rent") await loadRentTab();
    if (name === "documents") await loadDocuments();
    if (name === "settings") await loadSettings();
  } catch (err) {
    loaded.delete(name);
    showAlert(alertBox, err.message || "Something went wrong loading this section.");
  }
}

// ---------- Overview ----------
async function loadOverview() {
  const me = await api.get("/api/auth/me");
  document.getElementById("overview-group-id").textContent = me.group_id;
  const users = await api.get("/api/groups/users");
  document.getElementById("overview-user-count").textContent = users.length;
  const pending = await api.get("/api/join-requests");
  document.getElementById("overview-pending-count").textContent = pending.length;
}

// ---------- Join Requests ----------
async function loadRequests() {
  await renderRequests();
}

async function renderRequests() {
  const list = document.getElementById("requests-list");
  const items = await api.get("/api/join-requests");
  if (items.length === 0) {
    list.innerHTML = `<div class="empty-state">No pending join requests.</div>`;
    return;
  }
  list.innerHTML = items.map((r) => `
    <div class="list-item list-item-header">
      <div>
        <strong>${escapeHtml(r.user_name || r.user_id)}</strong>
        <p class="text-muted">Requested ${formatDateTime(r.requested_at)}</p>
      </div>
      <div class="btn-row">
        <button class="btn-sm" data-approve="${r.request_id}">Approve</button>
        <button class="btn-sm btn-danger" data-reject="${r.request_id}">Reject</button>
      </div>
    </div>
  `).join("");

  list.querySelectorAll("[data-approve]").forEach((btn) => {
    btn.addEventListener("click", () => decide(btn.dataset.approve, true));
  });
  list.querySelectorAll("[data-reject]").forEach((btn) => {
    btn.addEventListener("click", () => decide(btn.dataset.reject, false));
  });
}

async function decide(requestId, approve) {
  try {
    await api.patch(`/api/join-requests/${requestId}/decision`, { approve });
    await renderRequests();
    loaded.delete("overview");
    loaded.delete("users");
  } catch (err) {
    showAlert(alertBox, err.message || "Could not update request.");
  }
}

// ---------- Users ----------
async function loadUsers() {
  const list = document.getElementById("users-list");
  const users = await api.get("/api/groups/users");
  if (users.length === 0) {
    list.innerHTML = `<div class="empty-state">No approved residents yet.</div>`;
    return;
  }
  list.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Name</th><th>Room</th><th>Sharing</th><th>Phone</th><th>Joined</th></tr></thead>
        <tbody>
          ${users.map((u) => `
            <tr>
              <td>${escapeHtml(u.name)}</td>
              <td>${escapeHtml(u.room_number || "—")}</td>
              <td>${u.sharing_type || "—"}</td>
              <td>${escapeHtml(u.phone || "—")}</td>
              <td>${u.joined_date ? formatDate(u.joined_date) : "—"}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

// ---------- Food ----------
document.getElementById("menu-date").valueAsDate = new Date();

let currentOwnerMenu = null;

async function loadFood() {
  await loadMenuForSelectedDate();
}

async function loadMenuForSelectedDate() {
  const selectedDate = document.getElementById("menu-date").value;
  if (!selectedDate) return;

  try {
    currentOwnerMenu = await api.get(`/api/food/by-date/${selectedDate}`);
  } catch (err) {
    showAlert(alertBox, err.message || "Could not load menu for that date.");
    return;
  }

  document.getElementById("menu-breakfast").value = currentOwnerMenu?.breakfast || "";
  document.getElementById("menu-lunch").value = currentOwnerMenu?.lunch || "";
  document.getElementById("menu-dinner").value = currentOwnerMenu?.dinner || "";

  await renderFeedback();
}

document.getElementById("menu-date").addEventListener("change", loadMenuForSelectedDate);

async function renderFeedback() {
  const list = document.getElementById("feedback-list");
  if (!currentOwnerMenu) {
    list.innerHTML = `<div class="empty-state">No menu posted for this date yet.</div>`;
    return;
  }
  const feedback = await api.get(`/api/food/${currentOwnerMenu.id}/feedback`);
  if (feedback.length === 0) {
    list.innerHTML = `<div class="empty-state">No feedback submitted for this date yet.</div>`;
    return;
  }
  list.innerHTML = feedback.map((f) => `
    <div class="list-item">
      <div class="list-item-header">
        ${badge(statusLabel(f.rating), f.rating === "bad" ? "unpaid" : f.rating === "average" ? "warning" : "paid")}
        <span class="text-muted">${formatDateTime(f.created_at)}</span>
      </div>
      ${f.comment ? `<p>${escapeHtml(f.comment)}</p>` : ""}
    </div>
  `).join("");
}

document.getElementById("menu-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    menu_date: document.getElementById("menu-date").value,
    breakfast: document.getElementById("menu-breakfast").value.trim() || null,
    lunch: document.getElementById("menu-lunch").value.trim() || null,
    dinner: document.getElementById("menu-dinner").value.trim() || null,
  };
  try {
    await api.post("/api/food", payload);
    showAlert(alertBox, "Menu saved.", "success");
    await loadMenuForSelectedDate();
  } catch (err) {
    showAlert(alertBox, err.message || "Could not save menu.");
  }
});

// ---------- Announcements ----------
async function loadAnnouncements() {
  await renderAnnouncements();
}

async function renderAnnouncements() {
  const list = document.getElementById("announcements-list");
  const items = await api.get("/api/announcements");
  if (items.length === 0) {
    list.innerHTML = `<div class="empty-state">No announcements published yet.</div>`;
    return;
  }
  list.innerHTML = items.map((a) => `
    <div class="list-item">
      <div class="list-item-header">
        <strong>${escapeHtml(a.title)}</strong>
        ${badge(statusLabel(a.type), a.type)}
      </div>
      <p>${escapeHtml(a.message)}</p>
      <div class="list-item-header">
        <span class="text-muted">${formatDateTime(a.created_at)}</span>
        <button class="btn-sm btn-danger" data-delete-announcement="${a.id}">Delete</button>
      </div>
    </div>
  `).join("");

  list.querySelectorAll("[data-delete-announcement]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Delete this announcement?")) return;
      try {
        await api.delete(`/api/announcements/${btn.dataset.deleteAnnouncement}`);
        await renderAnnouncements();
      } catch (err) {
        showAlert(alertBox, err.message || "Could not delete announcement.");
      }
    });
  });
}

document.getElementById("announcement-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    title: document.getElementById("ann-title").value.trim(),
    message: document.getElementById("ann-message").value.trim(),
    type: document.getElementById("ann-type").value,
  };
  try {
    await api.post("/api/announcements", payload);
    e.target.reset();
    await renderAnnouncements();
    showAlert(alertBox, "Announcement published.", "success");
  } catch (err) {
    showAlert(alertBox, err.message || "Could not publish announcement.");
  }
});

// ---------- Issues ----------
async function loadIssues() {
  await renderIssues();
}

async function renderIssues() {
  const list = document.getElementById("issues-list");
  const issues = await api.get("/api/issues");
  if (issues.length === 0) {
    list.innerHTML = `<div class="empty-state">No issues reported yet.</div>`;
    return;
  }
  list.innerHTML = issues.map((issue) => `
    <div class="list-item">
      <div class="list-item-header">
        <strong>${escapeHtml(statusLabel(issue.category))}</strong>
        ${badge(statusLabel(issue.status), issue.status)}
      </div>
      <p>${escapeHtml(issue.description)}</p>
      ${issue.room_number ? `<p class="text-muted">Room ${escapeHtml(issue.room_number)}</p>` : ""}
      ${issue.image_path ? `<img src="${API_BASE}/api/issues/${issue.id}/image" style="max-width:200px; border-radius:8px;" />` : ""}
      <p class="text-muted">Reported ${formatDateTime(issue.created_at)}</p>
      <div class="field" style="max-width:220px;">
        <label>Status</label>
        <select data-issue-status="${issue.id}">
          <option value="pending" ${issue.status === "pending" ? "selected" : ""}>Pending</option>
          <option value="in_progress" ${issue.status === "in_progress" ? "selected" : ""}>In Progress</option>
          <option value="resolved" ${issue.status === "resolved" ? "selected" : ""}>Resolved</option>
        </select>
      </div>
    </div>
  `).join("");

  list.querySelectorAll("[data-issue-status]").forEach((select) => {
    select.addEventListener("change", async () => {
      try {
        await api.patch(`/api/issues/${select.dataset.issueStatus}/status`, { status: select.value });
      } catch (err) {
        showAlert(alertBox, err.message || "Could not update issue status.");
      }
    });
  });
}

// ---------- Rent ----------
let rentUserNames = {};

async function loadRentTab() {
  const userSelect = document.getElementById("rent-user");
  const users = await api.get("/api/groups/users");
  rentUserNames = Object.fromEntries(users.map((u) => [u.user_id, u.name]));
  userSelect.innerHTML = users.map((u) => `<option value="${u.user_id}">${escapeHtml(u.name)} (Room ${escapeHtml(u.room_number || "—")})</option>`).join("");
  await renderRentList();
}

async function renderRentList() {
  const list = document.getElementById("rent-list");
  const items = await api.get("/api/rent");
  if (items.length === 0) {
    list.innerHTML = `<div class="empty-state">No rent records yet.</div>`;
    return;
  }
  list.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Resident</th><th>Due date</th><th>Amount</th><th>Status</th></tr></thead>
        <tbody>
          ${items.map((r) => `
            <tr>
              <td>${escapeHtml(rentUserNames[r.user_id] || r.user_id)}</td>
              <td>${formatDate(r.due_date)}</td>
              <td>${r.monthly_rent}</td>
              <td>
                <select data-rent-status="${r.id}">
                  <option value="unpaid" ${r.status === "unpaid" ? "selected" : ""}>Unpaid</option>
                  <option value="paid" ${r.status === "paid" ? "selected" : ""}>Paid</option>
                  <option value="overdue" ${r.status === "overdue" ? "selected" : ""}>Overdue</option>
                </select>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;

  list.querySelectorAll("[data-rent-status]").forEach((select) => {
    select.addEventListener("change", async () => {
      try {
        await api.put(`/api/rent/${select.dataset.rentStatus}`, { status: select.value });
      } catch (err) {
        showAlert(alertBox, err.message || "Could not update rent status.");
      }
    });
  });
}

document.getElementById("rent-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    user_id: document.getElementById("rent-user").value,
    monthly_rent: Number(document.getElementById("rent-amount").value),
    due_date: document.getElementById("rent-due").value,
  };
  try {
    await api.post("/api/rent", payload);
    e.target.reset();
    await renderRentList();
    showAlert(alertBox, "Rent record added.", "success");
  } catch (err) {
    showAlert(alertBox, err.message || "Could not add rent record.");
  }
});

// ---------- Documents ----------
async function loadDocuments() {
  await renderDocuments();
}

async function renderDocuments() {
  const list = document.getElementById("documents-list");
  const items = await api.get("/api/documents");
  if (items.length === 0) {
    list.innerHTML = `<div class="empty-state">No documents uploaded yet.</div>`;
    return;
  }
  list.innerHTML = items.map((d) => `
    <div class="list-item list-item-header">
      <div>
        <strong>${escapeHtml(d.title)}</strong>
        <p class="text-muted">${escapeHtml(statusLabel(d.category))} &middot; ${formatDate(d.uploaded_at)}</p>
      </div>
      <div class="btn-row">
        <a class="btn btn-sm btn-secondary" href="${API_BASE}/api/documents/${d.id}/file" target="_blank" rel="noopener">View</a>
        <button class="btn-sm btn-danger" data-delete-document="${d.id}">Delete</button>
      </div>
    </div>
  `).join("");

  list.querySelectorAll("[data-delete-document]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Delete this document?")) return;
      try {
        await api.delete(`/api/documents/${btn.dataset.deleteDocument}`);
        await renderDocuments();
      } catch (err) {
        showAlert(alertBox, err.message || "Could not delete document.");
      }
    });
  });
}

document.getElementById("document-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById("doc-file");
  if (!fileInput.files[0]) return;
  const form = new FormData();
  form.append("title", document.getElementById("doc-title").value.trim());
  form.append("category", document.getElementById("doc-category").value);
  form.append("file", fileInput.files[0]);
  try {
    await api.postForm("/api/documents", form);
    e.target.reset();
    await renderDocuments();
    showAlert(alertBox, "Document uploaded.", "success");
  } catch (err) {
    showAlert(alertBox, err.message || "Could not upload document.");
  }
});

// ---------- Settings ----------
async function loadSettings() {
  const contact = await api.get("/api/groups/owner-contact");
  document.getElementById("contact-phone").value = contact.phone || "";
  document.getElementById("contact-email").value = contact.contact_email || "";
}

document.getElementById("rotate-key-btn").addEventListener("click", async () => {
  if (!confirm("Rotate the access key? The old key will stop working immediately.")) return;
  try {
    const result = await api.post("/api/groups/access-key/rotate", {});
    document.getElementById("rotate-result").innerHTML = `
      <div class="alert success">
        New access key: <span class="key-display">${escapeHtml(result.access_key)}</span>
      </div>
    `;
  } catch (err) {
    showAlert(alertBox, err.message || "Could not rotate access key.");
  }
});

document.getElementById("contact-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    phone: document.getElementById("contact-phone").value.trim() || null,
    contact_email: document.getElementById("contact-email").value.trim() || null,
  };
  try {
    await api.put("/api/groups/owner-contact", payload);
    showAlert(alertBox, "Contact info saved.", "success");
  } catch (err) {
    showAlert(alertBox, err.message || "Could not save contact info.");
  }
});

// ---------- Init ----------
(async () => {
  const me = await guardPage({ requireRole: "owner", requireGroup: true });
  if (!me) return;
  document.getElementById("user-name").textContent = me.name;
  document.getElementById("welcome-line").textContent = `Welcome, ${me.name}.`;
  await loadTab("overview");
})();

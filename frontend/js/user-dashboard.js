const alertBox = document.getElementById("alert-box");
const tabs = document.getElementById("tabs");
const panels = {
  food: document.getElementById("panel-food"),
  issues: document.getElementById("panel-issues"),
  announcements: document.getElementById("panel-announcements"),
  rent: document.getElementById("panel-rent"),
  documents: document.getElementById("panel-documents"),
  owner: document.getElementById("panel-owner"),
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

const loaded = new Set();

async function loadTab(name) {
  if (loaded.has(name)) return;
  loaded.add(name);
  try {
    if (name === "food") await loadFood();
    if (name === "issues") await loadIssues();
    if (name === "announcements") await loadAnnouncements();
    if (name === "rent") await loadRent();
    if (name === "documents") await loadDocuments();
    if (name === "owner") await loadOwnerContact();
  } catch (err) {
    loaded.delete(name);
    showAlert(alertBox, err.message || "Something went wrong loading this section.");
  }
}

// ---------- Food ----------
let currentMenu = null;

async function loadFood() {
  const container = document.getElementById("food-content");
  currentMenu = await api.get("/api/food/today");
  document.getElementById("food-date-heading").textContent =
    "Today's Menu — " + new Date().toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });

  if (!currentMenu) {
    container.innerHTML = `<div class="empty-state">No menu has been posted for today yet.</div>`;
    return;
  }

  container.innerHTML = `
    <div class="grid cols-2" style="margin-bottom:1rem;">
      <div><strong>Breakfast</strong><p>${escapeHtml(currentMenu.breakfast || "—")}</p></div>
      <div><strong>Lunch</strong><p>${escapeHtml(currentMenu.lunch || "—")}</p></div>
      <div><strong>Dinner</strong><p>${escapeHtml(currentMenu.dinner || "—")}</p></div>
    </div>
    <h3>Give Feedback</h3>
    <form id="feedback-form">
      <div class="field">
        <label for="feedback-rating">Rating</label>
        <select id="feedback-rating">
          <option value="good">Good</option>
          <option value="average">Average</option>
          <option value="bad">Bad</option>
        </select>
      </div>
      <div class="field">
        <label for="feedback-comment">Comment (optional)</label>
        <textarea id="feedback-comment" rows="2" maxlength="1000"></textarea>
      </div>
      <button type="submit">Send Feedback</button>
    </form>
    <div id="feedback-result"></div>
  `;

  document.getElementById("feedback-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const rating = document.getElementById("feedback-rating").value;
    const comment = document.getElementById("feedback-comment").value.trim() || null;
    try {
      await api.post(`/api/food/${currentMenu.id}/feedback`, { rating, comment });
      document.getElementById("feedback-result").innerHTML =
        `<div class="alert success">Thanks for your feedback.</div>`;
      e.target.reset();
    } catch (err) {
      document.getElementById("feedback-result").innerHTML =
        `<div class="alert error">${escapeHtml(err.message)}</div>`;
    }
  });
}

// ---------- Issues ----------
async function loadIssues() {
  await renderMyIssues();
}

async function renderMyIssues() {
  const list = document.getElementById("my-issues-list");
  const issues = await api.get("/api/issues/mine");
  if (issues.length === 0) {
    list.innerHTML = `<div class="empty-state">You haven't reported any issues yet.</div>`;
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
    </div>
  `).join("");
}

document.getElementById("issue-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData();
  form.append("category", document.getElementById("issue-category").value);
  form.append("description", document.getElementById("issue-description").value);
  const room = document.getElementById("issue-room").value.trim();
  if (room) form.append("room_number", room);
  const imageInput = document.getElementById("issue-image");
  if (imageInput.files[0]) form.append("image", imageInput.files[0]);

  const submitBtn = e.target.querySelector("button[type=submit]");
  submitBtn.disabled = true;
  try {
    await api.postForm("/api/issues", form);
    e.target.reset();
    loaded.delete("issues");
    await renderMyIssues();
    showAlert(alertBox, "Issue submitted.", "success");
  } catch (err) {
    showAlert(alertBox, err.message || "Could not submit issue.");
  } finally {
    submitBtn.disabled = false;
  }
});

// ---------- Announcements ----------
async function loadAnnouncements() {
  const list = document.getElementById("announcements-list");
  const items = await api.get("/api/announcements");
  if (items.length === 0) {
    list.innerHTML = `<div class="empty-state">No announcements yet.</div>`;
    return;
  }
  list.innerHTML = items.map((a) => `
    <div class="list-item">
      <div class="list-item-header">
        <strong>${escapeHtml(a.title)}</strong>
        ${badge(statusLabel(a.type), a.type)}
      </div>
      <p>${escapeHtml(a.message)}</p>
      <p class="text-muted">${formatDateTime(a.created_at)}</p>
    </div>
  `).join("");
}

// ---------- Rent ----------
async function loadRent() {
  const list = document.getElementById("rent-list");
  const items = await api.get("/api/rent/mine");
  if (items.length === 0) {
    list.innerHTML = `<div class="empty-state">No rent records yet.</div>`;
    return;
  }
  list.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Due date</th><th>Amount</th><th>Status</th></tr></thead>
        <tbody>
          ${items.map((r) => `
            <tr>
              <td>${formatDate(r.due_date)}</td>
              <td>${r.monthly_rent}</td>
              <td>${badge(statusLabel(r.status), r.status)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

// ---------- Documents ----------
async function loadDocuments() {
  const list = document.getElementById("documents-list");
  const items = await api.get("/api/documents");
  if (items.length === 0) {
    list.innerHTML = `<div class="empty-state">No documents have been shared yet.</div>`;
    return;
  }
  list.innerHTML = items.map((d) => `
    <div class="list-item list-item-header">
      <div>
        <strong>${escapeHtml(d.title)}</strong>
        <p class="text-muted">${escapeHtml(statusLabel(d.category))} &middot; ${formatDate(d.uploaded_at)}</p>
      </div>
      <a class="btn btn-sm btn-secondary" href="${API_BASE}/api/documents/${d.id}/file" target="_blank" rel="noopener">View</a>
    </div>
  `).join("");
}

// ---------- Owner Contact ----------
async function loadOwnerContact() {
  const el = document.getElementById("owner-contact");
  const contact = await api.get("/api/groups/owner-contact");
  el.innerHTML = `
    <p><strong>Name:</strong> ${escapeHtml(contact.name)}</p>
    ${contact.phone ? `<p><strong>Phone:</strong> ${escapeHtml(contact.phone)}</p>` : ""}
    ${contact.contact_email ? `<p><strong>Email:</strong> ${escapeHtml(contact.contact_email)}</p>` : ""}
  `;
}

// ---------- Init ----------
(async () => {
  const me = await guardPage({ requireRole: "user", requireGroup: true });
  if (!me) return;
  document.getElementById("user-name").textContent = me.name;
  document.getElementById("welcome-line").textContent = `Welcome, ${me.name}.`;
  await loadTab("food");
})();

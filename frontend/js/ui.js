function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function showAlert(container, message, type = "error") {
  if (!container) return;
  container.innerHTML = `<div class="alert ${type}">${escapeHtml(message)}</div>`;
  container.hidden = false;
}

function clearAlert(container) {
  if (!container) return;
  container.innerHTML = "";
  container.hidden = true;
}

function formatDate(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function formatDateTime(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function badge(text, cssClass) {
  return `<span class="badge ${cssClass}">${escapeHtml(text)}</span>`;
}

function statusLabel(status) {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

async function guardPage({ requireRole, requireGroup } = {}) {
  let me;
  try {
    me = await api.get("/api/auth/me");
  } catch (e) {
    window.location.href = "index.html";
    return null;
  }

  if (requireRole && me.role !== requireRole) {
    window.location.href = me.role === "owner" ? "owner-dashboard.html" : "user-dashboard.html";
    return null;
  }

  if (requireGroup) {
    try {
      const status = await api.get("/api/terms/status");
      if (!status.accepted) {
        window.location.href = "terms.html";
        return null;
      }
    } catch (e) {
      // terms endpoint should always work if authenticated; ignore otherwise
    }

    if (!me.group_id) {
      window.location.href = "join.html";
      return null;
    }
  }

  return me;
}

async function logout() {
  try {
    await api.post("/api/auth/logout");
  } finally {
    window.location.href = "index.html";
  }
}

const APP_VERSION = "v1.0.0";

function renderFooter() {
  const placeholder = document.getElementById("app-footer");
  if (!placeholder) return;

  placeholder.innerHTML = `
    <div class="app-footer-inner">
      <span>&copy; 2026 POV-ZEN. All rights reserved.</span>
      <span class="app-footer-sep">&middot;</span>
      <span>${APP_VERSION}</span>
      <span class="app-footer-sep">&middot;</span>
      <a href="terms.html?view=1">Terms &amp; Conditions</a>
      <span class="app-footer-sep">&middot;</span>
      <a href="privacy.html">Privacy Policy</a>
      <span class="app-footer-sep">&middot;</span>
      <a href="#" id="footer-report-issue-link">Help / Report Website Issue</a>
    </div>
    <div id="report-issue-panel" class="report-issue-panel" hidden>
      <div class="card report-issue-card">
        <h3>Report a Website Issue</h3>
        <p class="text-muted">
          Use this for a problem with the website or app itself — not a PG
          maintenance issue. For plumbing, electricity, or similar, use
          "Report an Issue" in your dashboard instead.
        </p>
        <div id="report-issue-alert" hidden></div>
        <form id="report-issue-form">
          <div class="field">
            <label for="report-issue-description">What went wrong?</label>
            <textarea id="report-issue-description" rows="3" maxlength="2000" required></textarea>
          </div>
          <div class="field">
            <label for="report-issue-email">Your email (optional, for follow-up)</label>
            <input type="email" id="report-issue-email" />
          </div>
          <div class="btn-row">
            <button type="submit">Submit Report</button>
            <button type="button" class="btn-secondary" id="report-issue-cancel">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  `;

  const reportLink = document.getElementById("footer-report-issue-link");
  const panel = document.getElementById("report-issue-panel");
  const cancelBtn = document.getElementById("report-issue-cancel");
  const form = document.getElementById("report-issue-form");
  const alertBox = document.getElementById("report-issue-alert");

  reportLink.addEventListener("click", (e) => {
    e.preventDefault();
    panel.hidden = !panel.hidden;
  });

  cancelBtn.addEventListener("click", () => {
    panel.hidden = true;
    clearAlert(alertBox);
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlert(alertBox);
    const description = document.getElementById("report-issue-description").value.trim();
    const email = document.getElementById("report-issue-email").value.trim() || null;
    const submitBtn = form.querySelector("button[type=submit]");
    submitBtn.disabled = true;
    try {
      await api.post("/api/website-issues", {
        description,
        page_url: window.location.href,
        reporter_email: email,
      });
      form.reset();
      showAlert(alertBox, "Thanks — your report has been received.", "success");
      setTimeout(() => {
        panel.hidden = true;
        clearAlert(alertBox);
      }, 2500);
    } catch (err) {
      showAlert(alertBox, err.message || "Could not submit report.");
    } finally {
      submitBtn.disabled = false;
    }
  });
}

document.addEventListener("DOMContentLoaded", renderFooter);

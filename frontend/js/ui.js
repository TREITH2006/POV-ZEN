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

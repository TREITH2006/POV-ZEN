const alertBox = document.getElementById("alert-box");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const modeToggle = document.getElementById("mode-toggle");
const roleToggle = document.getElementById("role-toggle");
const ownerFields = document.getElementById("owner-fields");
const userFields = document.getElementById("user-fields");

let currentMode = "login";
let currentRole = "user";

modeToggle.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-mode]");
  if (!btn) return;
  currentMode = btn.dataset.mode;
  [...modeToggle.children].forEach((b) => b.classList.toggle("active", b === btn));
  loginForm.hidden = currentMode !== "login";
  registerForm.hidden = currentMode !== "register";
  clearAlert(alertBox);
});

roleToggle.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-role]");
  if (!btn) return;
  currentRole = btn.dataset.role;
  [...roleToggle.children].forEach((b) => b.classList.toggle("active", b === btn));
  ownerFields.hidden = currentRole !== "owner";
  userFields.hidden = currentRole !== "user";
});

async function afterAuth() {
  const me = await api.get("/api/auth/me");
  const termsStatus = await api.get("/api/terms/status");
  if (!termsStatus.accepted) {
    window.location.href = "terms.html";
    return;
  }
  if (me.role === "owner") {
    window.location.href = "owner-dashboard.html";
  } else if (me.group_id) {
    window.location.href = "user-dashboard.html";
  } else {
    window.location.href = "join.html";
  }
}

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearAlert(alertBox);
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const submitBtn = loginForm.querySelector("button[type=submit]");
  submitBtn.disabled = true;
  try {
    await api.post("/api/auth/login", { email, password });
    await afterAuth();
  } catch (err) {
    showAlert(alertBox, err.message || "Login failed.");
  } finally {
    submitBtn.disabled = false;
  }
});

registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearAlert(alertBox);
  const submitBtn = registerForm.querySelector("button[type=submit]");
  submitBtn.disabled = true;

  const name = document.getElementById("reg-name").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;
  const phone = document.getElementById("reg-phone").value.trim() || null;

  try {
    if (currentRole === "owner") {
      const pgName = document.getElementById("reg-pg-name").value.trim();
      if (!pgName) {
        showAlert(alertBox, "PG name is required.");
        return;
      }
      const result = await api.post("/api/auth/register/owner", {
        name, email, password, phone, pg_name: pgName,
      });
      sessionStorage.setItem("pov_zen_new_access_key", JSON.stringify(result));
      window.location.href = "access-key.html";
      return;
    }

    const roomNumber = document.getElementById("reg-room").value.trim() || null;
    const sharingRaw = document.getElementById("reg-sharing").value;
    const sharingType = sharingRaw ? Number(sharingRaw) : null;

    await api.post("/api/auth/register/user", {
      name, email, password, phone, room_number: roomNumber, sharing_type: sharingType,
    });
    await afterAuth();
  } catch (err) {
    showAlert(alertBox, err.message || "Registration failed.");
  } finally {
    submitBtn.disabled = false;
  }
});

// If already authenticated, skip the landing page entirely.
(async () => {
  try {
    await api.get("/api/auth/me");
    await afterAuth();
  } catch (e) {
    // not authenticated — stay on this page
  }
})();

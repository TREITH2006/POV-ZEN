// Central fetch wrapper. All backend calls go through here so credentialed
// cookies and consistent error handling stay in one place.
//
// API_BASE defaults to the backend on the SAME hostname the page itself was
// loaded from (just a different port), rather than a hardcoded "127.0.0.1".
// This matters because the auth cookie is SameSite=Strict: browsers treat
// "localhost" and "127.0.0.1" as different sites even on one machine, so a
// page opened via http://localhost:5500 calling a hardcoded
// http://127.0.0.1:8000 API was cross-site — the browser correctly refused
// to send the cookie, and login silently didn't stick. Deriving the host
// keeps frontend and backend same-site regardless of which of the two
// conventional local hostnames was used, without weakening SameSite at all.
// Production deployments (frontend/backend on different real domains) MUST
// set window.POV_ZEN_API_BASE explicitly before this script loads.
const API_BASE = window.POV_ZEN_API_BASE || (() => {
  const { protocol, hostname } = window.location;
  if (protocol === "http:" || protocol === "https:") {
    return `${protocol}//${hostname}:8000`;
  }
  // e.g. opened as a file:// page rather than served — fall back to a
  // sane default; same-site cookie behavior is not guaranteed in this case.
  return "http://127.0.0.1:8000";
})();

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function apiRequest(path, { method = "GET", json, form, headers = {} } = {}) {
  const opts = {
    method,
    credentials: "include",
    headers: { ...headers },
  };

  if (json !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(json);
  } else if (form !== undefined) {
    opts.body = form; // FormData sets its own multipart content-type
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, opts);
  } catch (networkErr) {
    throw new ApiError("Could not reach the server. Check your connection.", 0);
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const detail = typeof body === "object" && body && body.detail ? body.detail : response.statusText;
    throw new ApiError(detail, response.status);
  }

  return body;
}

const api = {
  get: (path) => apiRequest(path),
  post: (path, json) => apiRequest(path, { method: "POST", json }),
  postForm: (path, form) => apiRequest(path, { method: "POST", form }),
  put: (path, json) => apiRequest(path, { method: "PUT", json }),
  patch: (path, json) => apiRequest(path, { method: "PATCH", json }),
  delete: (path) => apiRequest(path, { method: "DELETE" }),
};

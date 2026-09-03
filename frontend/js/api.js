// Central fetch wrapper. All backend calls go through here so credentialed
// cookies and consistent error handling stay in one place.

const API_BASE = window.POV_ZEN_API_BASE || "http://127.0.0.1:8000";

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

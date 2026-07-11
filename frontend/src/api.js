const BASE = "/api";

function getCookie(name) {
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : null;
}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json" };
  const csrfToken = getCookie("csrftoken");
  if (csrfToken) {
    headers["X-CSRFToken"] = csrfToken;
  }
  const config = {
    credentials: "same-origin",
    headers,
    ...options,
  };
  const res = await fetch(BASE + path, config);
  if (res.status === 401) {
    window.location.href = "/";
    throw new ApiError("Unauthorized", 401);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.error || res.statusText, res.status);
  }
  if (res.status === 204) return null;
  return res.json();
}

function post(path, data) {
  return request(path, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

function put(path, data) {
  return request(path, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

function del(path) {
  return request(path, { method: "DELETE" });
}

function get(path) {
  return request(path);
}

async function initCsrf() {
  if (!getCookie("csrftoken")) {
    await fetch(BASE + "/csrf/", { credentials: "same-origin" });
  }
}

export const api = { get, post, put, del, initCsrf };
export { ApiError };

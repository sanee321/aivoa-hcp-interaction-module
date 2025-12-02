const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

async function request(path, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json();
}

export async function listHcps() {
  return request("/v1/hcps");
}

export async function createHcp(payload) {
  return request("/v1/hcps", { method: "POST", body: JSON.stringify(payload) });
}

export async function createInteraction(payload) {
  return request("/v1/interactions", { method: "POST", body: JSON.stringify(payload) });
}

export async function getInteraction(id) {
  return request(`/v1/interactions/${id}`);
}

export async function listInteractions(hcp_id) {
  const q = hcp_id ? `?hcp_id=${hcp_id}` : "";
  return request(`/v1/interactions${q}`);
}

export async function editInteraction(id, updates) {
  return request(`/v1/interactions/${id}`, { method: "PUT", body: JSON.stringify({ updates }) });
}

export async function processInteractionNow(id) {
  return request(`/v1/interactions/${id}/process`, { method: "POST" });
}

class BridgeApi {
  async request(path, options = {}) {
    const response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || data.message || `HTTP ${response.status}`);
    }
    return data;
  }

  health() {
    return this.request("/health");
  }

  start() {
    return this.request("/start", { method: "POST", body: "{}" });
  }

  stop() {
    return this.request("/stop", { method: "POST", body: "{}" });
  }

  listTools() {
    return this.request("/tools/list");
  }

  reloadTools() {
    return this.request("/tools/reload", { method: "POST", body: "{}" });
  }

  logs() {
    return this.request("/logs");
  }
}

window.bridgeApi = new BridgeApi();

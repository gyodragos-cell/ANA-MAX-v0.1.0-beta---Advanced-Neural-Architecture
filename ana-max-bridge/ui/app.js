const statusBadge = document.getElementById("statusBadge");
const summary = document.getElementById("summary");
const toolList = document.getElementById("toolList");
const logList = document.getElementById("logList");
const toolCount = document.getElementById("toolCount");
const logCount = document.getElementById("logCount");
const toolFilter = document.getElementById("toolFilter");

let tools = [];

function setStatus(online, text) {
  statusBadge.textContent = online ? "Online" : "Offline";
  statusBadge.dataset.state = online ? "online" : "offline";
  summary.textContent = text;
}

function renderTools() {
  const query = toolFilter.value.trim().toLowerCase();
  const filtered = tools.filter((tool) => {
    return `${tool.name} ${tool.description} ${tool.category}`.toLowerCase().includes(query);
  });
  toolCount.textContent = String(filtered.length);
  toolList.innerHTML = filtered.map((tool) => `
    <div class="tool">
      <strong>${escapeHtml(tool.name)}</strong>
      <span>${escapeHtml(tool.category || "ana-max")}</span>
      <p>${escapeHtml(tool.description || "")}</p>
    </div>
  `).join("");
}

function renderLogs(entries) {
  logCount.textContent = String(entries.length);
  logList.innerHTML = entries.slice().reverse().map((entry) => `
    <div class="log ${escapeHtml(entry.level)}">
      <span>${escapeHtml(entry.time || "")}</span>
      <strong>${escapeHtml(entry.level || "info")}</strong>
      <p>${escapeHtml(entry.message || "")}</p>
    </div>
  `).join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function refreshAll() {
  try {
    const health = await window.bridgeApi.health();
    setStatus(health.bridge_running, `ANA status ${health.ana_status_code}; ${health.tools_count} tools cached`);
  } catch (error) {
    setStatus(false, error.message);
  }

  try {
    const result = await window.bridgeApi.listTools();
    tools = result.tools || [];
    renderTools();
  } catch (error) {
    tools = [];
    renderTools();
  }

  try {
    const result = await window.bridgeApi.logs();
    renderLogs(result.logs || []);
  } catch (error) {
    renderLogs([{ level: "error", message: error.message, time: "" }]);
  }
}

document.getElementById("startBtn").addEventListener("click", async () => {
  await window.bridgeApi.start();
  await refreshAll();
});

document.getElementById("stopBtn").addEventListener("click", async () => {
  await window.bridgeApi.stop();
  await refreshAll();
});

document.getElementById("reloadBtn").addEventListener("click", async () => {
  const result = await window.bridgeApi.reloadTools();
  tools = result.tools || [];
  renderTools();
  await refreshAll();
});

toolFilter.addEventListener("input", renderTools);
refreshAll();
setInterval(refreshAll, 5000);

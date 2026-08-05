const state = {
  projects: [],
  loading: false,
};

const elements = {
  grid: document.querySelector("#project-grid"),
  summary: document.querySelector("#dashboard-summary"),
  total: document.querySelector("#metric-total"),
  warn: document.querySelector("#metric-warn"),
  dirty: document.querySelector("#metric-dirty"),
  refresh: document.querySelector("#refresh-projects"),
  token: document.querySelector("#api-token"),
  template: document.querySelector("#project-card-template"),
};

function formatValue(value, fallback = "Not available") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function statusClass(project) {
  return String(project.status || "").toLowerCase() === "ok" ? "ok" : "warn";
}

function formatDirtyState(value) {
  if (value === true) {
    return "Uncommitted changes";
  }
  if (value === false) {
    return "Clean";
  }
  return "Not available";
}

function updateMetrics(projects) {
  const warningCount = projects.filter((project) => project.status !== "OK").length;
  const dirtyCount = projects.filter((project) => project.dirty === true).length;

  elements.total.textContent = String(projects.length);
  elements.warn.textContent = String(warningCount);
  elements.dirty.textContent = String(dirtyCount);
  elements.summary.textContent = projects.length
    ? `${projects.length} projects tracked, ${warningCount} need review.`
    : "No projects configured yet.";
}

function renderEmpty() {
  elements.grid.textContent = "";
  const article = document.createElement("article");
  const heading = document.createElement("h2");
  const copy = document.createElement("p");

  article.className = "empty-state";
  heading.textContent = "No projects configured";
  copy.textContent = "Add local projects to the Project OS registry to populate this dashboard.";

  article.append(heading, copy);
  elements.grid.append(article);
}

function renderError(message) {
  elements.grid.textContent = "";
  const article = document.createElement("article");
  const heading = document.createElement("h2");
  const copy = document.createElement("p");

  article.className = "error-state";
  article.setAttribute("role", "alert");
  heading.textContent = "Project status unavailable";
  copy.textContent = message;

  article.append(heading, copy);
  elements.grid.append(article);
}

function renderProjects(projects) {
  elements.grid.innerHTML = "";
  if (!projects.length) {
    renderEmpty();
    return;
  }

  for (const project of projects) {
    const card = elements.template.content.firstElementChild.cloneNode(true);
    const pill = card.querySelector(".status-pill");

    card.querySelector(".project-name").textContent = project.name;
    card.querySelector(".project-kind").textContent = project.kind;
    pill.textContent = project.status || "WARN";
    pill.classList.add(statusClass(project));
    card.querySelector(".project-branch").textContent = formatValue(project.branch);
    card.querySelector(".project-dirty").textContent = formatDirtyState(project.dirty);
    card.querySelector(".project-commit").textContent = formatValue(project.latest_commit);
    card.querySelector(".project-path").textContent = project.path;
    card.querySelector(".next-action").textContent = project.warning || project.next_action;

    elements.grid.append(card);
  }
}

async function loadProjects() {
  if (state.loading) {
    return;
  }
  state.loading = true;
  elements.refresh.disabled = true;
  elements.summary.textContent = "Refreshing project status...";

  try {
    const token = elements.token.value.trim();
    if (token) {
      localStorage.setItem("vasyaApiToken", token);
    }
    const headers = token ? { "x-api-key": token } : {};
    const response = await fetch("/v1/projects/status", { headers });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    state.projects = Array.isArray(payload.items) ? payload.items : [];
    updateMetrics(state.projects);
    renderProjects(state.projects);
  } catch (error) {
    updateMetrics([]);
    renderError(error instanceof Error ? error.message : "Unknown error");
  } finally {
    state.loading = false;
    elements.refresh.disabled = false;
  }
}

elements.token.value = localStorage.getItem("vasyaApiToken") || "";
elements.refresh.addEventListener("click", loadProjects);
loadProjects();

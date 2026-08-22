const state = {
  projects: [],
  registryProjects: [],
  loading: false,
  editingId: null,
  deletingId: null,
};

const elements = {
  grid: document.querySelector("#project-grid"),
  summary: document.querySelector("#dashboard-summary"),
  total: document.querySelector("#metric-total"),
  warn: document.querySelector("#metric-warn"),
  dirty: document.querySelector("#metric-dirty"),
  refresh: document.querySelector("#refresh-projects"),
  token: document.querySelector("#api-token"),
  tokenForm: document.querySelector("#api-token-form"),
  template: document.querySelector("#project-card-template"),
  registryList: document.querySelector("#registry-list"),
  registryTemplate: document.querySelector("#registry-row-template"),
  registryFeedback: document.querySelector("#registry-feedback"),
  addProject: document.querySelector("#add-project"),
  projectDialog: document.querySelector("#project-dialog"),
  projectDialogTitle: document.querySelector("#project-dialog-title"),
  projectForm: document.querySelector("#project-form"),
  projectFormError: document.querySelector("#project-form-error"),
  projectId: document.querySelector("#project-id"),
  projectName: document.querySelector("#project-name"),
  projectPath: document.querySelector("#project-path"),
  projectKind: document.querySelector("#project-kind"),
  projectPriority: document.querySelector("#project-priority"),
  projectEnabled: document.querySelector("#project-enabled"),
  closeProjectDialog: document.querySelector("#close-project-dialog"),
  cancelProjectDialog: document.querySelector("#cancel-project-dialog"),
  saveProject: document.querySelector("#save-project"),
  deleteDialog: document.querySelector("#delete-project-dialog"),
  deleteCopy: document.querySelector("#delete-project-copy"),
  cancelDelete: document.querySelector("#cancel-delete-project"),
  confirmDelete: document.querySelector("#confirm-delete-project"),
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

function apiHeaders(hasBody = false) {
  const token = elements.token.value.trim();
  if (token) {
    localStorage.setItem("vasyaApiToken", token);
  } else {
    localStorage.removeItem("vasyaApiToken");
  }
  return {
    ...(token ? { "x-api-key": token } : {}),
    ...(hasBody ? { "Content-Type": "application/json" } : {}),
  };
}

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...apiHeaders(Boolean(options.body)),
      ...(options.headers || {}),
    },
  });
  let responsePayload = {};
  if (response.status !== 204) {
    try {
      responsePayload = await response.json();
    } catch (_error) {
      responsePayload = {};
    }
  }
  if (!response.ok) {
    const detail =
      typeof responsePayload.detail === "string"
        ? responsePayload.detail
        : `Request failed with HTTP ${response.status}.`;
    throw new Error(detail);
  }
  return responsePayload;
}

function errorMessage(error) {
  return error instanceof Error ? error.message : "Unknown error";
}

function updateMetrics(projects) {
  const warningCount = projects.filter((project) => project.status !== "OK").length;
  const dirtyCount = projects.filter((project) => project.dirty === true).length;

  elements.total.textContent = String(projects.length);
  elements.warn.textContent = String(warningCount);
  elements.dirty.textContent = String(dirtyCount);
  elements.summary.textContent = projects.length
    ? `${projects.length} projects tracked, ${warningCount} need review.`
    : "No enabled projects configured yet.";
}

function renderEmpty() {
  elements.grid.textContent = "";
  const article = document.createElement("article");
  const heading = document.createElement("h2");
  const copy = document.createElement("p");

  article.className = "empty-state";
  heading.textContent = "No enabled projects";
  copy.textContent = "Use Add project above to start tracking a local folder.";
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
  elements.grid.textContent = "";
  if (!projects.length) {
    renderEmpty();
    return;
  }

  for (const project of projects) {
    const card = elements.template.content.firstElementChild.cloneNode(true);
    const pill = card.querySelector(".status-pill");

    card.id = `project-${project.id}`;
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

function setRegistryFeedback(message, tone = "") {
  elements.registryFeedback.textContent = message;
  elements.registryFeedback.className = "registry-feedback";
  if (tone) {
    elements.registryFeedback.classList.add(tone);
  }
}

function renderRegistryMessage(title, copy, isError = false) {
  elements.registryList.textContent = "";
  const message = document.createElement("div");
  const heading = document.createElement("strong");
  const body = document.createElement("p");

  message.className = `registry-message${isError ? " is-error" : ""}`;
  if (isError) {
    message.setAttribute("role", "alert");
  }
  heading.textContent = title;
  body.textContent = copy;
  message.append(heading, body);
  elements.registryList.append(message);
}

function renderRegistry(projects) {
  elements.registryList.textContent = "";
  if (!projects.length) {
    renderRegistryMessage(
      "No saved projects",
      "Add a local folder when you are ready. New installations stay empty by default.",
    );
    return;
  }

  for (const project of projects) {
    const row = elements.registryTemplate.content.firstElementChild.cloneNode(true);
    const enabled = row.querySelector(".registry-enabled");
    const edit = row.querySelector(".edit-project");
    const remove = row.querySelector(".remove-project");

    row.dataset.projectId = project.id;
    row.classList.toggle("is-disabled", !project.enabled);
    row.querySelector(".registry-name").textContent = project.name;
    row.querySelector(".registry-kind").textContent = `${project.kind} · priority ${project.priority}`;
    row.querySelector(".registry-path").textContent = project.path;
    enabled.checked = project.enabled;
    enabled.setAttribute("aria-label", `Enable ${project.name}`);
    edit.setAttribute("aria-label", `Edit ${project.name}`);
    remove.setAttribute("aria-label", `Remove ${project.name}`);
    enabled.addEventListener("change", () => toggleProject(project, enabled));
    edit.addEventListener("click", () => openProjectDialog(project));
    remove.addEventListener("click", () => openDeleteDialog(project));
    elements.registryList.append(row);
  }
}

async function loadProjectStatus() {
  try {
    const payload = await requestJson("/v1/projects/status");
    state.projects = Array.isArray(payload.items) ? payload.items : [];
    updateMetrics(state.projects);
    renderProjects(state.projects);
  } catch (error) {
    updateMetrics([]);
    renderError(errorMessage(error));
  }
}

async function loadRegistry() {
  setRegistryFeedback("Refreshing registry...");
  try {
    const payload = await requestJson("/v1/projects");
    state.registryProjects = Array.isArray(payload.items) ? payload.items : [];
    renderRegistry(state.registryProjects);
    setRegistryFeedback(
      state.registryProjects.length
        ? `${state.registryProjects.length} local projects saved.`
        : "Registry ready for your first project.",
    );
  } catch (error) {
    state.registryProjects = [];
    renderRegistryMessage("Registry unavailable", errorMessage(error), true);
    setRegistryFeedback("Could not refresh the registry.", "is-error");
  }
}

async function refreshDashboard() {
  if (state.loading) {
    return;
  }
  state.loading = true;
  elements.refresh.disabled = true;
  elements.summary.textContent = "Refreshing project status...";
  try {
    await Promise.all([loadProjectStatus(), loadRegistry()]);
  } finally {
    state.loading = false;
    elements.refresh.disabled = false;
  }
}

function openProjectDialog(project = null) {
  state.editingId = project ? project.id : null;
  elements.projectForm.reset();
  elements.projectFormError.hidden = true;
  elements.projectId.disabled = Boolean(project);
  elements.projectId.value = project ? project.id : "";
  elements.projectName.value = project ? project.name : "";
  elements.projectPath.value = project ? project.path : "";
  elements.projectKind.value = project ? project.kind : "python";
  elements.projectPriority.value = project ? String(project.priority) : "100";
  elements.projectEnabled.checked = project ? project.enabled : true;
  elements.projectDialogTitle.textContent = project ? "Edit project" : "Add project";
  elements.saveProject.textContent = project ? "Save changes" : "Save project";
  elements.projectDialog.showModal();
  (project ? elements.projectName : elements.projectId).focus();
}

function closeProjectDialog() {
  elements.projectDialog.close();
}

async function submitProject(event) {
  event.preventDefault();
  const isEditing = Boolean(state.editingId);
  const payload = {
    name: elements.projectName.value.trim(),
    path: elements.projectPath.value.trim(),
    kind: elements.projectKind.value.trim(),
    priority: Number(elements.projectPriority.value),
    enabled: elements.projectEnabled.checked,
  };
  if (!isEditing) {
    payload.id = elements.projectId.value.trim();
  }

  elements.saveProject.disabled = true;
  elements.projectFormError.hidden = true;
  try {
    await requestJson(
      isEditing ? `/v1/projects/${encodeURIComponent(state.editingId)}` : "/v1/projects",
      {
        method: isEditing ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      },
    );
    closeProjectDialog();
    await refreshDashboard();
    setRegistryFeedback(isEditing ? "Project updated." : "Project added.", "is-success");
  } catch (error) {
    elements.projectFormError.textContent = errorMessage(error);
    elements.projectFormError.hidden = false;
  } finally {
    elements.saveProject.disabled = false;
  }
}

async function toggleProject(project, checkbox) {
  checkbox.disabled = true;
  try {
    await requestJson(`/v1/projects/${encodeURIComponent(project.id)}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled: checkbox.checked }),
    });
    await refreshDashboard();
    setRegistryFeedback(
      checkbox.checked ? `${project.name} enabled.` : `${project.name} paused.`,
      "is-success",
    );
  } catch (error) {
    checkbox.checked = project.enabled;
    setRegistryFeedback(errorMessage(error), "is-error");
  } finally {
    checkbox.disabled = false;
  }
}

function openDeleteDialog(project) {
  state.deletingId = project.id;
  elements.deleteCopy.textContent = `Remove ${project.name} from Vasya Project OS?`;
  elements.deleteDialog.showModal();
  elements.cancelDelete.focus();
}

async function deleteProject() {
  if (!state.deletingId) {
    return;
  }
  const project = state.registryProjects.find((item) => item.id === state.deletingId);
  elements.confirmDelete.disabled = true;
  try {
    await requestJson(`/v1/projects/${encodeURIComponent(state.deletingId)}`, {
      method: "DELETE",
    });
    elements.deleteDialog.close();
    await refreshDashboard();
    setRegistryFeedback(`${project ? project.name : "Project"} removed.`, "is-success");
  } catch (error) {
    elements.deleteDialog.close();
    setRegistryFeedback(errorMessage(error), "is-error");
  } finally {
    elements.confirmDelete.disabled = false;
    state.deletingId = null;
  }
}

elements.token.value = localStorage.getItem("vasyaApiToken") || "";
elements.refresh.addEventListener("click", refreshDashboard);
elements.tokenForm.addEventListener("submit", (event) => {
  event.preventDefault();
  refreshDashboard();
});
elements.addProject.addEventListener("click", () => openProjectDialog());
elements.projectForm.addEventListener("submit", submitProject);
elements.closeProjectDialog.addEventListener("click", closeProjectDialog);
elements.cancelProjectDialog.addEventListener("click", closeProjectDialog);
elements.cancelDelete.addEventListener("click", () => elements.deleteDialog.close());
elements.confirmDelete.addEventListener("click", deleteProject);
elements.projectDialog.addEventListener("close", () => {
  state.editingId = null;
});
elements.deleteDialog.addEventListener("close", () => {
  state.deletingId = null;
});
refreshDashboard();

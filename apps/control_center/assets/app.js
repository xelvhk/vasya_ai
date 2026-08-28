import {
  clearApiToken,
  createApiClient,
  loadApiToken,
  saveApiToken,
} from "./api-client.js";
import { createDashboardView } from "./dashboard-view.js";
import { createProjectActions } from "./project-actions.js";
import { createRegistryView } from "./registry-view.js";

const state = {
  registryProjects: [],
  loading: false,
};

const elements = {
  grid: document.querySelector("#project-grid"),
  summary: document.querySelector("#dashboard-summary"),
  total: document.querySelector("#metric-total"),
  warn: document.querySelector("#metric-warn"),
  dirty: document.querySelector("#metric-dirty"),
  refresh: document.querySelector("#refresh-projects"),
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
  connectionDialog: document.querySelector("#connection-dialog"),
  connectionForm: document.querySelector("#connection-form"),
  connectionFeedback: document.querySelector("#connection-feedback"),
  token: document.querySelector("#api-token"),
  openConnection: document.querySelector("#open-connection-dialog"),
  closeConnection: document.querySelector("#close-connection-dialog"),
  cancelConnection: document.querySelector("#cancel-connection-dialog"),
  clearToken: document.querySelector("#clear-api-token"),
};

function errorMessage(error) {
  return error instanceof Error ? error.message : "Неизвестная ошибка";
}

function setRegistryFeedback(message, tone = "") {
  elements.registryFeedback.textContent = message;
  elements.registryFeedback.className = "registry-feedback";
  if (tone) {
    elements.registryFeedback.classList.add(tone);
  }
}

function showConnectionDialog(message = "") {
  elements.connectionFeedback.textContent = message;
  if (!elements.connectionDialog.open) {
    elements.connectionDialog.showModal();
  }
  elements.token.focus();
}

const api = createApiClient({
  getToken: () => elements.token.value,
  onUnauthorized: () => showConnectionDialog("Проверьте API-токен и подключитесь снова."),
});
const dashboardView = createDashboardView(elements);
let registryView;

async function loadProjectStatus() {
  try {
    const payload = await api.requestJson("/v1/projects/status");
    const projects = Array.isArray(payload.items) ? payload.items : [];
    dashboardView.updateMetrics(projects);
    dashboardView.renderProjects(projects);
  } catch (error) {
    dashboardView.updateMetrics([]);
    dashboardView.renderError(errorMessage(error));
  }
}

async function loadRegistry() {
  setRegistryFeedback("Обновляю реестр...");
  try {
    const payload = await api.requestJson("/v1/projects");
    state.registryProjects = Array.isArray(payload.items) ? payload.items : [];
    registryView.render(state.registryProjects);
    setRegistryFeedback(
      state.registryProjects.length
        ? "Сохранено локальных проектов: " + state.registryProjects.length + "."
        : "Реестр готов к добавлению первого проекта.",
    );
  } catch (error) {
    state.registryProjects = [];
    registryView.renderMessage("Реестр недоступен", errorMessage(error), true);
    setRegistryFeedback("Не удалось обновить реестр.", "is-error");
  }
}

async function refreshDashboard() {
  if (state.loading) {
    return;
  }
  state.loading = true;
  elements.refresh.disabled = true;
  elements.summary.textContent = "Обновляю состояние проектов...";
  try {
    await Promise.all([loadProjectStatus(), loadRegistry()]);
  } finally {
    state.loading = false;
    elements.refresh.disabled = false;
  }
}

const projectActions = createProjectActions({
  api,
  elements,
  getRegistryProjects: () => state.registryProjects,
  refreshDashboard,
  setRegistryFeedback,
});
registryView = createRegistryView(elements, projectActions);
projectActions.bind();

elements.token.value = loadApiToken();
elements.refresh.addEventListener("click", refreshDashboard);
elements.openConnection.addEventListener("click", () => showConnectionDialog());
elements.closeConnection.addEventListener("click", () => elements.connectionDialog.close());
elements.cancelConnection.addEventListener("click", () => elements.connectionDialog.close());
elements.connectionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  saveApiToken(elements.token.value);
  elements.connectionDialog.close();
  await refreshDashboard();
});
elements.clearToken.addEventListener("click", async () => {
  clearApiToken();
  elements.token.value = "";
  elements.connectionDialog.close();
  await refreshDashboard();
});

refreshDashboard();

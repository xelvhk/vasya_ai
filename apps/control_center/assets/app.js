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
  chatForm: document.querySelector("#agent-chat-form"),
  chatAgent: document.querySelector("#agent-chat-agent"),
  chatInput: document.querySelector("#agent-chat-input"),
  chatSubmit: document.querySelector("#agent-chat-submit"),
  chatResult: document.querySelector("#agent-chat-result"),
  chatAnswer: document.querySelector("#agent-chat-answer"),
  chatSources: document.querySelector("#agent-chat-sources"),
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

elements.chatAgent.addEventListener("change", () => {
  elements.chatInput.placeholder = elements.chatAgent.value === "knowledge"
    ? "Что известно о локальном индексе?"
    : "Покажи сводку проектов";
});

elements.chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = elements.chatInput.value.trim();
  if (!question) {
    return;
  }
  elements.chatSubmit.disabled = true;
  elements.chatResult.hidden = false;
  const agent = elements.chatAgent.value;
  elements.chatAnswer.textContent = agent === "knowledge" ? "Ищу в заметках..." : "Проверяю проекты...";
  elements.chatSources.replaceChildren();
  try {
    const payload = await api.requestJson("/v1/chat", {
      method: "POST",
      body: JSON.stringify({ text: question, agent }),
    });
    elements.chatAnswer.textContent = payload.response || "Ответ пуст.";
    for (const source of payload.sources || []) {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = source.url;
      link.textContent = source.title;
      item.append(link);
      const timestamp = source.modified_at || source.observed_at;
      if (timestamp) {
        const checkedAt = new Date(timestamp);
        if (!Number.isNaN(checkedAt.getTime())) {
          const time = document.createElement("time");
          time.dateTime = timestamp;
          time.textContent = ` · ${source.modified_at ? "изменено" : "проверено"} ${checkedAt.toLocaleString("ru-RU")}`;
          item.append(time);
        }
      }
      elements.chatSources.append(item);
    }
  } catch (error) {
    elements.chatAnswer.textContent = errorMessage(error);
  } finally {
    elements.chatSubmit.disabled = false;
  }
});

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

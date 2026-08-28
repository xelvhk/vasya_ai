function formatValue(value, fallback = "Нет данных") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function statusClass(project) {
  return String(project.status || "").toLowerCase() === "ok" ? "ok" : "warn";
}

function statusLabel(project) {
  return statusClass(project) === "ok" ? "Готов" : "Проверить";
}

function formatDirtyState(value) {
  if (value === true) {
    return "Есть незакоммиченные изменения";
  }
  if (value === false) {
    return "Чисто";
  }
  return "Нет данных";
}

export function createDashboardView(elements) {
  function updateMetrics(projects) {
    const warningCount = projects.filter((project) => project.status !== "OK").length;
    const dirtyCount = projects.filter((project) => project.dirty === true).length;

    elements.total.textContent = String(projects.length);
    elements.warn.textContent = String(warningCount);
    elements.dirty.textContent = String(dirtyCount);
    elements.summary.textContent = projects.length
      ? "Отслеживается проектов: " + projects.length + ". Требуют внимания: " + warningCount + "."
      : "Включённых проектов пока нет.";
  }

  function renderMessage(title, copy, isError = false) {
    elements.grid.textContent = "";
    const article = document.createElement("article");
    const heading = document.createElement("h3");
    const body = document.createElement("p");

    article.className = isError ? "error-state" : "empty-state";
    if (isError) {
      article.setAttribute("role", "alert");
    }
    heading.textContent = title;
    body.textContent = copy;
    article.append(heading, body);
    elements.grid.append(article);
  }

  function renderProjects(projects) {
    elements.grid.textContent = "";
    if (!projects.length) {
      renderMessage(
        "Нет включённых проектов",
        "Добавьте локальную папку, чтобы начать отслеживание.",
      );
      return;
    }

    for (const project of projects) {
      const card = elements.template.content.firstElementChild.cloneNode(true);
      const pill = card.querySelector(".status-pill");

      card.id = "project-" + project.id;
      card.querySelector(".project-name").textContent = project.name;
      card.querySelector(".project-kind").textContent = project.kind;
      pill.textContent = statusLabel(project);
      pill.classList.add(statusClass(project));
      card.querySelector(".project-branch").textContent = formatValue(project.branch);
      card.querySelector(".project-dirty").textContent = formatDirtyState(project.dirty);
      card.querySelector(".project-commit").textContent = formatValue(project.latest_commit);
      card.querySelector(".project-path").textContent = project.path;
      card.querySelector(".next-action").textContent =
        project.warning || project.next_action || "Следующих действий нет.";
      elements.grid.append(card);
    }
  }

  function renderError(message) {
    renderMessage("Статус проектов недоступен", message, true);
  }

  return { renderError, renderProjects, updateMetrics };
}


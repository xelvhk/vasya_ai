export function createRegistryView(elements, actions) {
  function renderMessage(title, copy, isError = false) {
    elements.registryList.textContent = "";
    const message = document.createElement("div");
    const heading = document.createElement("strong");
    const body = document.createElement("p");

    message.className = "registry-message" + (isError ? " is-error" : "");
    if (isError) {
      message.setAttribute("role", "alert");
    }
    heading.textContent = title;
    body.textContent = copy;
    message.append(heading, body);
    elements.registryList.append(message);
  }

  function render(projects) {
    elements.registryList.textContent = "";
    if (!projects.length) {
      renderMessage(
        "Сохранённых проектов нет",
        "Добавьте локальную папку, когда будете готовы. Новая установка всегда начинает с пустого реестра.",
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
      row.querySelector(".registry-kind").textContent =
        project.kind + " · приоритет " + project.priority;
      row.querySelector(".registry-path").textContent = project.path;
      enabled.checked = project.enabled;
      enabled.setAttribute("aria-label", "Включить " + project.name);
      edit.setAttribute("aria-label", "Изменить " + project.name);
      remove.setAttribute("aria-label", "Удалить " + project.name);
      enabled.addEventListener("change", () => actions.toggleProject(project, enabled));
      edit.addEventListener("click", () => actions.openProjectDialog(project));
      remove.addEventListener("click", () => actions.openDeleteDialog(project));
      elements.registryList.append(row);
    }
  }

  return { render, renderMessage };
}


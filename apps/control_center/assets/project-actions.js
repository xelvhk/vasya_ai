function errorMessage(error) {
  return error instanceof Error ? error.message : "Неизвестная ошибка";
}

export function createProjectActions({
  api,
  elements,
  getRegistryProjects,
  refreshDashboard,
  setRegistryFeedback,
}) {
  let editingId = null;
  let deletingId = null;

  function clearProjectFormError() {
    elements.projectFormError.hidden = true;
    elements.projectFormError.textContent = "";
  }

  function openProjectDialog(project = null) {
    editingId = project ? project.id : null;
    elements.projectForm.reset();
    clearProjectFormError();
    elements.projectId.disabled = Boolean(project);
    elements.projectId.value = project ? project.id : "";
    elements.projectName.value = project ? project.name : "";
    elements.projectPath.value = project ? project.path : "";
    elements.projectKind.value = project ? project.kind : "python";
    elements.projectPriority.value = project ? String(project.priority) : "100";
    elements.projectEnabled.checked = project ? project.enabled : true;
    elements.projectDialogTitle.textContent =
      project ? "Изменить проект" : "Добавить проект";
    elements.saveProject.textContent =
      project ? "Сохранить изменения" : "Сохранить проект";
    elements.projectDialog.showModal();
    (project ? elements.projectName : elements.projectId).focus();
  }

  function closeProjectDialog() {
    elements.projectDialog.close();
  }

  async function submitProject(event) {
    event.preventDefault();
    const isEditing = Boolean(editingId);
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
    clearProjectFormError();
    try {
      await api.requestJson(
        isEditing ? "/v1/projects/" + encodeURIComponent(editingId) : "/v1/projects",
        {
          method: isEditing ? "PATCH" : "POST",
          body: JSON.stringify(payload),
        },
      );
      closeProjectDialog();
      await refreshDashboard();
      setRegistryFeedback(
        isEditing ? "Проект обновлён." : "Проект добавлен.",
        "is-success",
      );
    } catch (error) {
      elements.projectFormError.textContent = errorMessage(error);
      elements.projectFormError.hidden = false;
      elements.projectFormError.focus();
    } finally {
      elements.saveProject.disabled = false;
    }
  }

  async function toggleProject(project, checkbox) {
    checkbox.disabled = true;
    try {
      await api.requestJson("/v1/projects/" + encodeURIComponent(project.id), {
        method: "PATCH",
        body: JSON.stringify({ enabled: checkbox.checked }),
      });
      await refreshDashboard();
      setRegistryFeedback(
        checkbox.checked ? project.name + " включён." : project.name + " приостановлен.",
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
    deletingId = project.id;
    elements.deleteCopy.textContent =
      "Удалить " + project.name + " из Vasya Project OS?";
    elements.deleteDialog.showModal();
    elements.cancelDelete.focus();
  }

  async function deleteProject() {
    if (!deletingId) {
      return;
    }
    const project = getRegistryProjects().find((item) => item.id === deletingId);
    elements.confirmDelete.disabled = true;
    try {
      await api.requestJson("/v1/projects/" + encodeURIComponent(deletingId), {
        method: "DELETE",
      });
      elements.deleteDialog.close();
      await refreshDashboard();
      setRegistryFeedback(
        (project ? project.name : "Проект") + " удалён.",
        "is-success",
      );
    } catch (error) {
      elements.deleteDialog.close();
      setRegistryFeedback(errorMessage(error), "is-error");
    } finally {
      elements.confirmDelete.disabled = false;
      deletingId = null;
    }
  }

  function bind() {
    elements.addProject.addEventListener("click", () => openProjectDialog());
    elements.projectForm.addEventListener("submit", submitProject);
    elements.closeProjectDialog.addEventListener("click", closeProjectDialog);
    elements.cancelProjectDialog.addEventListener("click", closeProjectDialog);
    elements.cancelDelete.addEventListener(
      "click",
      () => elements.deleteDialog.close(),
    );
    elements.confirmDelete.addEventListener("click", deleteProject);
    elements.projectDialog.addEventListener("close", () => {
      editingId = null;
    });
    elements.deleteDialog.addEventListener("close", () => {
      deletingId = null;
    });
  }

  return { bind, openDeleteDialog, openProjectDialog, toggleProject };
}


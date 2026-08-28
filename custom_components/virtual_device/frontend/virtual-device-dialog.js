import {
  createVirtualDevice,
  updateVirtualDevice,
  addVirtualEntity,
  updateVirtualEntity,
  deleteVirtualEntity,
  synchronizeHistory,
  loadSourceEntities,
} from "./virtual-device-api.js";

const FILTER_OPERATORS = [
  "equals", "not_equals", "contains", "not_contains", "starts_with",
  "ends_with", "regex", "is_empty", "is_not_empty",
];

function filterEditorHtml(kind, filter, diagnostics, t) {
  const current = filter || {mode: kind === "include" ? "all" : "any", conditions: []};
  const noCandidates = diagnostics?.base_candidate_count === 0;
  const rows = current.conditions.map((condition, index) => {
    const diagnostic = diagnostics?.[kind]?.[index];
    const fieldWarning = !noCandidates && diagnostic && !diagnostic.field_hit;
    const valueWarning = !noCandidates && diagnostic?.field_hit && !diagnostic.rule_hit;
    const valueless = condition.operator === "is_empty" || condition.operator === "is_not_empty";
    return `<div class="filter-condition" data-index="${index}">
      <input class="filter-field ${fieldWarning ? "filter-warning" : ""}" type="text"
        value="${escapeAttribute(condition.field || "")}" placeholder="entity.entity_category"
        title="${fieldWarning ? escapeAttribute(t("filters.attribute_not_found")) : ""}" />
      <select class="filter-operator">${FILTER_OPERATORS.map((operator) =>
        `<option value="${operator}" ${operator === condition.operator ? "selected" : ""}>${escapeHtml(t(`filters.operators.${operator}`))}</option>`
      ).join("")}</select>
      <input class="filter-value ${valueWarning ? "filter-warning" : ""}" type="text"
        value="${escapeAttribute(condition.value ?? "")}" ${valueless ? "disabled" : ""}
        title="${valueWarning ? escapeAttribute(t("filters.condition_not_matched")) : ""}" />
      <button type="button" class="remove-filter-condition" title="${escapeAttribute(t("filters.remove"))}">×</button>
    </div>`;
  }).join("");
  return `<section class="filter-editor" data-kind="${kind}">
    <h3>${t(`filters.${kind}_title`)}</h3>
    <label>${t("filters.match")}
      <select class="filter-mode"><option value="all" ${current.mode === "all" ? "selected" : ""}>${t("filters.all")}</option>
      <option value="any" ${current.mode === "any" ? "selected" : ""}>${t("filters.any")}</option></select>
    </label>
    ${noCandidates ? `<div class="filter-neutral">${t("filters.no_candidates")}</div>` : ""}
    <div class="filter-conditions">${rows}</div>
    <button type="button" class="add-filter-condition">+ ${t("filters.add")}</button>
  </section>`;
}

function setupFilterEditors(dialog, t) {
  dialog.querySelectorAll(".filter-editor").forEach((editor) => {
    const conditions = editor.querySelector(".filter-conditions");
    const bindRow = (row) => {
      row.querySelector(".remove-filter-condition").addEventListener("click", () => row.remove());
      row.querySelector(".filter-operator").addEventListener("change", (event) => {
        row.querySelector(".filter-value").disabled = ["is_empty", "is_not_empty"].includes(event.target.value);
      });
    };
    conditions.querySelectorAll(".filter-condition").forEach(bindRow);
    editor.querySelector(".add-filter-condition").addEventListener("click", () => {
      const wrapper = document.createElement("div");
      wrapper.innerHTML = filterEditorHtml(editor.dataset.kind, {mode: "all", conditions: [{field: "", operator: "equals", value: ""}]}, null, t);
      const row = wrapper.querySelector(".filter-condition");
      conditions.appendChild(row);
      bindRow(row);
      row.querySelector(".filter-field").focus();
    });
  });
}

function collectFilter(dialog, kind) {
  const editor = dialog.querySelector(`.filter-editor[data-kind="${kind}"]`);
  return {
    mode: editor.querySelector(".filter-mode").value,
    conditions: [...editor.querySelectorAll(".filter-condition")].map((row) => {
      const operator = row.querySelector(".filter-operator").value;
      const condition = {field: row.querySelector(".filter-field").value.trim(), operator};
      if (!["is_empty", "is_not_empty"].includes(operator)) condition.value = row.querySelector(".filter-value").value;
      return condition;
    }),
  };
}
import {resolveEntityName} from "./virtual-device-translations.js";


export async function openSourceEntitiesDialog(component, device, entity) {
  const t = component._t;
  const dialog = document.createElement("div");
  dialog.className = "dialog-backdrop";
  dialog.innerHTML = `
    <div class="dialog" role="dialog" aria-modal="true">
      <div class="dialog-title">
        ${escapeHtml(`${device.name || device.id} – ${entity.name || entity.id}`)}
      </div>
      <div class="dialog-content source-dialog-content">
        <div class="source-loading">${t("loading")}</div>
      </div>
      <div class="dialog-actions">
        <button class="close-button">${t("actions.close")}</button>
      </div>
    </div>
  `;
  component.appendChild(dialog);
  const close = () => dialog.remove();
  dialog.querySelector(".close-button").addEventListener("click", close);
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) close();
  });

  try {
    const result = await loadSourceEntities(component._hass, device.id, entity.id);
    const content = dialog.querySelector(".source-dialog-content");
    content.innerHTML = result.sources.length === 0
      ? `<div class="entities-empty">${t("empty.assigned_entities")}</div>`
      : `
        <table class="source-table">
          <thead><tr>
            <th>${t("fields.entity")}</th>
            <th>${t("fields.device")}</th>
          </tr></thead>
          <tbody>${result.sources.map((source) => `
            <tr>
              <td title="${escapeAttribute(source.entity_id)}">${escapeHtml(source.entity_name)}</td>
              <td>${escapeHtml(source.device_name || t("fields.no_device"))}</td>
            </tr>
          `).join("")}</tbody>
        </table>`;
  } catch (error) {
    console.error("Virtual Device Manager: failed to load source entities", error);
    showDialogError(dialog, t("messages.load_sources_failed"));
    dialog.querySelector(".source-loading")?.remove();
  }
}


export async function openHistorySyncDialog(
  component,
  device,
  onCompleted,
) {
  const t = component._t;
  const dialog = document.createElement("div");
  dialog.className = "dialog-backdrop";
  dialog.innerHTML = `
    <div class="dialog">
      <div class="dialog-title">${t("dialogs.sync_title")}</div>
      <div class="dialog-content">
        <p>
          ${t("dialogs.sync_description")}
        </p>
        <p>
          ${t("dialogs.sync_limitations")}
        </p>
      </div>
      <div class="dialog-actions">
        <button class="cancel-button">${t("actions.cancel")}</button>
        <button class="sync-confirm-button">${t("actions.sync")}</button>
      </div>
    </div>
  `;
  component.appendChild(dialog);
  const cancelButton = dialog.querySelector(".cancel-button");
  const syncButton = dialog.querySelector(".sync-confirm-button");
  return await new Promise((resolve, reject) => {
    cancelButton.addEventListener("click", () => {
      dialog.remove();
      resolve(null);
    });
    syncButton.addEventListener("click", async () => {
      cancelButton.disabled = true;
      syncButton.disabled = true;
      syncButton.textContent = t("actions.syncing");
      try {
        const result = await synchronizeHistory(component._hass, device.id);
        dialog.remove();
        await onCompleted(result);
        resolve(result);
      } catch (error) {
        cancelButton.disabled = false;
        syncButton.disabled = false;
        syncButton.textContent = t("actions.sync");
        showDialogError(
          dialog,
          t(error?.code === "busy" ? "reasons.busy" : "messages.sync_failed"),
        );
        reject(error);
      }
    });
  });
}


export async function openCreateVirtualDeviceDialog(
  component,
  labels,
  onCreated,
) {
  const t = component._t;
  const dialog = document.createElement("div");

  dialog.className = "dialog-backdrop";

  dialog.innerHTML = `
    <div class="dialog">
      <div class="dialog-title">
        ${t("dialogs.create_device")}
      </div>

      <div class="dialog-content">
        <label>${t("fields.name")}</label>

        <input
          class="name-input"
          type="text"
          placeholder="${escapeAttribute(t("fields.optional"))}"
        />

        <label>${t("fields.label")}</label>

        <select class="label-select">
          ${labels
            .map(
              (label) => `
                <option
                  value="${escapeAttribute(label.label_id)}"
                >
                  ${escapeHtml(label.name)}
                </option>
              `,
            )
            .join("")}
        </select>
      </div>

      <div class="dialog-actions">
        <button class="cancel-button">
          ${t("actions.cancel")}
        </button>

        <button class="create-button">
          ${t("actions.create")}
        </button>
      </div>
    </div>
  `;

  component.appendChild(dialog);

  const cancelButton =
    dialog.querySelector(".cancel-button");

  const createButton =
    dialog.querySelector(".create-button");

  const nameInput =
    dialog.querySelector(".name-input");

  const labelSelect =
    dialog.querySelector(".label-select");

  let nameTouched = false;

  const updateSuggestedName = () => {
    if (nameTouched) {
      return;
    }

    const selectedLabel = labels.find(
      (label) => label.label_id === labelSelect.value,
    );

    nameInput.value = selectedLabel?.name || "";
  };

  nameInput.addEventListener("input", () => {
    nameTouched = true;
  });

  labelSelect.addEventListener("change", updateSuggestedName);
  updateSuggestedName();

  cancelButton.addEventListener(
    "click",
    () => dialog.remove(),
  );

  dialog.addEventListener(
    "click",
    (event) => {
      if (event.target === dialog) {
        dialog.remove();
      }
    },
  );

  createButton.addEventListener(
    "click",
    async () => {
      const name = nameInput.value.trim();
      const labelRef = labelSelect.value;

      if (!labelRef) {
        return;
      }

      createButton.disabled = true;
      createButton.textContent = t("actions.creating");

      try {
        const data = {
          label_ref: labelRef,
        };

        if (name) {
          data.name = name;
        }

        await createVirtualDevice(
          component._hass,
          data,
        );

        dialog.remove();

        await onCreated();
      } catch (error) {
        console.error(
          "Virtual Device Manager: failed to create virtual device",
          error,
        );

        createButton.disabled = false;
        createButton.textContent = t("actions.create");

        showDialogError(
          dialog,
          t("messages.create_device_failed"),
        );
      }
    },
  );

  nameInput.focus();
}


export async function openEditVirtualDeviceDialog(
  component,
  device,
  labels,
  onUpdated,
) {
  const t = component._t;
  const dialog = document.createElement("div");

  dialog.className = "dialog-backdrop";

  dialog.innerHTML = `
    <div class="dialog">
      <div class="dialog-title">
        ${t("dialogs.edit_device")}
      </div>

      <div class="dialog-content">
        <label>${t("fields.name")}</label>

        <input
          class="name-input"
          type="text"
          value="${escapeAttribute(device.name || "")}"
        />

        <label>${t("fields.label")}</label>

        <input
          class="label-input"
          type="text"
          value="${escapeAttribute(
            labels.find(
              (label) => label.label_id === device.label_ref,
            )?.name || device.label_ref || "",
          )}"
          disabled
        />

        <div class="physical-name-warning hidden">
          ${t("dialogs.physical_name_warning")}

          <label class="confirm-row">
            <input
              class="confirm-conflict"
              type="checkbox"
            />

            ${t("dialogs.confirm_name_conflict")}
          </label>
        </div>
      </div>

      <div class="dialog-actions">
        <button class="cancel-button">
          ${t("actions.cancel")}
        </button>

        <button class="save-button">
          ${t("actions.save")}
        </button>
      </div>
    </div>
  `;

  component.appendChild(dialog);

  const cancelButton =
    dialog.querySelector(".cancel-button");

  const saveButton =
    dialog.querySelector(".save-button");

  const nameInput =
    dialog.querySelector(".name-input");

  const warning =
    dialog.querySelector(
      ".physical-name-warning",
    );

  const confirmConflict =
    dialog.querySelector(
      ".confirm-conflict",
    );

  cancelButton.addEventListener(
    "click",
    () => dialog.remove(),
  );

  dialog.addEventListener(
    "click",
    (event) => {
      if (event.target === dialog) {
        dialog.remove();
      }
    },
  );

  saveButton.addEventListener(
    "click",
    async () => {
      const name = nameInput.value.trim();

      saveButton.disabled = true;
      saveButton.textContent = t("actions.saving");

      try {
        const result =
          await updateVirtualDevice(
            component._hass,
            {
              device_id: device.id,
              name,
              confirm_physical_name_conflict:
                confirmConflict.checked,
            },
          );

        dialog.remove();

        await onUpdated(result.device);
      } catch (error) {
        console.error(
          "Virtual Device Manager: failed to update virtual device",
          error,
        );

        saveButton.disabled = false;
        saveButton.textContent = t("actions.save");

        /* WebSocket conflict details can be surfaced in a later refinement. */
        showDialogError(
          dialog,
          t("messages.update_device_failed"),
        );
      }
    },
  );

  /* The authoritative name conflict check remains server-side. */
  warning.classList.add("hidden");

  nameInput.focus();
}


export async function openCreateVirtualEntityDialog(
  component,
  device,
  entityConfig,
  onCreated,
) {
  const t = component._t;
  const dialog = document.createElement("div");

  dialog.className = "dialog-backdrop";

  dialog.innerHTML = `
    <div class="dialog">
      <div class="dialog-title">
        ${t("dialogs.create_entity")}
      </div>

      <div class="dialog-content">

        <label>${t("fields.name")}</label>

        <input
          class="entity-name-input"
          type="text"
          placeholder="${escapeAttribute(
            t(`device_classes.${entityConfig.device_classes[0]}`),
          )}"
        />

        <label>${t("fields.device_class")}</label>

        <select class="entity-device-class-select">
          ${entityConfig.device_classes
            .map(
              (deviceClass) => `
                <option value="${escapeAttribute(deviceClass)}">
                  ${escapeHtml(t(`device_classes.${deviceClass}`))}
                </option>
              `,
            )
            .join("")}
        </select>

        <label>${t("fields.aggregation")}</label>

        <select class="entity-aggregation-select">
          ${entityConfig.aggregations
            .map(
              (aggregation) => `
                <option value="${escapeAttribute(aggregation)}">
                  ${escapeHtml(t(`aggregations.${aggregation}`))}
                </option>
              `,
            )
            .join("")}
        </select>

        ${filterEditorHtml("include", null, null, t)}
        ${filterEditorHtml("exclude", null, null, t)}

      </div>

      <div class="dialog-actions">

        <button class="cancel-button">
          ${t("actions.cancel")}
        </button>

        <button class="create-button">
          ${t("actions.create")}
        </button>

      </div>
    </div>
  `;

  component.appendChild(dialog);

  const cancelButton =
    dialog.querySelector(".cancel-button");

  const createButton =
    dialog.querySelector(".create-button");

  const nameInput =
    dialog.querySelector(
      ".entity-name-input",
    );

  const deviceClassSelect =
    dialog.querySelector(
      ".entity-device-class-select",
    );

  const aggregationSelect =
    dialog.querySelector(
      ".entity-aggregation-select",
    );
  setupFilterEditors(dialog, t);

  const updateNamePlaceholder = () => {
    nameInput.placeholder = t(`device_classes.${deviceClassSelect.value}`);
  };

  deviceClassSelect.addEventListener("change", updateNamePlaceholder);
  updateNamePlaceholder();

  cancelButton.addEventListener(
    "click",
    () => dialog.remove(),
  );

  dialog.addEventListener(
    "click",
    (event) => {
      if (event.target === dialog) {
        dialog.remove();
      }
    },
  );

  createButton.addEventListener(
    "click",
    async () => {
      const name =
        nameInput.value.trim();

      const deviceClass =
        deviceClassSelect.value;

      const aggregation =
        aggregationSelect.value;

      if (!deviceClass) {
        showDialogError(
          dialog,
          t("messages.device_class_required"),
        );

        return;
      }

      createButton.disabled = true;
      createButton.textContent =
        t("actions.creating");

      try {
        const updatedDevice =
          await addVirtualEntity(
            component._hass,
            {
              device_id: device.id,
              device_class: deviceClass,
              aggregation,
              name: resolveEntityName(name, deviceClass, t),
              include_filter: collectFilter(dialog, "include"),
              exclude_filter: collectFilter(dialog, "exclude"),
            },
          );

        dialog.remove();

        await onCreated(
          updatedDevice,
        );
      } catch (error) {
        console.error(
          "Virtual Device Manager: failed to create virtual entity",
          error,
        );

        createButton.disabled = false;
        createButton.textContent =
          t("actions.create");

        showDialogError(
          dialog,
          t("messages.create_entity_failed"),
        );
      }
    },
  );

  nameInput.focus();
}


export async function openEditVirtualEntityDialog(
  component,
  device,
  entity,
  entityConfig,
  onUpdated,
) {
  const t = component._t;
  const dialog = document.createElement("div");

  dialog.className = "dialog-backdrop";

  dialog.innerHTML = `
    <div class="dialog">

      <div class="dialog-title">
        ${t("dialogs.edit_entity")}
      </div>

      <div class="dialog-content">

        <label>${t("fields.name")}</label>

        <input
          class="entity-name-input"
          type="text"
          value="${escapeAttribute(
            entity.name || "",
          )}"
          placeholder="${escapeAttribute(
            t(`device_classes.${entity.device_class}`),
          )}"
        />

        <label>${t("fields.entity_id")}</label>

        <input
          class="entity-id-input"
          type="text"
          value="${escapeAttribute(
            entity.id,
          )}"
          disabled
        />

        <label>${t("fields.device_class")}</label>

        <select class="entity-device-class-select">
          ${entityConfig.device_classes
            .map(
              (deviceClass) => `
                <option
                  value="${escapeAttribute(deviceClass)}"
                  ${deviceClass === entity.device_class ? "selected" : ""}
                >
                  ${escapeHtml(t(`device_classes.${deviceClass}`))}
                </option>
              `,
            )
            .join("")}
        </select>

        <label>${t("fields.aggregation")}</label>

        <select class="entity-aggregation-select">
          ${entityConfig.aggregations
            .map(
              (aggregation) => `
                <option
                  value="${escapeAttribute(aggregation)}"
                  ${aggregation === entity.aggregation ? "selected" : ""}
                >
                  ${escapeHtml(t(`aggregations.${aggregation}`))}
                </option>
              `,
            )
            .join("")}
        </select>

        ${filterEditorHtml("include", entity.include_filter, entity.filter_diagnostics, t)}
        ${filterEditorHtml("exclude", entity.exclude_filter, entity.filter_diagnostics, t)}

      </div>

      <div class="dialog-actions">

        <button class="cancel-button">
          ${t("actions.cancel")}
        </button>

        <button class="save-button">
          ${t("actions.save")}
        </button>

      </div>

    </div>
  `;

  component.appendChild(dialog);

  const cancelButton =
    dialog.querySelector(
      ".cancel-button",
    );

  const saveButton =
    dialog.querySelector(
      ".save-button",
    );

  const nameInput =
    dialog.querySelector(
      ".entity-name-input",
    );

  const aggregationSelect =
    dialog.querySelector(
      ".entity-aggregation-select",
    );

  const deviceClassSelect =
    dialog.querySelector(
      ".entity-device-class-select",
    );
  setupFilterEditors(dialog, t);

  const updateNamePlaceholder = () => {
    nameInput.placeholder = t(`device_classes.${deviceClassSelect.value}`);
  };

  deviceClassSelect.addEventListener("change", updateNamePlaceholder);
  updateNamePlaceholder();

  cancelButton.addEventListener(
    "click",
    () => dialog.remove(),
  );

  dialog.addEventListener(
    "click",
    (event) => {
      if (event.target === dialog) {
        dialog.remove();
      }
    },
  );

  saveButton.addEventListener(
    "click",
    async () => {
      const name =
        nameInput.value.trim();

      const aggregation =
        aggregationSelect.value;

      const deviceClass =
        deviceClassSelect.value;

      saveButton.disabled = true;
      saveButton.textContent =
        t("actions.saving");

      try {
        const updatedDevice =
          await updateVirtualEntity(
            component._hass,
            {
              device_id: device.id,
              entity_id: entity.id,
              device_class: deviceClass,
              aggregation,
              name: resolveEntityName(name, deviceClass, t),
              include_filter: collectFilter(dialog, "include"),
              exclude_filter: collectFilter(dialog, "exclude"),
            },
          );

        dialog.remove();

        await onUpdated(
          updatedDevice,
        );
      } catch (error) {
        console.error(
          "Virtual Device Manager: failed to update virtual entity",
          error,
        );

        saveButton.disabled = false;
        saveButton.textContent =
          t("actions.save");

        showDialogError(
          dialog,
          t("messages.update_entity_failed"),
        );
      }
    },
  );

  nameInput.focus();
}


export async function confirmDeleteVirtualEntity(
  component,
  device,
  entity,
  onDeleted,
) {
  const name =
    entity.name || entity.id;

  if (
    !window.confirm(
      component._t("dialogs.delete_entity", {name}),
    )
  ) {
    return;
  }

  try {
    const updatedDevice =
      await deleteVirtualEntity(
        component._hass,
        {
          device_id: device.id,
          entity_id: entity.id,
        },
      );

    await onDeleted(
      updatedDevice,
    );
  } catch (error) {
    console.error(
      "Virtual Device Manager: failed to delete virtual entity",
      error,
    );

    component._showMessage(
      component._t("messages.delete_entity_failed"),
    );
  }
}


function showDialogError(
  dialog,
  message,
) {
  let errorElement =
    dialog.querySelector(
      ".dialog-error",
    );

  if (!errorElement) {
    errorElement =
      document.createElement("div");

    errorElement.className =
      "dialog-error";

    dialog
      .querySelector(".dialog-content")
      .prepend(errorElement);
  }

  errorElement.textContent = message;
}


function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


function escapeAttribute(value) {
  return escapeHtml(value);
}

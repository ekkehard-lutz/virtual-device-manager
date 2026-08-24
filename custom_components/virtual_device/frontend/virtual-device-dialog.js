import {
  createVirtualDevice,
  updateVirtualDevice,
  addVirtualEntity,
  updateVirtualEntity,
  deleteVirtualEntity,
  synchronizeHistory,
} from "./virtual-device-api.js";
import {resolveEntityName} from "./virtual-device-translations.js";


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

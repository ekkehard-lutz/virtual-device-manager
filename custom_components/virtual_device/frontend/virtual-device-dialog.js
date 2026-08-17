import {
  createVirtualDevice,
  updateVirtualDevice,
  addVirtualEntity,
  updateVirtualEntity,
  deleteVirtualEntity,
} from "./virtual-device-api.js";


export async function openCreateVirtualDeviceDialog(
  component,
  labels,
  onCreated,
) {
  const dialog = document.createElement("div");

  dialog.className = "dialog-backdrop";

  dialog.innerHTML = `
    <div class="dialog">
      <div class="dialog-title">
        Neues virtuelles Gerät
      </div>

      <div class="dialog-content">
        <label>Name</label>

        <input
          class="name-input"
          type="text"
          placeholder="Optional"
        />

        <label>Label</label>

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
          Abbrechen
        </button>

        <button class="create-button">
          Erstellen
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
      createButton.textContent = "Erstellen …";

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
          "Virtual Device Manager: Fehler beim Erstellen des Virtual Device",
          error,
        );

        createButton.disabled = false;
        createButton.textContent = "Erstellen";

        showDialogError(
          dialog,
          "Das virtuelle Gerät konnte nicht erstellt werden.",
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
  const dialog = document.createElement("div");

  dialog.className = "dialog-backdrop";

  dialog.innerHTML = `
    <div class="dialog">
      <div class="dialog-title">
        Virtuelles Gerät bearbeiten
      </div>

      <div class="dialog-content">
        <label>Name</label>

        <input
          class="name-input"
          type="text"
          value="${escapeAttribute(device.name || "")}"
        />

        <label>Label</label>

        <select class="label-select">
          ${labels
            .map(
              (label) => `
                <option
                  value="${escapeAttribute(label.label_id)}"
                  ${
                    label.label_id === device.label_ref
                      ? "selected"
                      : ""
                  }
                >
                  ${escapeHtml(label.name)}
                </option>
              `,
            )
            .join("")}
        </select>

        <div class="physical-name-warning hidden">
          Der Name entspricht dem Namen eines physischen
          Home-Assistant-Gerätes.

          <label class="confirm-row">
            <input
              class="confirm-conflict"
              type="checkbox"
            />

            Diesen Namen trotzdem verwenden.
          </label>
        </div>
      </div>

      <div class="dialog-actions">
        <button class="cancel-button">
          Abbrechen
        </button>

        <button class="save-button">
          Speichern
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

  const labelSelect =
    dialog.querySelector(".label-select");

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
      const labelRef = labelSelect.value;

      saveButton.disabled = true;
      saveButton.textContent = "Speichern …";

      try {
        const result =
          await updateVirtualDevice(
            component._hass,
            {
              device_id: device.id,
              name,
              label_ref: labelRef,
              confirm_physical_name_conflict:
                confirmConflict.checked,
            },
          );

        dialog.remove();

        await onUpdated(result.device);
      } catch (error) {
        console.error(
          "Virtual Device Manager: Fehler beim Aktualisieren des Virtual Device",
          error,
        );

        saveButton.disabled = false;
        saveButton.textContent = "Speichern";

        /*
         * Der Backend-Konflikt wird später noch
         * genauer über die HA-WebSocket-Fehlerdaten
         * behandelt.
         *
         * Für den ersten Refactoring-Schritt zeigen
         * wir zunächst eine allgemeine Meldung.
         */
        showDialogError(
          dialog,
          "Das virtuelle Gerät konnte nicht aktualisiert werden.",
        );
      }
    },
  );

  /*
   * Die Konfliktabfrage bleibt zunächst bewusst
   * einfach. Die eigentliche Prüfung erfolgt
   * serverseitig.
   */
  warning.classList.add("hidden");

  nameInput.focus();
}


export async function openCreateVirtualEntityDialog(
  component,
  device,
  onCreated,
) {
  const dialog = document.createElement("div");

  dialog.className = "dialog-backdrop";

  dialog.innerHTML = `
    <div class="dialog">
      <div class="dialog-title">
        Neue Virtual Entity
      </div>

      <div class="dialog-content">

        <label>Name</label>

        <input
          class="entity-name-input"
          type="text"
          placeholder="z. B. Gesamtleistung"
        />

        <label>Device Class</label>

        <input
          class="entity-device-class-input"
          type="text"
          placeholder="z. B. power"
        />

        <label>Aggregation</label>

        <select class="entity-aggregation-select">
          <option value="sum">Summe</option>
          <option value="avg">Durchschnitt</option>
          <option value="min">Minimum</option>
          <option value="max">Maximum</option>
        </select>

        <label>Einheit</label>

        <input
          class="entity-unit-input"
          type="text"
          placeholder="z. B. W"
        />

      </div>

      <div class="dialog-actions">

        <button class="cancel-button">
          Abbrechen
        </button>

        <button class="create-button">
          Erstellen
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

  const deviceClassInput =
    dialog.querySelector(
      ".entity-device-class-input",
    );

  const aggregationSelect =
    dialog.querySelector(
      ".entity-aggregation-select",
    );

  const unitInput =
    dialog.querySelector(
      ".entity-unit-input",
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

  createButton.addEventListener(
    "click",
    async () => {
      const name =
        nameInput.value.trim();

      const deviceClass =
        deviceClassInput.value.trim();

      const aggregation =
        aggregationSelect.value;

      const unit =
        unitInput.value.trim();

      if (!deviceClass || !unit) {
        showDialogError(
          dialog,
          "Device Class und Einheit müssen angegeben werden.",
        );

        return;
      }

      createButton.disabled = true;
      createButton.textContent =
        "Erstellen …";

      try {
        const updatedDevice =
          await addVirtualEntity(
            component._hass,
            {
              device_id: device.id,
              device_class: deviceClass,
              aggregation,
              unit,
              name: name || undefined,
            },
          );

        dialog.remove();

        await onCreated(
          updatedDevice,
        );
      } catch (error) {
        console.error(
          "Virtual Device Manager: Fehler beim Erstellen der Virtual Entity",
          error,
        );

        createButton.disabled = false;
        createButton.textContent =
          "Erstellen";

        showDialogError(
          dialog,
          "Die Virtual Entity konnte nicht erstellt werden.",
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
  onUpdated,
) {
  const dialog = document.createElement("div");

  dialog.className = "dialog-backdrop";

  dialog.innerHTML = `
    <div class="dialog">

      <div class="dialog-title">
        Virtual Entity bearbeiten
      </div>

      <div class="dialog-content">

        <label>Name</label>

        <input
          class="entity-name-input"
          type="text"
          value="${escapeAttribute(
            entity.name || "",
          )}"
        />

        <label>Entity-ID</label>

        <input
          class="entity-id-input"
          type="text"
          value="${escapeAttribute(
            entity.id,
          )}"
          disabled
        />

        <label>Device Class</label>

        <input
          class="entity-device-class-input"
          type="text"
          value="${escapeAttribute(
            entity.device_class || "",
          )}"
        />

        <label>Aggregation</label>

        <select class="entity-aggregation-select">

          <option
            value="sum"
            ${
              entity.aggregation === "sum"
                ? "selected"
                : ""
            }
          >
            Summe
          </option>

          <option
            value="avg"
            ${
              entity.aggregation === "avg"
                ? "selected"
                : ""
            }
          >
            Durchschnitt
          </option>

          <option
            value="min"
            ${
              entity.aggregation === "min"
                ? "selected"
                : ""
            }
          >
            Minimum
          </option>

          <option
            value="max"
            ${
              entity.aggregation === "max"
                ? "selected"
                : ""
            }
          >
            Maximum
          </option>

        </select>

        <label>Einheit</label>

        <input
          class="entity-unit-input"
          type="text"
          value="${escapeAttribute(
            entity.unit || "",
          )}"
        />

      </div>

      <div class="dialog-actions">

        <button class="cancel-button">
          Abbrechen
        </button>

        <button class="save-button">
          Speichern
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

  const deviceClassInput =
    dialog.querySelector(
      ".entity-device-class-input",
    );

  const aggregationSelect =
    dialog.querySelector(
      ".entity-aggregation-select",
    );

  const unitInput =
    dialog.querySelector(
      ".entity-unit-input",
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
      const name =
        nameInput.value.trim();

      const deviceClass =
        deviceClassInput.value.trim();

      const aggregation =
        aggregationSelect.value;

      const unit =
        unitInput.value.trim();

      if (!deviceClass || !unit) {
        showDialogError(
          dialog,
          "Device Class und Einheit müssen angegeben werden.",
        );

        return;
      }

      saveButton.disabled = true;
      saveButton.textContent =
        "Speichern …";

      try {
        const updatedDevice =
          await updateVirtualEntity(
            component._hass,
            {
              device_id: device.id,
              entity_id: entity.id,
              device_class: deviceClass,
              aggregation,
              unit,
              name: name || undefined,
            },
          );

        dialog.remove();

        await onUpdated(
          updatedDevice,
        );
      } catch (error) {
        console.error(
          "Virtual Device Manager: Fehler beim Aktualisieren der Virtual Entity",
          error,
        );

        saveButton.disabled = false;
        saveButton.textContent =
          "Speichern";

        showDialogError(
          dialog,
          "Die Virtual Entity konnte nicht aktualisiert werden.",
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
      `Virtual Entity „${name}“ wirklich löschen?`,
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
      "Virtual Device Manager: Fehler beim Löschen der Virtual Entity",
      error,
    );

    component._showMessage(
      "Die Virtual Entity konnte nicht gelöscht werden.",
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

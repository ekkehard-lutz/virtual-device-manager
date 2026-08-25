import {
  loadVirtualDevices,
  loadLabels,
  loadEntityConfig,
  deleteVirtualDevice,
  addVirtualEntity,
  updateVirtualEntity,
  deleteVirtualEntity,
} from "./virtual-device-api.js";

import {
  openCreateVirtualDeviceDialog,
  openEditVirtualDeviceDialog,
  openCreateVirtualEntityDialog,
  openEditVirtualEntityDialog,
  confirmDeleteVirtualEntity,
  openHistorySyncDialog,
  openSourceEntitiesDialog,
} from "./virtual-device-dialog.js";

import {
  addStyles,
} from "./virtual-device-styles.js";
import {
  createTranslator,
  loadTranslations,
} from "./virtual-device-translations.js";


class VirtualDeviceManager
  extends HTMLElement {

  set hass(hass) {
    this._hass = hass;
    const language = hass.language || "en";
    if (!this._initialized || language !== this._language) {
      this._initialized = true;
      this._language = language;
      this._loadTranslationsAndDevices();
    }
  }

  async _loadTranslationsAndDevices() {
    try {
      const translations = await loadTranslations(this._hass);
      this._t = createTranslator(translations.messages);
      await this._loadDevices();
    } catch (error) {
      console.error("Virtual Device Manager: failed to load translations", error);
      this._t = createTranslator();
      this._renderError(error);
    }
  }


  async _loadDevices() {
    this._setLoading();

    try {
      this._devices =
        await loadVirtualDevices(
          this._hass,
        );

      this._render();
    } catch (error) {
      this._renderError(error);
    }
  }


  _render() {
    const devices = [
      ...(this._devices || []),
    ].sort((a, b) =>
      String(a.name || a.id).localeCompare(
        String(b.name || b.id),
      ),
    );

    const content =
      devices.length === 0
        ? `
          <div class="empty">
            ${this._t("empty.devices")}
          </div>
        `
        : `
          <div class="device-list">
            ${devices
              .map(
                (device) =>
                  this._renderDevice(device),
              )
              .join("")}
          </div>
        `;

    this.innerHTML = `
      <ha-card>
        <div class="header">
          <div class="title">
            ${this._t("title")}
          </div>

          <ha-button class="add-button">
            <ha-icon icon="mdi:plus"></ha-icon>
            ${this._t("actions.add")}
          </ha-button>
        </div>

        <div class="content">
          ${content}
        </div>
      </ha-card>
    `;

    addStyles(this);

    this
      .querySelector(".add-button")
      ?.addEventListener(
        "click",
        () => this._openCreateDialog(),
      );

    this
      .querySelectorAll(".device-header")
      .forEach((header) => {
        const toggle = () => {
          const body = header.closest(".device-main")?.querySelector(".device-body");
          const control = header.querySelector(".collapse-button");
          const expanded = control?.getAttribute("aria-expanded") === "true";
          control?.setAttribute("aria-expanded", String(!expanded));
          control?.setAttribute("aria-label", this._t(expanded ? "actions.expand" : "actions.collapse"));
          header.querySelector(".device-chevron")?.setAttribute(
            "icon", expanded ? "mdi:chevron-right" : "mdi:chevron-down",
          );
          body?.classList.toggle("hidden", expanded);
        };
        header.addEventListener("click", toggle);
      });

    this.querySelectorAll(".device-actions button").forEach((button) => {
      button.addEventListener("click", (event) => event.stopPropagation());
    });

    this.querySelectorAll(".source-count-button").forEach((button) => {
      button.addEventListener("click", () => {
        const device = this._devices.find((item) => item.id === button.dataset.deviceId);
        const entity = device?.entities?.find((item) => item.id === button.dataset.entityId);
        if (device && entity) openSourceEntitiesDialog(this, device, entity);
      });
    });

    this
      .querySelectorAll(".history-sync-button")
      .forEach((button) => {
        button.addEventListener("click", () => {
          const device = this._devices.find(
            (item) => item.id === button.dataset.deviceId,
          );
          if (device) {
            this._openHistorySyncDialog(device);
          }
        });
      });

    this
      .querySelectorAll(".edit-button")
      .forEach((button) => {
        button.addEventListener(
          "click",
          () => {
            const device =
              this._devices.find(
                (item) =>
                  item.id ===
                  button.dataset.deviceId,
              );

            if (device) {
              this._openEditDialog(
                device,
              );
            }
          },
        );
      });

    this
      .querySelectorAll(".delete-button")
      .forEach((button) => {
        button.addEventListener(
          "click",
          () => {
            this._deleteDevice(
              button.dataset.deviceId,
              button.dataset.deviceName,
            );
          },
        );
      });

    this
      .querySelectorAll(".add-entity-button")
      .forEach((button) => {
        button.addEventListener(
          "click",
          () => {
            const device =
              this._devices.find(
                (item) =>
                  item.id ===
                  button.dataset.deviceId,
              );

            if (device) {
              this._openAddEntityDialog(
                device,
              );
            }
          },
        );
      });


    this
      .querySelectorAll(".edit-entity-button")
      .forEach((button) => {
        button.addEventListener(
          "click",
          () => {
            const device =
              this._devices.find(
                (item) =>
                  item.id ===
                  button.dataset.deviceId,
              );

            if (!device) {
              return;
            }

            const entity =
              device.entities?.find(
                (item) =>
                  item.id ===
                  button.dataset.entityId,
              );

            if (entity) {
              this._openEditEntityDialog(
                device,
                entity,
              );
            }
          },
        );
      });


    this
      .querySelectorAll(".delete-entity-button")
      .forEach((button) => {
        button.addEventListener(
          "click",
          () => {
            this._deleteEntity(
              button.dataset.deviceId,
              button.dataset.entityId,
              button.dataset.entityName,
            );
          },
        );
      });
  }


  _renderDevice(device) {
    const name =
      device.name || device.id;

    const entities = (
      Array.isArray(device.entities)
        ? device.entities
        : []
    ).slice().sort((a, b) =>
      String(a.name || a.id).localeCompare(
        String(b.name || b.id),
      ),
    );

    return `
      <div class="device">

        <div class="device-main">

          <div class="device-header">

            <button class="collapse-button" aria-expanded="false"
              aria-label="${this._escapeAttribute(this._t("actions.expand"))}">
              <ha-icon class="device-chevron" icon="mdi:chevron-right"></ha-icon>
            </button>

            <div class="device-heading">
              <div class="device-name">
                <span>${this._escape(name)}</span>
                ${device.label_missing ? `
                  <ha-icon class="label-missing-warning" icon="mdi:alert"
                    title="${this._escapeAttribute(this._t("messages.label_deleted"))}"
                    aria-label="${this._escapeAttribute(this._t("messages.label_deleted"))}"></ha-icon>
                ` : ""}
              </div>
              <div class="device-entity-count">${this._entityCount(entities.length, "virtual_entity")}</div>
            </div>

            <div class="device-actions">

              <button
                class="history-sync-button"
                data-device-id="${this._escapeAttribute(device.id)}"
                title="${this._escapeAttribute(this._t("actions.sync"))}"
                aria-label="${this._escapeAttribute(this._t("actions.sync"))}"
                ${this._historySyncRunning ? "disabled" : ""}
              >
                <ha-icon icon="mdi:history"></ha-icon>
              </button>

              <button
                class="edit-button"
                data-device-id="${this._escapeAttribute(
                  device.id,
                )}"
                title="${this._escapeAttribute(this._t("actions.edit_device"))}"
                aria-label="${this._escapeAttribute(this._t("actions.edit_device"))}"
              >
                <ha-icon
                  icon="mdi:pencil-outline"
                ></ha-icon>
              </button>

              <button
                class="delete-button"
                data-device-id="${this._escapeAttribute(
                  device.id,
                )}"
                data-device-name="${this._escapeAttribute(
                  name,
                )}"
                title="${this._escapeAttribute(this._t("actions.delete_device"))}"
                aria-label="${this._escapeAttribute(this._t("actions.delete_device"))}"
              >
                <ha-icon
                  icon="mdi:delete-outline"
                ></ha-icon>
              </button>

            </div>

          </div>

          <div class="device-body hidden">

          <div class="device-details">

            <span>
              ${this._t("fields.label")}:
              <strong>
                ${this._escape(
                  device.label_ref,
                )}
              </strong>
            </span>

          </div>

          <div class="entities-header">

            <span class="entities-title">
              ${this._t("entities_title")}
            </span>

            <button
              class="add-entity-button"
              data-device-id="${this._escapeAttribute(
                device.id,
              )}"
              title="${this._escapeAttribute(this._t("actions.add_entity"))}"
              aria-label="${this._escapeAttribute(this._t("actions.add_entity"))}"
            >
              <ha-icon
                icon="mdi:plus"
              ></ha-icon>
            </button>

          </div>

          <div class="entity-list">

            ${
              entities.length === 0
                ? `
                  <div class="entities-empty">
                    ${this._t("empty.entities")}
                  </div>
                `
                : entities
                    .map(
                      (entity) =>
                        this._renderEntity(
                          device,
                          entity,
                        ),
                    )
                    .join("")
            }

          </div>

          </div>

        </div>

      </div>
    `;
  }


  async _openHistorySyncDialog(device) {
    if (this._historySyncRunning) {
      return;
    }
    this._historySyncRunning = true;
    this._render();
    let summary = null;
    try {
      await openHistorySyncDialog(this, device, async (result) => {
        const lines = [
          this._t("messages.sync_result", {status: this._t(`status.${result.status}`)}),
          ...result.entities.map((entity) => {
            const range = entity.range_start && entity.range_end
              ? ` (${entity.range_start} – ${entity.range_end})`
              : "";
            const reason = entity.reason_code
              ? this._t(`reasons.${entity.reason_code}`)
              : entity.reason;
            const detail = reason
              ? `: ${reason}`
              : `: ${this._t("messages.hours_updated", {count: entity.hourly_slots_upserted})}`;
            return `${entity.entity_id}: ${this._t(`status.${entity.status}`)}${detail}${range}`;
          }),
          this._t("messages.sync_limitations"),
        ];
        summary = lines.join("\n");
      });
    } catch (error) {
      console.error("Virtual Device Manager: history synchronization failed", error);
      this._showMessage(
        this._t(error?.code === "busy" ? "reasons.busy" : "messages.sync_failed"),
      );
    } finally {
      this._historySyncRunning = false;
      this._render();
      if (summary) {
        this._showMessage(summary);
      }
    }
  }



  _renderEntity(device, entity) {
    const name =
      entity.name || entity.id;

    return `
      <div class="entity">

        <div class="entity-main">

          <div class="entity-name">
            ${this._escape(entity.name || this._t(`device_classes.${entity.device_class}`))}
          </div>

          <div class="entity-details">

            <button class="source-count-button"
              data-device-id="${this._escapeAttribute(device.id)}"
              data-entity-id="${this._escapeAttribute(entity.id)}">
              ${this._entityCount(entity.source_count || 0, "physical_entity")}
            </button>

            <span>
              ${this._escape(
                this._t(`device_classes.${entity.device_class}`),
              )}
            </span>

            <span>
              ${this._escape(
                this._t(`aggregations.${entity.aggregation}`),
              )}
            </span>

          </div>

          <div class="entity-id">
            ${this._escape(entity.id)}
          </div>

        </div>

        <div class="entity-actions">

          <button
            class="edit-entity-button"
            data-device-id="${this._escapeAttribute(
              device.id,
            )}"
            data-entity-id="${this._escapeAttribute(
              entity.id,
            )}"
            title="${this._escapeAttribute(this._t("actions.edit_entity"))}"
            aria-label="${this._escapeAttribute(this._t("actions.edit_entity"))}"
          >
            <ha-icon
              icon="mdi:pencil-outline"
            ></ha-icon>
          </button>

          <button
            class="delete-entity-button"
            data-device-id="${this._escapeAttribute(
              device.id,
            )}"
            data-entity-id="${this._escapeAttribute(
              entity.id,
            )}"
            data-entity-name="${this._escapeAttribute(
              name,
            )}"
            title="${this._escapeAttribute(this._t("actions.delete_entity"))}"
            aria-label="${this._escapeAttribute(this._t("actions.delete_entity"))}"
          >
            <ha-icon
              icon="mdi:delete-outline"
            ></ha-icon>
          </button>

        </div>

      </div>
    `;
  }


  async _deleteDevice(
    deviceId,
    deviceName,
  ) {
    if (
      !window.confirm(
        this._t("dialogs.delete_device", {name: deviceName}),
      )
    ) {
      return;
    }

    try {
      await deleteVirtualDevice(
        this._hass,
        deviceId,
      );

      await this._loadDevices();
    } catch (error) {
      console.error(
        "Virtual Device Manager: failed to delete virtual device",
        error,
      );

      this._showMessage(
        this._t("messages.delete_device_failed"),
      );
    }
  }


  async _openCreateDialog() {
    try {
      const labels =
        await loadLabels(
          this._hass,
        );

      if (
        !labels ||
        labels.length === 0
      ) {
        this._showMessage(
          "Es sind keine Home-Assistant-Labels vorhanden.",
        );

        return;
      }

      const usedLabelRefs = new Set(
        (this._devices || []).map(
          (device) => device.label_ref,
        ),
      );

      const availableLabels = labels
        .filter(
          (label) =>
            !usedLabelRefs.has(label.label_id),
        )
        .sort((a, b) =>
          String(a.name).localeCompare(
            String(b.name),
          ),
        );

      if (availableLabels.length === 0) {
        this._showMessage(
          "Es sind keine freien Home-Assistant-Labels vorhanden.",
        );

        return;
      }

      await openCreateVirtualDeviceDialog(
        this,
        availableLabels,
        () => this._loadDevices(),
      );
    } catch (error) {
      this._renderError(error);
    }
  }


  async _openEditDialog(device) {
    try {
      const labels =
        await loadLabels(
          this._hass,
        );

      if (
        !labels ||
        labels.length === 0
      ) {
        this._showMessage(
          "Es sind keine Home-Assistant-Labels vorhanden.",
        );

        return;
      }

      await openEditVirtualDeviceDialog(
        this,
        device,
        labels,
        async () => {
          await this._loadDevices();
        },
      );
    } catch (error) {
      this._renderError(error);
    }
  }


  async _openAddEntityDialog(device) {
    try {
      const entityConfig = await loadEntityConfig(
        this._hass,
      );

      await openCreateVirtualEntityDialog(
        this,
        device,
        entityConfig,
        async () => {
          await this._loadDevices();
        },
      );
    } catch (error) {
      console.error(
        "Virtual Device Manager: failed to open virtual entity dialog",
        error,
      );

      this._renderError(error);
    }
  }


  async _openEditEntityDialog(
    device,
    entity,
  ) {
    try {
      const entityConfig = await loadEntityConfig(
        this._hass,
      );

      await openEditVirtualEntityDialog(
        this,
        device,
        entity,
        entityConfig,
        async () => {
          await this._loadDevices();
        },
      );
    } catch (error) {
      console.error(
        "Virtual Device Manager: failed to open virtual entity dialog",
        error,
      );

      this._renderError(error);
    }
  }


  async _deleteEntity(
    deviceId,
    entityId,
    entityName,
  ) {
    const device =
      this._devices.find(
        (item) =>
          item.id === deviceId,
      );

    if (!device) {
      return;
    }

    const entity =
      Array.isArray(device.entities)
        ? device.entities.find(
            (item) =>
              item.id === entityId,
          )
        : null;

    if (!entity) {
      return;
    }

    try {
      await confirmDeleteVirtualEntity(
        this,
        device,
        entity,
        async () => {
          await this._loadDevices();
        },
      );
    } catch (error) {
      console.error(
        "Virtual Device Manager: failed to delete virtual entity",
        error,
      );

      this._showMessage(
        this._t("messages.delete_named_entity_failed", {name: entityName}),
      );
    }
  }


  _showMessage(message) {
    const existing =
      this.querySelector(".message");

    if (existing) {
      existing.remove();
    }

    const messageElement =
      document.createElement("div");

    messageElement.className =
      "message";

    messageElement.textContent =
      message;

    this.appendChild(
      messageElement,
    );

    addStyles(this);
  }


  _setLoading() {
    this.innerHTML = `
      <ha-card>
        <div class="header">
          <div class="title">
            ${this._t?.("title") || "Virtual Device Manager"}
          </div>
        </div>

        <div class="content loading">
          ${this._t?.("loading") || "Loading…"}
        </div>
      </ha-card>
    `;

    addStyles(this);
  }


  _renderError(error) {
    console.error(
      "Virtual Device Manager WebSocket error:",
      error,
    );

    this.innerHTML = `
      <ha-card>
        <div class="header">
          <div class="title">
            ${this._t?.("title") || "Virtual Device Manager"}
          </div>
        </div>

        <div class="content error">
          ${this._t?.("messages.load_failed") || "Failed to load virtual devices."}
        </div>
      </ha-card>
    `;

    addStyles(this);
  }


  _escape(value) {
    return String(value)
      .replaceAll(
        "&",
        "&amp;",
      )
      .replaceAll(
        "<",
        "&lt;",
      )
      .replaceAll(
        ">",
        "&gt;",
      )
      .replaceAll(
        '"',
        "&quot;",
      )
      .replaceAll(
        "'",
        "&#039;",
      );
  }


  _entityCount(count, prefix) {
    const key = count === 1 ? `${prefix}_count_one` : `${prefix}_count_other`;
    return this._escape(this._t(`counts.${key}`, {count}));
  }


  _escapeAttribute(value) {
    return this._escape(value);
  }
}


export { VirtualDeviceManager };

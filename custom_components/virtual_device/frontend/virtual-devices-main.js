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
} from "./virtual-device-dialog.js";

import {
  addStyles,
} from "./virtual-device-styles.js";


class VirtualDeviceManager
  extends HTMLElement {

  set hass(hass) {
    this._hass = hass;

    if (!this._initialized) {
      this._initialized = true;
      this._loadDevices();
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
            Keine virtuellen Geräte vorhanden.
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
            Virtual Device Manager – Virtual Devices
          </div>

          <ha-button class="add-button">
            <ha-icon icon="mdi:plus"></ha-icon>
            Hinzufügen
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

            <div class="device-name">
              ${this._escape(name)}
            </div>

            <div class="device-actions">

              <button
                class="edit-button"
                data-device-id="${this._escapeAttribute(
                  device.id,
                )}"
                title="Virtuelles Gerät bearbeiten"
                aria-label="Virtuelles Gerät bearbeiten"
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
                title="Virtuelles Gerät löschen"
                aria-label="Virtuelles Gerät löschen"
              >
                <ha-icon
                  icon="mdi:delete-outline"
                ></ha-icon>
              </button>

            </div>

          </div>

          <div class="device-details">

            <span>
              Label:
              <strong>
                ${this._escape(
                  device.label_ref,
                )}
              </strong>
            </span>

          </div>

          <div class="entities-header">

            <span class="entities-title">
              Virtual Entities
            </span>

            <button
              class="add-entity-button"
              data-device-id="${this._escapeAttribute(
                device.id,
              )}"
              title="Virtual Entity hinzufügen"
              aria-label="Virtual Entity hinzufügen"
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
                    Keine Virtual Entities vorhanden.
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
    `;
  }



  _renderEntity(device, entity) {
    const name =
      entity.name || entity.id;

    return `
      <div class="entity">

        <div class="entity-main">

          <div class="entity-name">
            ${this._escape(name)}
          </div>

          <div class="entity-details">

            <span>
              ${this._escape(
                entity.device_class,
              )}
            </span>

            <span>
              ${this._escape(
                entity.aggregation,
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
            title="Virtual Entity bearbeiten"
            aria-label="Virtual Entity bearbeiten"
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
            title="Virtual Entity löschen"
            aria-label="Virtual Entity löschen"
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
        `Virtuelles Gerät „${deviceName}“ wirklich löschen?`,
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
        "Virtual Device Manager: Fehler beim Löschen des Virtual Device",
        error,
      );

      this._showMessage(
        "Das virtuelle Gerät konnte nicht gelöscht werden.",
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
        "Virtual Device Manager: Fehler beim Öffnen des Virtual Entity Dialogs",
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
        "Virtual Device Manager: Fehler beim Öffnen des Virtual Entity Dialogs",
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
        "Virtual Device Manager: Fehler beim Löschen der Virtual Entity",
        error,
      );

      this._showMessage(
        `Die Virtual Entity „${entityName}“ konnte nicht gelöscht werden.`,
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
            Virtual Device Manager – Virtual Devices
          </div>
        </div>

        <div class="content loading">
          Wird geladen …
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
            Virtual Device Manager – Virtual Devices
          </div>
        </div>

        <div class="content error">
          Fehler beim Laden der virtuellen Geräte.
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


  _escapeAttribute(value) {
    return this._escape(value);
  }
}


export { VirtualDeviceManager };

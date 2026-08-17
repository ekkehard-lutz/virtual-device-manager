class VirtualDeviceManagerBootstrap
  extends HTMLElement {

  constructor() {
    super();

    this._hass = undefined;
    this._implementationLoaded = false;
    this._loading = false;
  }

  set hass(hass) {
    this._hass = hass;

    if (!this._implementationLoaded) {
      this._loadImplementation();
      return;
    }

    this._applyHass(hass);
  }

  get hass() {
    return this._hass;
  }

  async _loadImplementation() {
    if (this._loading) {
      return;
    }

    this._loading = true;

    try {
      const module =
        await import("./virtual-devices-main.js");

      const Implementation =
        module.VirtualDeviceManager;

      if (!Implementation) {
        throw new Error(
          "Virtual Device Manager: VirtualDeviceManager wurde nicht exportiert",
        );
      }

      /*
       * Die Methoden der Implementierung auf
       * dieses bereits von Home Assistant
       * erzeugte Element übertragen.
       */
      const descriptors =
        Object.getOwnPropertyDescriptors(
          Implementation.prototype,
        );

      for (
        const [name, descriptor]
        of Object.entries(descriptors)
      ) {
        if (name === "constructor") {
          continue;
        }

        Object.defineProperty(
          this,
          name,
          descriptor,
        );
      }

      /*
       * Den hass-Setter der Implementierung
       * direkt übernehmen.
       */
      const hassDescriptor =
        Object.getOwnPropertyDescriptor(
          Implementation.prototype,
          "hass",
        );

      if (
        hassDescriptor &&
        hassDescriptor.set
      ) {
        Object.defineProperty(
          this,
          "hass",
          {
            configurable: true,
            enumerable: false,
            get: hassDescriptor.get,
            set: hassDescriptor.set,
          },
        );
      }

      this._implementationLoaded = true;

      if (this._hass) {
        hassDescriptor?.set?.call(
          this,
          this._hass,
        );
      }

    } catch (error) {
      console.error(
        "Virtual Device Manager: Failed to load frontend module",
        error,
      );

      this.innerHTML = `
        <ha-card>
          <div style="
            padding: 16px;
            color: var(--error-color);
          ">
            Virtual Device Manager konnte nicht geladen werden.
          </div>
        </ha-card>
      `;
    }
  }

  _applyHass(hass) {
    const descriptor =
      Object.getOwnPropertyDescriptor(
        this,
        "hass",
      );

    descriptor?.set?.call(
      this,
      hass,
    );
  }
}


if (
  !customElements.get(
    "virtual-device-manager",
  )
) {
  customElements.define(
    "virtual-device-manager",
    VirtualDeviceManagerBootstrap,
  );
}

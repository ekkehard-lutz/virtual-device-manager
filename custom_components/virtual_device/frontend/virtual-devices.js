class VirtualDeviceManagerBootstrap
  extends HTMLElement {

  constructor() {
    super();

    this._hass = undefined;
    this._narrow = false;
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

  set narrow(narrow) {
    this._narrow = Boolean(narrow);

    if (this._implementationLoaded) {
      this._applyNarrow(this._narrow);
    }
  }

  get narrow() {
    return this._narrow;
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
        throw new Error("Virtual Device Manager: implementation was not exported");
      }

      /* Copy implementation methods onto the element created by Home Assistant. */
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

      /* Install the implementation's hass setter directly. */
      const hassDescriptor =
        Object.getOwnPropertyDescriptor(
          Implementation.prototype,
          "hass",
        );

      const narrowDescriptor =
        Object.getOwnPropertyDescriptor(
          Implementation.prototype,
          "narrow",
        );

      if (
        narrowDescriptor &&
        narrowDescriptor.set
      ) {
        Object.defineProperty(
          this,
          "narrow",
          {
            configurable: true,
            enumerable: false,
            get: narrowDescriptor.get,
            set: narrowDescriptor.set,
          },
        );
      }

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

      narrowDescriptor?.set?.call(
        this,
        this._narrow,
      );

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
            Virtual Device Manager failed to load.
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

  _applyNarrow(narrow) {
    const descriptor =
      Object.getOwnPropertyDescriptor(
        this,
        "narrow",
      );

    descriptor?.set?.call(
      this,
      narrow,
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

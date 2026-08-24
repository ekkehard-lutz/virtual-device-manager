export function addStyles(component) {
  if (component.querySelector("style")) {
    return;
  }

  const style = document.createElement("style");

  style.textContent = `
    :host {
      display: block;
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 16px;
    }

    .title {
      font-size: 20px;
      font-weight: 500;
    }

    .content {
      padding: 0 16px 16px;
    }

    .loading,
    .empty,
    .error,
    .message {
      padding: 16px 0;
      color: var(--secondary-text-color);
      white-space: pre-line;
    }

    .error {
      color: var(--error-color);
    }

    .device-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .device {
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      padding: 16px;
    }

    .device-main {
      min-width: 0;
      flex: 1;
    }

    .device-name {
      font-size: 18px;
      font-weight: 500;
    }

    .device-details {
      display: flex;
      flex-wrap: wrap;
      gap: 20px;
      margin-top: 8px;
      color: var(--secondary-text-color);
      font-size: 14px;
    }

    .device-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .device-actions {
      display: flex;
      align-items: center;
      gap: 2px;
      flex-shrink: 0;
    }

    .edit-button,
    .delete-button,
    .history-sync-button,
    .add-entity-button {
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      width: 40px;
      height: 40px;
      padding: 0;
      border: none;
      border-radius: 50%;
      background: transparent;
      color: var(--secondary-text-color);
      cursor: pointer;
    }

    .edit-button:hover,
    .history-sync-button:hover,
    .add-entity-button:hover {
      color: var(--primary-color);
      background: var(--secondary-background-color);
    }

    .entities-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-top: 20px;
      padding-top: 12px;
      border-top: 1px solid var(--divider-color);
    }

    .entities-title {
      font-size: 15px;
      font-weight: 500;
    }

    .entity-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 8px;
    }

    .entities-empty {
      padding: 8px 0;
      color: var(--secondary-text-color);
      font-size: 14px;
    }

    .entity {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 12px;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      background: var(--secondary-background-color);
    }

    .entity-main {
      min-width: 0;
      flex: 1;
    }

    .entity-name {
      font-size: 15px;
      font-weight: 500;
      overflow-wrap: anywhere;
    }

    .entity-details {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 4px;
      color: var(--secondary-text-color);
      font-size: 13px;
    }

    .entity-id {
      margin-top: 4px;
      color: var(--secondary-text-color);
      font-family: monospace;
      font-size: 12px;
      overflow-wrap: anywhere;
    }

    .entity-actions {
      display: flex;
      align-items: center;
      gap: 2px;
      flex-shrink: 0;
    }

    .edit-entity-button,
    .delete-entity-button {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      padding: 0;
      border: none;
      border-radius: 50%;
      background: transparent;
      color: var(--secondary-text-color);
      cursor: pointer;
    }

    .edit-entity-button:hover {
      color: var(--primary-color);
      background: var(--secondary-background-color);
    }

    .delete-entity-button:hover {
      color: var(--error-color);
      background: var(--secondary-background-color);
    }

    .delete-button {
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      width: 40px;
      height: 40px;
      padding: 0;
      border: none;
      border-radius: 50%;
      background: transparent;
      color: var(--secondary-text-color);
      cursor: pointer;
    }

    .delete-button:hover {
      color: var(--error-color);
      background: var(--secondary-background-color);
    }

    .dialog-backdrop {
      position: fixed;
      inset: 0;
      z-index: 1000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      background: rgba(0, 0, 0, 0.45);
    }

    .dialog {
      width: min(500px, 100%);
      background: var(--card-background-color);
      color: var(--primary-text-color);
      border-radius: 12px;
      box-shadow: var(--ha-card-box-shadow);
      overflow: hidden;
    }

    .dialog-title {
      padding: 20px 20px 12px;
      font-size: 20px;
      font-weight: 500;
    }

    .dialog-content {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 8px 20px 20px;
    }

    .dialog-content label {
      margin-top: 8px;
      font-size: 14px;
      color: var(--secondary-text-color);
    }

    .name-input,
    .label-select {
      box-sizing: border-box;
      width: 100%;
      min-height: 44px;
      padding: 10px 12px;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      background: var(--primary-background-color);
      color: var(--primary-text-color);
      font: inherit;
    }

    .dialog-error {
      padding: 10px;
      border-radius: 6px;
      background: var(--error-color);
      color: var(--text-primary-color);
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      padding: 12px 20px 20px;
    }

    .dialog-actions button {
      min-height: 40px;
      padding: 0 18px;
      border: none;
      border-radius: 6px;
      font: inherit;
      cursor: pointer;
    }

    .cancel-button {
      background: transparent;
      color: var(--primary-text-color);
    }

    .create-button,
    .save-button,
    .sync-confirm-button {
      background: var(--primary-color);
      color: var(--text-primary-color);
    }

    .create-button:disabled,
    .save-button:disabled,
    .sync-confirm-button:disabled {
      opacity: 0.6;
      cursor: default;
    }

    .physical-name-warning {
      margin-top: 12px;
      padding: 12px;
      border-radius: 6px;
      background: var(--secondary-background-color);
      color: var(--primary-text-color);
    }

    .physical-name-warning.hidden {
      display: none;
    }

    .confirm-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 8px;
      color: var(--primary-text-color) !important;
    }

    .confirm-row input {
      width: auto;
      min-height: auto;
    }

    @media (max-width: 600px) {
      .header {
        align-items: flex-start;
        flex-direction: column;
      }

      .add-button {
        width: 100%;
      }

      .device-details {
        flex-direction: column;
        gap: 4px;
      }

      .device {
        align-items: stretch;
      }

      .device-header {
        align-items: flex-start;
      }

      .entity {
        align-items: flex-start;
      }

      .entity-actions {
        flex-direction: column;
      }

      .entity-details {
        gap: 4px 12px;
      }
    }
  `;

  component.appendChild(style);
}

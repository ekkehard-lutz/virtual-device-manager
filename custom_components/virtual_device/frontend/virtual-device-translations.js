const EMERGENCY_FALLBACK = "Translation unavailable";

export function createTranslator(messages = {}) {
  return (key, parameters = {}) => {
    const value = key.split(".").reduce((current, part) => current?.[part], messages);
    const template = typeof value === "string"
      ? value
      : messages.messages?.missing_translation || EMERGENCY_FALLBACK;
    if (typeof value !== "string") {
      console.warn(`Virtual Device Manager: missing translation '${key}'`);
    }
    return template.replace(/\{([^{}]+)\}/g, (match, name) =>
      Object.hasOwn(parameters, name) ? String(parameters[name]) : match,
    );
  };
}

export async function loadTranslations(hass) {
  return hass.callWS({
    type: "virtual_device/get_translations",
    language: hass.language || "en",
  });
}

export function resolveEntityName(name, deviceClass, translate) {
  const enteredName = String(name || "").trim();
  return enteredName || translate(`device_classes.${deviceClass}`);
}

export async function loadVirtualDevices(hass) {
  const result = await hass.callWS({
    type: "virtual_device/get_virtual_devices",
  });

  return result.devices || [];
}


export async function loadEntityConfig(hass) {
  return await hass.callWS({
    type: "virtual_device/get_entity_config",
  });
}


export async function loadLabels(hass) {
  const result = await hass.callWS({
    type: "config/label_registry/list",
  });

  return result.labels || result;
}


export async function deleteVirtualDevice(
  hass,
  deviceId,
) {
  await hass.callWS({
    type: "virtual_device/delete_virtual_device",
    device_id: deviceId,
  });
}


export async function createVirtualDevice(
  hass,
  data,
) {
  await hass.callService(
    "virtual_device",
    "create_virtual_device",
    data,
  );
}


export async function updateVirtualDevice(
  hass,
  data,
) {
  return await hass.callWS({
    type: "virtual_device/update_virtual_device",
    device_id: data.device_id,
    name: data.name,
    label_ref: data.label_ref,
    confirm_physical_name_conflict:
      data.confirm_physical_name_conflict ?? false,
  });
}


export async function addVirtualEntity(
  hass,
  data,
) {
  const result = await hass.callWS({
    type: "virtual_device/add_virtual_entity",
    device_id: data.device_id,
    device_class: data.device_class,
    aggregation: data.aggregation,
    name: data.name,
    include_filter: data.include_filter,
    exclude_filter: data.exclude_filter,
  });

  return result.device;
}


export async function updateVirtualEntity(
  hass,
  data,
) {
  const result = await hass.callWS({
    type: "virtual_device/update_virtual_entity",
    device_id: data.device_id,
    entity_id: data.entity_id,
    device_class: data.device_class,
    aggregation: data.aggregation,
    name: data.name,
    include_filter: data.include_filter,
    exclude_filter: data.exclude_filter,
  });

  return result.device;
}


export async function deleteVirtualEntity(
  hass,
  data,
) {
  const result = await hass.callWS({
    type: "virtual_device/delete_virtual_entity",
    device_id: data.device_id,
    entity_id: data.entity_id,
  });

  return result.device;
}


export async function loadSourceEntities(hass, deviceId, entityId) {
  return await hass.callWS({
    type: "virtual_device/get_source_entities",
    device_id: deviceId,
    entity_id: entityId,
  });
}


export async function synchronizeHistory(
  hass,
  deviceId,
) {
  return await hass.callWS({
    type: "virtual_device/history_sync",
    device_id: deviceId,
  });
}

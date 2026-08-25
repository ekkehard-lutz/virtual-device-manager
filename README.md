# Virtual Device Manager for Home Assistant

Virtual Device Manager (VDM) creates virtual sensor devices in Home Assistant whose values are dynamically aggregated from source entities selected through Home Assistant labels. Source membership updates automatically when compatible entities are added to or removed from the referenced label.

## Features

- Label-based Virtual Devices with multiple independently configured Virtual Entities
- Dynamic source discovery and runtime updates without restarting Home Assistant
- Stable Virtual Device, Virtual Entity, entity, and unique identities
- Home Assistant Device Registry and Entity Registry integration
- Configurable Virtual Device and Virtual Entity names
- Energy, power, temperature, voltage, and electric-current sensors
- Sum, average, minimum, maximum, and median aggregation
- Compatible-unit normalization before aggregation
- Localized management panel with English and German support
- Manual history synchronization to Home Assistant long-term statistics
- Source counts and on-demand source-entity details
- Warning when a referenced Home Assistant label no longer exists
- Administrator-only management panel and WebSocket API

## How it works

```text
Home Assistant Label
        │
        │ selects source entities
        ▼
Virtual Device
        │
        ├── Virtual Entity (sum)
        ├── Virtual Entity (average)
        └── Virtual Entity (median)
```

VDM references, but does not own or manage, the Home Assistant label. The label determines which source entities are eligible. A Virtual Device can contain multiple Virtual Entities, each with its own sensor device class and aggregation method. VDM reconciles source relationships and reacts to source state changes, so matching label membership and sensor values are updated at runtime.

## Installation

### HACS

1. In HACS, search for **Virtual Device Manager** under integrations.
2. If it is not listed, add `https://github.com/ekkehard-lutz/virtual-device-manager` as a custom repository with category **Integration**.
3. Install the integration and restart Home Assistant when prompted.
4. Go to **Settings → Devices & services → Add integration → Virtual Device Manager**.

### Manual installation

Copy `custom_components/virtual_device` from this repository to:

```text
/config/custom_components/virtual_device
```

Restart Home Assistant, then add **Virtual Device Manager** from **Settings → Devices & services → Add integration**.

## Getting started

1. Create a Home Assistant label such as `Lighting`.
2. Assign the label to the source entities that should participate.
3. Open **Virtual Device Manager** from the Home Assistant sidebar.
4. Create a Virtual Device based on the `Lighting` label.
5. Add a Virtual Entity with device class `power` and aggregation `sum`.
6. Use the resulting Home Assistant sensor wherever you need the combined power value.

Adding or removing compatible entities from the label automatically changes the virtual sensor's sources. Each source must have the same sensor device class as the Virtual Entity and a compatible unit.

## Supported sensor types

| Device class | Native unit |
|---|---:|
| `energy` | Wh |
| `power` | W |
| `temperature` | °C |
| `voltage` | V |
| `current` | A |

Compatible source units are converted to the native unit before aggregation. This includes Home Assistant-supported units for these device classes and the electrical SI-scaled units handled by VDM.

## Aggregation methods

| Method | Result |
|---|---|
| `sum` | Sum of all source values |
| `avg` | Arithmetic average of all source values |
| `min` | Smallest source value |
| `max` | Largest source value |
| `median` | Median source value |

## Virtual Devices and stable identities

A **Home Assistant label** selects source entities. A **Virtual Device** is the stable Home Assistant device created by VDM for that label reference. A **Virtual Entity** is an aggregated sensor belonging to the Virtual Device.

Virtual Device and Virtual Entity identities do not depend on the label's current display name. Renaming a label therefore does not recreate the Virtual Device or its sensor entities. User-defined Virtual Device and Virtual Entity names can be changed independently without changing their stable identities.

## Label lifecycle

- Deleting a Virtual Device does not delete its Home Assistant label.
- Deleting a Home Assistant label does not delete or modify the Virtual Device or its Virtual Entities.
- If the referenced label is missing, the VDM panel shows a red warning icon beside the Virtual Device name. Hovering over the icon indicates that the label has been deleted.
- VDM retains the original label ID. It does not relink a new label by matching its display name.
- If Home Assistant later provides the same referenced label ID again, the relationship is valid automatically.

## Names and localization

The VDM panel supports English and German and follows the active Home Assistant frontend language, with English as the fallback. When a Virtual Entity is created without a custom name, VDM stores the localized device-class name in the Home Assistant Entity Registry. Later language changes do not rename existing entities, and user-defined registry names take precedence. Virtual Device names are maintained through the Home Assistant Device Registry.

## History synchronization

History synchronization is started manually for one Virtual Device from the VDM panel. VDM first reconciles the currently applicable source entities, then calculates historical values for each Virtual Entity using its aggregation and unit-conversion rules.

VDM writes hourly long-term statistics through Home Assistant's supported statistics import API. It does not write directly to the Recorder database. Historical raw states and five-minute statistics are used for calculation where available but are not written back because Home Assistant does not provide supported import APIs for them. Re-synchronization safely inserts or updates calculated hourly slots; obsolete slots that are no longer present in a later calculation are not removed.

## Administrator access

Virtual Device Manager is an administrator-only management interface. Only Home Assistant administrators can see the sidebar panel, and all VDM WebSocket management commands also require administrator privileges on the server. The resulting Virtual Entities are normal Home Assistant entities and follow Home Assistant's usual entity visibility and access behavior.

## Home Assistant integration

Virtual Devices are registered in Home Assistant's Device Registry. Their Virtual Entities are normal sensor entities in the Entity Registry and can be used in:

- dashboards
- automations
- templates
- long-term statistics
- the Energy Dashboard when an energy sensor's characteristics meet Home Assistant's requirements

## Requirements

- Home Assistant 2026.8.0 or newer
- HACS only when using the HACS installation method

## Troubleshooting

### VDM does not appear in the sidebar

The active Home Assistant user must be an administrator. Also confirm that the integration was added under **Settings → Devices & services**.

### A Virtual Device shows a red warning icon

The referenced Home Assistant label no longer exists. VDM keeps the Virtual Device and its original label reference unchanged.

### A Virtual Entity shows `unknown` after startup

VDM reconciles source membership and current source states during startup. The Virtual Entity remains `unknown` when no matching source currently has a usable numeric value and compatible unit. Check the label assignments and the source entities' states, device classes, and units.

### The frontend appears outdated after upgrading

Reload the Home Assistant page. If the browser still serves older frontend files, perform a hard refresh.

## Development

Install the dependencies from `requirements-dev.txt`, then run:

```bash
python -m pytest -q
ruff check .
```

The repository's validation workflow uses Python 3.12.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

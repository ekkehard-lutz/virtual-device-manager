# Home Assistant Virtual Device Manager

A Home Assistant custom integration for creating and managing virtual devices and virtual sensor entities based on Home Assistant labels.

## History synchronization (Home Assistant 2026.8)

History synchronization is an explicit per-Virtual-Device action. It freezes the
currently assigned physical source entities and calculates raw, aligned
five-minute, and aligned hourly virtual history with the same aggregation and unit
conversion semantics used by live entities.

Home Assistant Core 2026.8 supports reading all three resolutions and importing
hourly internal statistics through `async_import_statistics()`. It does not expose
supported public integration APIs for importing historical raw states, importing
five-minute statistics, or atomically replacing a selected statistics range.
Consequently VDM V1 persists hourly long-term statistics only. Re-synchronization
uses safe hourly upserts: recalculated slots are inserted or updated, while an
obsolete old slot absent from the new result cannot safely be removed. VDM never
uses direct Recorder SQL, fabricated historical events, private table-specific
imports, or destructive clear-and-reimport behavior.

## Status

**Version: 0.1.0**

The first release of the Virtual Device Manager.

The integration creates virtual devices whose source entities are selected through an existing Home Assistant label. Virtual devices and virtual entities are managed independently from the labels themselves.

## Concept

```text
Home Assistant Label
        │
        │ label_ref
        ▼
Virtual Device
        │
        ├── Virtual Entity
        ├── Virtual Entity
        └── Virtual Entity
```

The label itself is **not managed by the Virtual Device Manager**. It can be created, renamed, assigned, or removed by Home Assistant or another integration.

The Virtual Device Manager stores a reference to the selected label and uses entities carrying that label as source entities.

### Stable virtual devices

A virtual device has its own stable ID.

Changing the label assigned to an existing virtual device does **not** change its virtual device ID.

For example:

```text
Label: Beleuchtung
        ↓
Virtual Device ID: virtual_beleuchtung
Name: Virtual Licht
```

If the label is subsequently renamed:

```text
Label: Licht
        ↓
Virtual Device ID: virtual_beleuchtung
Name: Virtual Licht
```

The virtual device remains the same object.

The device name is not automatically changed when the referenced Home Assistant label is renamed.

### Stable virtual entities

Virtual entity IDs are based on the stable virtual device ID.

For example:

```text
Virtual Device:
    ID: virtual_beleuchtung

Virtual Entity:
    ID: virtual_beleuchtung_power
```

Renaming the referenced Home Assistant label therefore does not change existing virtual entity IDs.

### Virtual devices without entities

A virtual device can exist without any virtual entities.

Creating the device and creating its entities are independent operations.

If the last virtual entity of a device is deleted, the virtual device itself remains available.

### Labels are independent

The Virtual Device Manager does not own the Home Assistant label.

Deleting a virtual device does not delete its referenced Home Assistant label.

Likewise, changing or deleting a Home Assistant label does not implicitly delete the virtual device configuration.

## Features

- Create and manage virtual devices
- Use an existing Home Assistant label as the source for a virtual device
- Create multiple virtual sensor entities per virtual device
- Configure the aggregation method of each virtual entity
- Supported aggregations:
  - `sum`
  - `avg`
  - `min`
  - `max`
- Configure sensor device class
- Configure sensor unit
- Configure entity names
- Virtual devices can exist without entities
- Virtual device IDs remain stable when labels are renamed
- Existing virtual entity IDs remain stable
- Virtual device names are independent from Home Assistant label names
- Persistent storage of virtual device and entity configuration
- Automatic updating of virtual sensors when source entities change
- Home Assistant services for managing virtual devices
- WebSocket API for the frontend
- Dedicated Home Assistant sidebar panel

## Installation

### HACS

The Virtual Device Manager can be installed through HACS.

If the repository is not yet available in your HACS instance, add the GitHub repository as a custom repository:

```text
https://github.com/ekkehard-lutz/virtual-device-manager
```

Select **Integration** as the repository category and install **Virtual Device Manager**.

After installation, restart Home Assistant if requested by HACS.

Then add **Virtual Device Manager** through:

```text
Settings → Devices & services → Add integration
```

### Manual installation

Copy the integration directory:

```text
custom_components/virtual_device/
```

to:

```text
/config/custom_components/virtual_device/
```

Then restart Home Assistant and add **Virtual Device Manager** through the integrations page.

## Configuration

After installation, add **Virtual Device Manager** through:

```text
Settings → Devices & services → Add integration
```

The integration provides a dedicated **Virtual Device Manager** panel in the Home Assistant sidebar.

The panel is used to create and manage virtual devices and their virtual entities.

## Virtual Devices

A virtual device contains:

- a stable virtual device ID
- a name
- a reference to a Home Assistant label
- zero or more virtual entities

The Home Assistant label determines which source entities are available to the virtual device.

The label reference is stored internally as the Home Assistant label ID, not as the label's display name.

This means that renaming a Home Assistant label does not break the relationship between the label and the virtual device.

## Virtual Entities

A virtual entity belongs to one virtual device.

A virtual entity can define:

- entity ID
- name
- device class
- aggregation
- unit

The source values are obtained from entities associated with the virtual device's label.

### Aggregation

The following aggregation methods are supported:

| Aggregation | Description |
|---|---|
| `sum` | Sum all source values |
| `avg` | Calculate the average of all source values |
| `min` | Use the smallest source value |
| `max` | Use the largest source value |

The resulting value is exposed as a Home Assistant sensor entity.

## Services

The integration provides the following Home Assistant services under the `virtual_device` domain.

### `virtual_device.create_virtual_device`

Creates a virtual device.

Required:

```yaml
label_ref: "label-id"
```

Optional:

```yaml
name: "My Virtual Device"
```

### `virtual_device.update_virtual_device`

Updates an existing virtual device.

Required:

```yaml
device_id: "virtual_beleuchtung"
```

Optional:

```yaml
name: "Virtual Licht"
label_ref: "another-label-id"
```

Changing `label_ref` does not change the virtual device ID.

### `virtual_device.delete_virtual_device`

Deletes a virtual device and its stored configuration.

Required:

```yaml
device_id: "virtual_beleuchtung"
```

Deleting the virtual device does not delete the referenced Home Assistant label.

## WebSocket API

The frontend communicates with the integration through Home Assistant's WebSocket API.

The following commands are provided:

```text
virtual_device/get_virtual_devices
virtual_device/delete_virtual_device
virtual_device/update_virtual_device
virtual_device/add_virtual_entity
virtual_device/update_virtual_entity
virtual_device/delete_virtual_entity
```

These commands are intended primarily for the integrated frontend panel.

## Home Assistant entities

Virtual entities are exposed as Home Assistant sensor entities.

Their Home Assistant device association uses the stable virtual device identifier.

The integration does not create source entities. It only creates the virtual entities configured by the user.

## Persistent storage

Virtual Device Manager stores its configuration using Home Assistant's persistent storage mechanism.

The stored configuration contains the virtual devices and their virtual entities.

The Home Assistant label registry remains the source of truth for the referenced labels.

## Development

The project uses a Python virtual environment for development and testing.

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Run the complete test suite:

```bash
python -m pytest -q
```

The current test suite covers, among other things:

- virtual device creation
- virtual device updates
- virtual device deletion
- stable virtual device IDs
- stable virtual entity IDs
- virtual entity creation
- virtual entity updates
- virtual entity deletion
- persistent storage
- sensor creation and updates
- source entity discovery
- source value aggregation
- validation
- Home Assistant services
- WebSocket commands
- integration setup and unloading

## Project structure

```text
virtual-device-manager/
├── custom_components/
│   └── virtual_device/
│       ├── brand/
│       ├── frontend/
│       ├── translations/
│       ├── __init__.py
│       ├── aggregator.py
│       ├── config_flow.py
│       ├── const.py
│       ├── coordinator.py
│       ├── entity.py
│       ├── exceptions.py
│       ├── manifest.json
│       ├── models.py
│       ├── sensor.py
│       ├── source_finder.py
│       ├── source_manager.py
│       ├── statistics.py
│       ├── storage.py
│       ├── strings.json
│       ├── unit_converter.py
│       ├── validation.py
│       ├── virtual_device_manager.py
│       ├── virtual_device_services.py
│       ├── virtual_device_workflow.py
│       └── websocket.py
├── tests/
├── .gitignore
├── hacs.json
├── LICENSE
├── package.json
├── pyproject.toml
├── README.md
└── requirements-dev.txt
```

## Requirements

- Home Assistant `2026.8.0` or newer
- HACS for HACS-based installation

## Roadmap

### 0.1.x – Foundation and first stable release

- Virtual device management
- Virtual entity management
- Label-based source selection
- Persistent configuration
- Virtual sensor aggregation
- Home Assistant service API
- WebSocket frontend API

### Future releases

Possible future improvements include:

- Additional virtual entity types
- Additional aggregation methods
- More configurable source selection
- Improved frontend management
- Additional statistics
- More advanced virtual device functionality

The roadmap is intentionally kept open while the first stable releases are evaluated in practical Home Assistant installations.

## License

This project is licensed under the **MIT License**.

See the `LICENSE` file for the complete license text.

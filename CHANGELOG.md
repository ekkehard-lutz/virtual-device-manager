# Changelog

## 1.1.0

### Added

- Virtual Entity source filters with separate Include and Exclude groups and `all` or `any` matching.
- Exact, nested dot-notation filtering of Entity Registry (`entity.*`), Device Registry (`device.*`), and runtime state (`state.*`) metadata.
- Equals, not-equals, contains, not-contains, starts-with, ends-with, regular-expression, is-empty, and is-not-empty operators.
- Runtime diagnostics for filter attributes and conditions.
- Consistent filtered source selection for live aggregation, source details and counts, reconciliation, and history synchronization.
- Backward-compatible defaults for existing Virtual Entities without filters.

### Fixed

- Restored native Home Assistant mobile navigation and its menu button in narrow VDM layouts.
- Improved the Virtual Entity source-filter editor layout on narrow screens.

## 1.0.0

Initial stable release of Virtual Device Manager.

### Added

- Label-based Virtual Devices with multiple virtual sensor entities.
- Dynamic source discovery and reconciliation when label membership changes.
- Energy, power, temperature, voltage, and electric-current device classes.
- Sum, average, minimum, maximum, and median aggregation with compatible-unit normalization.
- Stable Home Assistant Device Registry and Entity Registry integration.
- Configurable Virtual Device and Virtual Entity names.
- English and German management interface.
- Runtime source counts and source-entity details.
- Manual synchronization of hourly long-term statistics.
- Missing-label detection and warnings without modifying stored devices.
- Administrator-only management panel and server-side WebSocket access.

# Tracking Integration

This document explains Edison’s tracking integration: how tasks can be linked to an external tracker, how **status sync** works, and how to extend the system for a **custom tracking system**.

## Supported tracking systems

Edison supports multiple tracking systems. Supported tracking systems include:
- Linear
- GitHub Issues

## Configuration (YAML)

Tracking integration is configured via YAML in your project’s config layer under `.edison/` (and overlays).

Typical places to configure tracking:
- `.edison/config/project.yml` (project metadata)
- `.edison/config/*.yml` / `.edison/config/*.yaml` (tracking configuration and overrides)

If you need to inspect the merged configuration, use the Edison CLI to view configuration in a single place.

## Status sync

When tasks transition inside Edison, the system can perform **status sync** with an external tracker / tracking system.

The key idea:
- Edison remains the source of truth for local workflow state.
- The external tracker mirrors state transitions (sync status) so teammates can follow progress.

## Extending for a custom tracking system

To integrate a custom tracking system, implement an extension that:
- maps Edison task identifiers to external tracker identifiers
- defines a status mapping (Edison state → external tracker state)
- handles auth and API requests at the boundary

This is an extension point: you can **extend** the integration without changing core task workflows.

## Troubleshooting

### Common issues

Common issues include:
- Missing credentials for the tracking system
- Misconfigured YAML (wrong keys, missing sections)
- Network/API errors from the external tracker

If status sync fails, verify configuration and then check logs for the underlying error.


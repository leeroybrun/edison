# Provider configuration

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Provider credentials come from environment variables.
- Redirect URIs must match provider console exactly.
- Always validate OAuth `state` parameter.

### Checks

- No secrets in client bundles.
- Callback handlers validate provider responses.
<!-- /section: patterns -->

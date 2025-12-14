# Error Handling

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Wrap handlers to catch errors and convert to HTTP responses.
- Log server-side details; return safe messages to clients.
- Map known errors to 4xx; reserve 5xx for unexpected failures.
<!-- /section: patterns -->


# Client setup patterns

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Keep client code thin: initiate auth flow, display session state.
- Post-auth redirects use placeholders (no app-specific paths).

```ts
await authClient.signIn.google({
  callbackURL: '<post-auth-redirect>',
})
```
<!-- /section: patterns -->

# Better Auth Provider Configuration Guidelines

Best practices for configuring OAuth/OIDC providers in Better Auth.

## Provider Setup Patterns

### OAuth 2.0 Providers (Google, GitHub, etc.)

```typescript
import { betterAuth } from 'better-auth';
import { google, github } from 'better-auth/providers';

const auth = await betterAuth({
  secret: process.env.BETTER_AUTH_SECRET,
  baseURL: process.env.BASE_URL,
  database: db,
  providers: [
    google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    }),
    github({
      clientId: process.env.GITHUB_CLIENT_ID,
      clientSecret: process.env.GITHUB_CLIENT_SECRET,
    }),
  ],
});
```

### OIDC Providers

```typescript
import { oidc } from 'better-auth/providers';

const auth = await betterAuth({
  providers: [
    oidc({
      id: 'custom-provider',
      issuer: process.env.OIDC_ISSUER,
      clientId: process.env.OIDC_CLIENT_ID,
      clientSecret: process.env.OIDC_CLIENT_SECRET,
    }),
  ],
});
```

## Credential Management

### Environment Variables
```bash
# .env.local (never commit this file)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
BETTER_AUTH_SECRET=your-secure-random-secret
```

### Secrets Vault Integration
```typescript
// Using a secrets manager
const googleSecret = await vault.getSecret('google-client-secret');
const auth = await betterAuth({
  providers: [
    google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: googleSecret,
    }),
  ],
});
```

## Redirect URI Configuration

### Setting Up Redirect URIs
Each OAuth provider requires exact redirect URI matches.

```typescript
// Development
https://localhost:3000/api/auth/callback/google

// Staging
https://staging.example.com/api/auth/callback/google

// Production
https://app.example.com/api/auth/callback/google
```

### Handler Implementation
```typescript
// API route to handle OAuth callbacks
export const GET = async (req: NextRequest) => {
  const authRes = await auth.handler(req);
  return authRes;
};
```

## Scope Management

### Google Scopes
```typescript
google({
  clientId: process.env.GOOGLE_CLIENT_ID,
  clientSecret: process.env.GOOGLE_CLIENT_SECRET,
  scopes: ['openid', 'profile', 'email'],
})
```

### GitHub Scopes
```typescript
github({
  clientId: process.env.GITHUB_CLIENT_ID,
  clientSecret: process.env.GITHUB_CLIENT_SECRET,
  scopes: ['user:email'], // Request specific scopes
})
```

## Provider-Specific Configuration

### Custom Provider Fields
```typescript
// Mapping provider fields to user schema
google({
  clientId: process.env.GOOGLE_CLIENT_ID,
  clientSecret: process.env.GOOGLE_CLIENT_SECRET,
  mapProfileToUser: (profile) => ({
    email: profile.email,
    name: profile.name,
    image: profile.picture,
    // Custom field mapping
  }),
})
```

## Testing Provider Configuration

```typescript
// Test provider setup
it('should initialize auth with google provider', async () => {
  const auth = await betterAuth({
    providers: [google(config)],
  });
  
  expect(auth.providers).toContain('google');
});
```

## Anti-Patterns

- Hardcoding client IDs and secrets in code
- Using same credentials across dev/staging/production
- Not validating redirect URI matches provider config
- Storing plaintext secrets in repository
- Using outdated provider libraries
- Requesting excessive scopes from providers
- Not implementing fallback providers for resilience

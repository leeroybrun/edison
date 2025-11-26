# Better Auth Client Setup Patterns Guidelines

Best practices for setting up Better Auth on the client side.

## Client Library Initialization

### Next.js Client Setup
```typescript
// lib/auth-client.ts
import { createAuthClient } from 'better-auth/client';

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_BASE_URL,
  plugins: [],
});

// Usage in client components
'use client';

import { authClient } from '@/lib/auth-client';

export function LoginButton() {
  const handleLogin = async () => {
    try {
      await authClient.signIn.google();
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return <button onClick={handleLogin}>Sign in with Google</button>;
}
```

### React Setup
```typescript
// src/lib/auth-client.ts
import { createAuthClient } from 'better-auth/client';

const authClient = createAuthClient({
  baseURL: 'http://localhost:3000',
});

export default authClient;

// src/hooks/useAuth.ts
import { useQuery } from '@tanstack/react-query';
import authClient from '@/lib/auth-client';

export function useAuth() {
  return useQuery({
    queryKey: ['session'],
    queryFn: () => authClient.getSession(),
  });
}
```

## Session Management on Client

### Fetching User Session
```typescript
// Get current session
const session = await authClient.getSession();

if (session) {
  console.log('User:', session.user);
  console.log('Expires:', session.expires);
} else {
  console.log('Not logged in');
}
```

### Watch Session Changes
```typescript
// React component with session watching
import { useEffect, useState } from 'react';
import authClient from '@/lib/auth-client';

export function UserProfile() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = authClient.onSessionChange((session) => {
      setUser(session?.user || null);
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  if (loading) return <div>Loading...</div>;
  if (!user) return <div>Not logged in</div>;

  return <div>Welcome, {user.name}</div>;
}
```

## Authentication Flows

### Sign Up Flow
```typescript
const handleSignUp = async (email: string, password: string, name: string) => {
  try {
    const { data, error } = await authClient.signUp.email({
      email,
      password,
      name,
      callbackURL: '/dashboard',
    });

    if (error) {
      console.error('Sign up error:', error.message);
      return;
    }

    // Redirect on success handled by callbackURL
  } catch (error) {
    console.error('Unexpected error:', error);
  }
};
```

### Sign In Flow
```typescript
const handleSignIn = async (email: string, password: string) => {
  try {
    const { data, error } = await authClient.signIn.email({
      email,
      password,
      callbackURL: '/dashboard',
    });

    if (error) {
      // Handle specific error types
      if (error.status === 401) {
        setError('Invalid email or password');
      } else {
        setError('Sign in failed. Please try again.');
      }
      return;
    }

    // Success - redirect handled by callbackURL
  } catch (error) {
    console.error('Unexpected error:', error);
  }
};
```

### Sign Out Flow
```typescript
const handleSignOut = async () => {
  try {
    await authClient.signOut({
      fetchOptions: {
        onSuccess: () => {
          // Clear local state, redirect to login
          window.location.href = '/login';
        },
      },
    });
  } catch (error) {
    console.error('Sign out failed:', error);
  }
};
```

## State Management Integration

### Zustand Store Pattern
```typescript
import { create } from 'zustand';
import authClient from '@/lib/auth-client';

interface AuthStore {
  user: any | null;
  loading: boolean;
  error: string | null;
  init: () => Promise<void>;
  signOut: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  loading: true,
  error: null,
  init: async () => {
    try {
      const session = await authClient.getSession();
      set({ user: session?.user, loading: false });
    } catch (error) {
      set({ error: 'Failed to load session', loading: false });
    }
  },
  signOut: async () => {
    await authClient.signOut();
    set({ user: null });
  },
}));
```

## Protected Routes/Pages

### Next.js Protected Routes
```typescript
// app/dashboard/page.tsx
import { redirect } from 'next/navigation';
import { auth } from '@/lib/auth';

export default async function DashboardPage() {
  const session = await auth.api.getSession();

  if (!session) {
    redirect('/login');
  }

  return <div>Welcome, {session.user.name}</div>;
}
```

### React Router Protection
```typescript
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) return <div>Loading...</div>;
  if (!user) return <Navigate to="/login" />;

  return children;
}

// Usage
<Routes>
  <Route
    path="/dashboard"
    element={
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    }
  />
</Routes>
```

## Error Handling on Client

```typescript
// Centralized error handling
async function handleAuthOperation(operation) {
  try {
    return await operation();
  } catch (error) {
    if (error.status === 401) {
      // Unauthorized - redirect to login
      window.location.href = '/login';
    } else if (error.status === 429) {
      // Rate limited
      setError('Too many attempts. Please try again later.');
    } else if (error.status === 500) {
      // Server error
      setError('Server error. Please try again.');
    } else {
      setError('An error occurred. Please try again.');
    }
  }
}
```

## Anti-Patterns

- Storing session token in LocalStorage
- Not checking session existence before rendering protected content
- Missing error handling in auth flows
- Hardcoding API URLs in client code
- Trusting unvalidated session data from client
- Not handling session expiration on client
- Using blocking operations during initialization

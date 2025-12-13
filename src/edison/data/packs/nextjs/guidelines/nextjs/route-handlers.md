# Route Handlers (API)

Route Handlers allow you to create custom request handlers for a given route using the Web Request and Response APIs.

## Convention

- Implement handlers in `app/api/<version>/<resource>/route.ts`.
- Keep handler thin; delegate business logic to modules.
- Use `NextRequest` and `NextResponse` from `next/server`.

## HTTP Methods

Support for standard HTTP methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, and `OPTIONS`.

### Example: GET and POST

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';

export async function GET(request: NextRequest) {
  // Handle GET request
  return NextResponse.json({ message: 'Hello from GET' });
}

const createSchema = z.object({
  title: z.string().min(1),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { title } = createSchema.parse(body);
    
    // Perform action...
    
    return NextResponse.json({ title }, { status: 201 });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ errors: error.errors }, { status: 400 });
    }
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
```

### Example: PUT, PATCH, DELETE

```typescript
import { NextRequest, NextResponse } from 'next/server';

export async function PUT(request: NextRequest) {
  return NextResponse.json({ message: 'Updated via PUT' });
}

export async function PATCH(request: NextRequest) {
  return NextResponse.json({ message: 'Partially updated via PATCH' });
}

export async function DELETE(request: NextRequest) {
  return NextResponse.json({ message: 'Deleted' }, { status: 204 });
}
```

## Authentication Patterns

Use your authentication library (e.g., NextAuth/Auth.js, Clerk, Supabase) to verify sessions.

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { auth } from '<auth-module>'; // Example auth import

export async function GET(request: NextRequest) {
  const session = await auth();
  
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }
  
  return NextResponse.json({ data: 'Protected data' });
}
```

## Input Validation with Zod

Always validate incoming data structure and types using Zod.

```typescript
import { z } from 'zod';
import { NextRequest, NextResponse } from 'next/server';

const schema = z.object({
  id: z.string().uuid(),
  quantity: z.number().int().positive(),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const data = schema.parse(body);
    // Process valid data...
    return NextResponse.json({ success: true });
  } catch (error) {
     return NextResponse.json({ error: 'Invalid input' }, { status: 400 });
  }
}
```

## Dynamic Route Parameters

Route handlers can access dynamic segment parameters.

File: `app/api/items/[id]/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const id = params.id; // Access dynamic param
  return NextResponse.json({ id });
}
```

## Error Handling

Use standard HTTP status codes and consistent error response formats. Wrap logic in try/catch blocks.

- 200: OK
- 201: Created
- 400: Bad Request (Validation Error)
- 401: Unauthorized (Auth Error)
- 403: Forbidden (Permission Error)
- 404: Not Found
- 500: Internal Server Error
import { Suspense } from 'react'

// Async component (Server Component)
async function UserData({ userId }: { userId: string }) {
  // Simulate data fetching
  const response = await fetch(`/api/users/${userId}`)
  const user = await response.json()
  
  return (
    <div className="p-4 bg-blue-50 rounded">
      <h3 className="font-bold">{user.name}</h3>
      <p className="text-gray-600">{user.email}</p>
    </div>
  )
}

// Loading skeleton fallback
function UserSkeleton() {
  return (
    <div className="p-4 bg-gray-200 rounded animate-pulse">
      <div className="h-4 bg-gray-300 rounded mb-2 w-32"></div>
      <div className="h-3 bg-gray-300 rounded w-48"></div>
    </div>
  )
}

// Suspense boundary - React 19 pattern for handling async components
export function UserProfile({ userId }: { userId: string }) {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">User Profile</h2>
      
      {/* Wrap async component in Suspense with fallback UI */}
      <Suspense fallback={<UserSkeleton />}>
        <UserData userId={userId} />
      </Suspense>
    </div>
  )
}

// Multiple async components with Suspense
export function Dashboard({ userId }: { userId: string }) {
  return (
    <div className="grid gap-4">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      
      <Suspense fallback={<UserSkeleton />}>
        <UserData userId={userId} />
      </Suspense>
    </div>
  )
}

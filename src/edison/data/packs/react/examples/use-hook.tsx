'use client'

import { use } from 'react'

// React 19 use() hook example - unwraps promises in components
export function UserDetails({ userPromise }: { userPromise: Promise<{ id: string; name: string; email: string }> }) {
  // use() unwraps the promise - can be called directly in component
  const user = use(userPromise)
  
  return (
    <div className="p-4">
      <h2 className="text-xl font-bold">{user.name}</h2>
      <p className="text-gray-600">{user.email}</p>
    </div>
  )
}

'use client'

import { useState } from 'react'

type Status = 'all' | 'active' | 'archived'

export default function ItemFilters() {
  const [status, setStatus] = useState<Status>('all')
  const [query, setQuery] = useState('')

  return (
    <div>
      <h1>Client Component - Item Filters</h1>

      <label>
        Status
        <select value={status} onChange={(e) => setStatus(e.target.value as Status)}>
          <option value="all">All</option>
          <option value="active">Active</option>
          <option value="archived">Archived</option>
        </select>
      </label>

      <label>
        Search
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search items"
        />
      </label>

      <p>Selected: {status}</p>
      <p>Query: {query || '(empty)'}</p>
    </div>
  )
}

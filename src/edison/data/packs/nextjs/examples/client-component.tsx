'use client'

import { useState } from 'react';

export default function LeadFilters() {
  const [status, setStatus] = useState<'all' | 'new' | 'contacted' | 'qualified'>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setStatus(e.target.value as 'all' | 'new' | 'contacted' | 'qualified');
    console.log('Selected Status:', e.target.value); // For demonstration
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    console.log('Search Term:', e.target.value); // For demonstration
  };

  const handleClearSearch = () => {
    setSearchTerm('');
    console.log('Search Cleared'); // For demonstration
  };

  return (
    <div style={{ padding: '20px', border: '1px solid #eee', borderRadius: '8px' }}>
      <h1>Client Component - Lead Filters</h1>
      <div style={{ marginBottom: '15px' }}>
        <label htmlFor="status-filter" style={{ marginRight: '10px' }}>Filter by Status:</label>
        <select
          id="status-filter"
          value={status}
          onChange={handleStatusChange}
          style={{ padding: '8px', borderRadius: '4px' }}
        >
          <option value="all">All</option>
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="qualified">Qualified</option>
        </select>
      </div>

      <div style={{ marginBottom: '15px' }}>
        <label htmlFor="search-input" style={{ marginRight: '10px' }}>Search Leads:</label>
        <input
          id="search-input"
          type="text"
          value={searchTerm}
          onChange={handleSearchChange}
          placeholder="Enter lead name or email"
          style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
        />
        <button
          onClick={handleClearSearch}
          style={{ marginLeft: '10px', padding: '8px 15px', borderRadius: '4px', border: 'none', background: '#007bff', color: 'white', cursor: 'pointer' }}
        >
          Clear Search
        </button>
      </div>

      <p>Current Filter Status: <strong>{status}</strong></p>
      <p>Current Search Term: <strong>{searchTerm || 'None'}</strong></p>

      {/* In a real app, this would trigger a data fetch or filter a list */}
      <p style={{ fontStyle: 'italic', color: '#666' }}>
        (This component demonstrates client-side interactivity. Actual lead filtering logic would be implemented here or passed down from a parent component.)
      </p>
    </div>
  );
}

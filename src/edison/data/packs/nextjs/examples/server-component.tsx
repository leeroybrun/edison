interface Lead {
  id: string;
  name: string;
  email: string;
}

// Simulate a database call
async function getLeads(): Promise<Lead[]> {
  // In a real application, this would fetch data from a database
  // For this example, we return mock data after a delay
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve([
        { id: '1', name: 'Alice Smith', email: 'alice@example.com' },
        { id: '2', name: 'Bob Johnson', email: 'bob@example.com' },
        { id: '3', name: 'Charlie Brown', email: 'charlie@example.com' },
      ]);
    }, 500); // Simulate network delay
  });
}

function LeadCard({ lead }: { lead: Lead }) {
  return (
    <div style={{ border: '1px solid #ccc', padding: '10px', margin: '10px 0' }}>
      <h3>{lead.name}</h3>
      <p>{lead.email}</p>
    </div>
  );
}

// Server Component - no 'use client' needed
// This component fetches data directly on the server
export default async function LeadsPage() {
  const leads = await getLeads();

  return (
    <div>
      <h1>Server Component - Leads</h1>
      {leads.length === 0 ? (
        <p>No leads found.</p>
      ) : (
        leads.map((l) => <LeadCard key={l.id} lead={l} />)
      )}
    </div>
  );
}

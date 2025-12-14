interface Item {
  id: string
  name: string
}

async function getItems(): Promise<Item[]> {
  // Illustrative: in a real app, fetch from DB or service on the server.
  return [
    { id: '1', name: 'Alpha' },
    { id: '2', name: 'Beta' },
  ]
}

function ItemRow(props: { item: Item }) {
  return <li>{props.item.name}</li>
}

// Server Component - no 'use client' needed.
export default async function ItemsPage() {
  const items = await getItems()

  return (
    <div>
      <h1>Server Component - Items</h1>
      {items.length === 0 ? <p>No items found.</p> : <ul>{items.map((i) => <ItemRow key={i.id} item={i} />)}</ul>}
    </div>
  )
}

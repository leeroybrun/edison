export default async function ServerComponent() {
  const data = await Promise.resolve({ message: 'hello' });
  return <pre>{JSON.stringify(data, null, 2)}</pre>;
}


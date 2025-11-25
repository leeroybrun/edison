// Generic function with constraints and explicit return type
export function pickKeys<T extends object, K extends keyof T>(obj: T, keys: K[]): Pick<T, K> {
  const out = {} as Pick<T, K>;
  for (const k of keys) out[k] = obj[k];
  return out;
}

// Using satisfies to enforce shape without widening
const user = {
  id: 'u_1',
  name: 'Ada',
  role: 'admin'
} as const satisfies { id: string; name: string; role: 'admin' | 'user' };


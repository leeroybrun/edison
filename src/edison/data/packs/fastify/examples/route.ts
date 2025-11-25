import Fastify from 'fastify';
import { z } from 'zod';

const app = Fastify();

const params = z.object({ id: z.string().uuid() });

app.get('/api/items/:id', async (request, reply) => {
  const parsed = params.safeParse(request.params);
  if (!parsed.success) return reply.status(400).send({ error: 'Invalid ID' });
  return { id: parsed.data.id, ok: true };
});

export default app;


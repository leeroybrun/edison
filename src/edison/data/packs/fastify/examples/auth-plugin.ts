import type { FastifyInstance } from 'fastify';

export async function authPlugin(app: FastifyInstance) {
  app.addHook('onRequest', async (req, reply) => {
    const token = req.headers['authorization'];
    if (!token) return reply.status(401).send({ error: 'Unauthorized' });
  });
}


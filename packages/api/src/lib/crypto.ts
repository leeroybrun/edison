import { createCipheriv, createDecipheriv, randomBytes } from 'crypto';

import { getConfig } from './config';

const algorithm = 'aes-256-gcm';

function getKey(): Buffer {
  const { ENCRYPTION_KEY } = getConfig();
  return Buffer.from(ENCRYPTION_KEY, 'hex');
}

export async function encrypt(plaintext: string): Promise<string> {
  const key = getKey();
  const iv = randomBytes(12);
  const cipher = createCipheriv(algorithm, key, iv);
  const ciphertext = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const authTag = cipher.getAuthTag();
  return Buffer.concat([iv, ciphertext, authTag]).toString('base64');
}

export async function decrypt(ciphertextBase64: string): Promise<string> {
  const key = getKey();
  const buffer = Buffer.from(ciphertextBase64, 'base64');
  const iv = buffer.subarray(0, 12);
  const authTag = buffer.subarray(buffer.length - 16);
  const encrypted = buffer.subarray(12, buffer.length - 16);
  const decipher = createDecipheriv(algorithm, key, iv);
  decipher.setAuthTag(authTag);
  const decrypted = Buffer.concat([decipher.update(encrypted), decipher.final()]);
  return decrypted.toString('utf8');
}

import { applyPatch, parsePatch, type ParsedDiff } from 'diff';

export function applyUnifiedDiff(
  original: string,
  unifiedDiff: string,
  maxRatioDelta = 0.3,
): string {
  const patches: ParsedDiff[] = parsePatch(unifiedDiff);
  if (patches.length === 0 || patches.every((patch) => patch.hunks.length === 0)) {
    throw new Error('Unified diff payload was empty');
  }

  const result = patches.reduce((text, patch) => {
    const applied = applyPatch(text, patch);
    if (applied === false) {
      throw new Error('Failed to apply unified diff');
    }
    return applied;
  }, original);

  const delta = Math.abs(result.length - original.length);
  if (original.length > 0 && delta / original.length > maxRatioDelta) {
    throw new Error('Unified diff modifies too much of the original text');
  }

  return result;
}

declare module 'diff' {
  export interface Change {
    value: string;
    count?: number;
    added?: boolean;
    removed?: boolean;
  }

  export interface Hunk {
    oldStart: number;
    oldLines: number;
    newStart: number;
    newLines: number;
    lines: string[];
  }

  export interface ParsedDiff {
    oldFileName?: string;
    newFileName?: string;
    oldHeader?: string;
    newHeader?: string;
    hunks: Hunk[];
  }

  export function diffLines(
    oldStr: string,
    newStr: string,
    options?: { ignoreWhitespace?: boolean; newlineIsToken?: boolean },
  ): Change[];

  export function parsePatch(diffStr: string): ParsedDiff[];

  export function applyPatch(source: string, patch: ParsedDiff | string): string | false;
}

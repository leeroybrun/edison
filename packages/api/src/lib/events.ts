import { EventEmitter } from 'events';

export type PairwiseRankingEntry = {
  winRate: number;
  wins: number;
  losses: number;
  comparisons: number;
};

export type CoverageMatrixCell = {
  count: number;
  avgScore: number;
};

export type CoverageMatrix = Record<string, Record<string, CoverageMatrixCell>>;

export type SafetySummary = {
  totalOutputs: number;
  flaggedOutputs: number;
  piiFindings: number;
  toxicFindings: number;
  jailbreakFindings: number;
  sampleFindings: Array<{ outputId: string; tags: string[]; issues: string[] }>;
};

export type BudgetStatus = {
  totalCost: number;
  totalTokens: number;
  budgetLimitUsd?: number;
  tokenLimit?: number;
  percentBudgetUsed?: number;
  percentTokenUsed?: number;
};

export type IterationMetricsPayload = {
  compositeScores: Record<string, number>;
  confidenceIntervals: Record<string, { lower: number; upper: number }>;
  pairwiseRanking: Record<string, PairwiseRankingEntry>;
  facetAnalysis: Record<string, number>;
  coverageMatrix: CoverageMatrix;
  compositeScore: number;
  totalCost: number;
  totalTokens: number;
  safetySummary?: SafetySummary;
  budgetStatus?: BudgetStatus;
};

export type IterationEvent =
  | { iterationId: string; type: 'status'; payload: { status: string; reason?: string } }
  | {
      iterationId: string;
      type: 'run-progress';
      payload: { completedRuns: number; totalRuns: number; failedRuns: number };
    }
  | { iterationId: string; type: 'judging-complete'; payload: { totalOutputs: number } }
  | { iterationId: string; type: 'metrics'; payload: IterationMetricsPayload }
  | { iterationId: string; type: 'safety'; payload: SafetySummary }
  | { iterationId: string; type: 'refinement'; payload: { suggestionId: string | null } }
  | { iterationId: string; type: 'failure'; payload: { message: string } };

export type EdisonEvents = {
  'modelRun:completed': { iterationId: string };
  'modelRun:failed': { iterationId: string; error: string };
  'iteration:event': IterationEvent;
};

type EventKey = keyof EdisonEvents;

type Listener<K extends EventKey> = (payload: EdisonEvents[K]) => void;

class TypedEventEmitter {
  private emitter = new EventEmitter();

  on<K extends EventKey>(event: K, listener: Listener<K>): void {
    this.emitter.on(event, listener);
  }

  once<K extends EventKey>(event: K, listener: Listener<K>): void {
    this.emitter.once(event, listener);
  }

  off<K extends EventKey>(event: K, listener: Listener<K>): void {
    this.emitter.off(event, listener);
  }

  emit<K extends EventKey>(event: K, payload: EdisonEvents[K]): void {
    this.emitter.emit(event, payload);
  }
}

export const appEvents = new TypedEventEmitter();

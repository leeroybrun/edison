'use client';

interface CoverageHeatmapProps {
  matrix: Record<string, Record<string, { count: number; avgScore: number }>>;
}

const difficultyOrder = ['1', '2', '3', '4', '5', 'unknown'];

export function CoverageHeatmap({ matrix }: CoverageHeatmapProps) {
  const tags = Object.keys(matrix);
  if (tags.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-200 p-4 text-sm text-slate-500">
        No coverage data yet.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-3 py-2 text-left font-medium text-slate-600">Tag</th>
            {difficultyOrder.map((bucket) => (
              <th key={bucket} className="px-3 py-2 text-center font-medium text-slate-600">
                Difficulty {bucket}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white">
          {tags.map((tag) => (
            <tr key={tag}>
              <td className="whitespace-nowrap px-3 py-2 font-medium text-slate-700">{tag}</td>
              {difficultyOrder.map((bucket) => {
                const cell = matrix[tag]?.[bucket];
                const intensity = Math.min(1, (cell?.avgScore ?? 0) / 5);
                const background = cell
                  ? `rgba(13, 148, 136, ${0.15 + intensity * 0.5})`
                  : 'transparent';
                return (
                  <td key={bucket} className="px-3 py-2 text-center">
                    <div
                      className="mx-auto rounded-md px-2 py-1 text-xs font-medium text-slate-700"
                      style={{ backgroundColor: background }}
                    >
                      {cell ? `${cell.avgScore.toFixed(2)} (${cell.count})` : '—'}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

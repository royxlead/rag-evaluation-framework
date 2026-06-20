"use client";

interface HallucinationDetail {
  claim: string;
  grounded: boolean;
  factual: boolean;
  hallucination_type: string;
  reason?: string;
}

interface HallucinationHeatmapProps {
  claims: HallucinationDetail[];
}

export default function HallucinationHeatmap({ claims }: HallucinationHeatmapProps) {
  if (!claims || claims.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500 dark:text-slate-400 text-sm">
        No claims to display.
      </div>
    );
  }

  const supported = claims.filter((c) => c.grounded).length;
  const unsupported = claims.filter((c) => !c.grounded).length;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 text-sm">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-emerald-500" />
          Supported: {supported}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-red-500" />
          Unsupported: {unsupported}
        </span>
      </div>

      <div className="space-y-1">
        {claims.map((claim, i) => (
          <div
            key={i}
            className={`flex items-start gap-2 p-2 rounded text-xs ${
              claim.grounded
                ? "bg-emerald-50 dark:bg-emerald-900/20"
                : "bg-red-50 dark:bg-red-900/20"
            }`}
          >
            <span
              className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${
                claim.grounded ? "bg-emerald-500" : "bg-red-500"
              }`}
            />
            <div className="flex-1 min-w-0">
              <p className="text-slate-700 dark:text-slate-300 truncate">
                {claim.claim}
              </p>
              {!claim.grounded && claim.reason && (
                <p className="text-red-600 dark:text-red-400 mt-0.5">
                  {claim.reason}
                </p>
              )}
            </div>
            <span className={`flex-shrink-0 text-xs font-medium ${
              claim.grounded
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-red-600 dark:text-red-400"
            }`}>
              {claim.hallucination_type || (claim.grounded ? "supported" : "unsupported")}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

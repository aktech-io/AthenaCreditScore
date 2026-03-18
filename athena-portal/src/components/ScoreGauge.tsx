import { getScoreColor, getScoreLabel } from "@/lib/mock-data";

interface ScoreGaugeProps {
  score: number;
  maxScore?: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

export function ScoreGauge({ score, maxScore = 900, size = "md", showLabel = true }: ScoreGaugeProps) {
  const percentage = (score / maxScore) * 100;
  const rotation = (percentage / 100) * 270 - 135;

  const sizeClasses = {
    sm: "w-24 h-24",
    md: "w-40 h-40",
    lg: "w-56 h-56",
  };

  const fontClasses = {
    sm: "text-lg",
    md: "text-3xl",
    lg: "text-5xl",
  };

  const labelClasses = {
    sm: "text-[10px]",
    md: "text-xs",
    lg: "text-sm",
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <div className={`${sizeClasses[size]} relative`}>
        {/* Background arc */}
        <svg viewBox="0 0 200 200" className="w-full h-full -rotate-[135deg]">
          <circle
            cx="100"
            cy="100"
            r="85"
            fill="none"
            stroke="hsl(var(--muted))"
            strokeWidth="12"
            strokeDasharray={`${270 * (Math.PI * 170) / 360} ${(Math.PI * 170)}`}
            strokeLinecap="round"
          />
          <circle
            cx="100"
            cy="100"
            r="85"
            fill="none"
            stroke="currentColor"
            className={getScoreColor(score)}
            strokeWidth="12"
            strokeDasharray={`${(percentage / 100) * 270 * (Math.PI * 170) / 360} ${(Math.PI * 170)}`}
            strokeLinecap="round"
            style={{ transition: "stroke-dasharray 1s ease-out" }}
          />
        </svg>
        {/* Score text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`${fontClasses[size]} font-bold font-mono ${getScoreColor(score)}`}>
            {score}
          </span>
          {showLabel && (
            <span className={`${labelClasses[size]} text-muted-foreground font-medium uppercase tracking-wider`}>
              out of {maxScore}
            </span>
          )}
        </div>
      </div>
      {showLabel && (
        <span className={`text-sm font-semibold ${getScoreColor(score)}`}>
          {getScoreLabel(score)}
        </span>
      )}
    </div>
  );
}

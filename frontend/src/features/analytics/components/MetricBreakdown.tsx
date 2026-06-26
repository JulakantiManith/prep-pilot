import { TrendingUp, TrendingDown, Minus, BarChart3, Sparkles, MessageCircle } from "lucide-react";
import type { ScoreTrend } from "../services/analyticsService";

interface MetricBreakdownProps {
  overallScores: ScoreTrend[];
  confidenceScores: ScoreTrend[];
  communicationScores: ScoreTrend[];
}

interface MetricCardProps {
  label: string;
  scores: ScoreTrend[];
  color: string;
  icon: React.ReactNode;
  iconBgClass: string;
}

function computeLatestScore(scores: ScoreTrend[]): number | null {
  if (scores.length === 0) return null;
  const last = scores[scores.length - 1];
  return last ? last.averageScore : null;
}

function computeTrend(scores: ScoreTrend[]): "up" | "down" | "neutral" {
  if (scores.length < 2) return "neutral";
  const latest = scores[scores.length - 1];
  const previous = scores[scores.length - 2];
  if (!latest || !previous) return "neutral";
  const diff = latest.averageScore - previous.averageScore;
  if (diff > 2) return "up";
  if (diff < -2) return "down";
  return "neutral";
}

function computeAverage(scores: ScoreTrend[]): number | null {
  if (scores.length === 0) return null;
  const sum = scores.reduce((acc, s) => acc + s.averageScore, 0);
  return Math.round(sum / scores.length);
}

function getScoreBarColor(score: number): string {
  if (score >= 75) return "bg-green-500 dark:bg-green-400";
  if (score >= 50) return "bg-yellow-500 dark:bg-yellow-400";
  return "bg-red-500 dark:bg-red-400";
}

function MetricCard({ label, scores, color, icon, iconBgClass }: MetricCardProps) {
  const latest = computeLatestScore(scores);
  const trend = computeTrend(scores);
  const average = computeAverage(scores);

  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm transition-all duration-200 hover:shadow-md hover:-translate-y-0.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`flex h-7 w-7 items-center justify-center rounded-md ${iconBgClass}`}>
            {icon}
          </div>
          <h4 className="text-sm font-medium text-muted-foreground">{label}</h4>
        </div>
        {trend === "up" && <TrendingUp className="h-4 w-4 text-green-500" />}
        {trend === "down" && <TrendingDown className="h-4 w-4 text-red-500" />}
        {trend === "neutral" && <Minus className="h-4 w-4 text-muted-foreground" />}
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold" style={{ color }}>
          {latest !== null ? `${Math.round(latest)}%` : "—"}
        </span>
        {average !== null && (
          <span className="text-xs text-muted-foreground">
            avg {average}%
          </span>
        )}
      </div>
      {latest !== null && (
        <div className="mt-3">
          <div className="h-1.5 w-full rounded-full bg-muted">
            <div
              className={`h-1.5 rounded-full transition-all duration-500 ${getScoreBarColor(latest)}`}
              style={{ width: `${Math.min(latest, 100)}%` }}
            />
          </div>
        </div>
      )}
      <p className="mt-2 text-xs text-muted-foreground">
        {scores.length} data {scores.length === 1 ? "point" : "points"}
      </p>
    </div>
  );
}

export function MetricBreakdown({
  overallScores,
  confidenceScores,
  communicationScores,
}: MetricBreakdownProps) {
  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <h3 className="text-lg font-semibold">Score Breakdown</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Latest scores and trends for each category
      </p>
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <MetricCard
          label="Overall Score"
          scores={overallScores}
          color="#3b82f6"
          icon={<BarChart3 className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />}
          iconBgClass="bg-blue-100 dark:bg-blue-900/30"
        />
        <MetricCard
          label="Confidence"
          scores={confidenceScores}
          color="#10b981"
          icon={<Sparkles className="h-3.5 w-3.5 text-green-600 dark:text-green-400" />}
          iconBgClass="bg-green-100 dark:bg-green-900/30"
        />
        <MetricCard
          label="Communication"
          scores={communicationScores}
          color="#f59e0b"
          icon={<MessageCircle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />}
          iconBgClass="bg-amber-100 dark:bg-amber-900/30"
        />
      </div>
    </div>
  );
}

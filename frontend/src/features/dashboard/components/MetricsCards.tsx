import { Briefcase, Mic, Target, TrendingUp, MessageCircle } from "lucide-react";
import type { DashboardOverview } from "../services/dashboardService";

interface MetricsCardsProps {
  overview: DashboardOverview;
}

interface MetricCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  subtitle?: string;
  iconBgClass: string;
  iconColorClass: string;
}

function getScoreColorClass(value: string | number): string {
  if (typeof value === "number") return "";
  const numericMatch = value.match(/^(\d+)%$/);
  if (!numericMatch || !numericMatch[1]) return "";
  const score = parseInt(numericMatch[1], 10);
  if (score >= 75) return "text-green-600 dark:text-green-400";
  if (score >= 50) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
}

function MetricCard({ title, value, icon, subtitle, iconBgClass, iconColorClass }: MetricCardProps) {
  const scoreColor = getScoreColorClass(value);

  return (
    <div className="rounded-xl border border-border/50 bg-card p-6 shadow-sm transition-all duration-200 ease-out hover:shadow-md hover:-translate-y-0.5 hover:border-border">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${iconBgClass} shadow-[0_0_8px_0] shadow-current/20`}>
          <div className={iconColorClass}>{icon}</div>
        </div>
      </div>
      <div className="mt-2">
        <p className={`text-3xl font-extrabold ${scoreColor}`}>{value}</p>
        {subtitle && (
          <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
        )}
      </div>
    </div>
  );
}

export function MetricsCards({ overview }: MetricsCardsProps) {
  const totalSessions =
    overview.totalInterviewSessions + overview.totalPresentationSessions;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <MetricCard
        title="Total Sessions"
        value={totalSessions}
        icon={<Target className="h-4 w-4" />}
        iconBgClass="bg-purple-100 dark:bg-purple-900/30"
        iconColorClass="text-purple-600 dark:text-purple-400"
        subtitle={`${overview.totalInterviewSessions} interview · ${overview.totalPresentationSessions} presentation`}
      />
      <MetricCard
        title="Interview Sessions"
        value={overview.totalInterviewSessions}
        icon={<Briefcase className="h-4 w-4" />}
        iconBgClass="bg-blue-100 dark:bg-blue-900/30"
        iconColorClass="text-blue-600 dark:text-blue-400"
      />
      <MetricCard
        title="Average Score"
        value={
          overview.averageOverallScore !== null
            ? `${Math.round(overview.averageOverallScore)}%`
            : "—"
        }
        icon={<TrendingUp className="h-4 w-4" />}
        iconBgClass="bg-green-100 dark:bg-green-900/30"
        iconColorClass="text-green-600 dark:text-green-400"
      />
      <MetricCard
        title="Confidence"
        value={
          overview.latestConfidenceScore !== null
            ? `${overview.latestConfidenceScore}%`
            : "—"
        }
        icon={<Mic className="h-4 w-4" />}
        iconBgClass="bg-amber-100 dark:bg-amber-900/30"
        iconColorClass="text-amber-600 dark:text-amber-400"
        subtitle="Latest session"
      />
      <MetricCard
        title="Communication"
        value={
          overview.latestCommunicationScore !== null
            ? `${overview.latestCommunicationScore}%`
            : "—"
        }
        icon={<MessageCircle className="h-4 w-4" />}
        iconBgClass="bg-rose-100 dark:bg-rose-900/30"
        iconColorClass="text-rose-600 dark:text-rose-400"
        subtitle="Latest session"
      />
    </div>
  );
}

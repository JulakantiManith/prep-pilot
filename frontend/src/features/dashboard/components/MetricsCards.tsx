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
}

function MetricCard({ title, value, icon, subtitle }: MetricCardProps) {
  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        <div className="text-muted-foreground">{icon}</div>
      </div>
      <div className="mt-2">
        <p className="text-2xl font-bold">{value}</p>
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
        subtitle={`${overview.totalInterviewSessions} interview · ${overview.totalPresentationSessions} presentation`}
      />
      <MetricCard
        title="Interview Sessions"
        value={overview.totalInterviewSessions}
        icon={<Briefcase className="h-4 w-4" />}
      />
      <MetricCard
        title="Average Score"
        value={
          overview.averageOverallScore !== null
            ? `${Math.round(overview.averageOverallScore)}%`
            : "—"
        }
        icon={<TrendingUp className="h-4 w-4" />}
      />
      <MetricCard
        title="Confidence"
        value={
          overview.latestConfidenceScore !== null
            ? `${overview.latestConfidenceScore}%`
            : "—"
        }
        icon={<Mic className="h-4 w-4" />}
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
        subtitle="Latest session"
      />
    </div>
  );
}

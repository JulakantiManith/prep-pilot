import { Briefcase, Presentation } from "lucide-react";
import type { RecentSession } from "../services/dashboardService";

interface RecentSessionsProps {
  sessions: RecentSession[];
}

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatSessionType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function SessionIcon({ type }: { type: string }) {
  if (type === "presentation") {
    return (
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-900/30">
        <Presentation className="h-4 w-4 text-amber-600 dark:text-amber-400" />
      </div>
    );
  }
  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/30">
      <Briefcase className="h-4 w-4 text-blue-600 dark:text-blue-400" />
    </div>
  );
}

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) {
    return (
      <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
        —
      </span>
    );
  }

  let colorClasses: string;
  if (score >= 75) {
    colorClasses = "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
  } else if (score >= 50) {
    colorClasses = "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400";
  } else {
    colorClasses = "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
  }

  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${colorClasses}`}>
      {score}%
    </span>
  );
}

export function RecentSessions({ sessions }: RecentSessionsProps) {
  if (sessions.length === 0) {
    return (
      <div className="rounded-xl border border-border/50 bg-card p-6 shadow-sm transition-all duration-200 ease-out hover:shadow-md hover:-translate-y-0.5 hover:border-border">
        <h3 className="text-lg font-semibold">Recent Sessions</h3>
        <div className="mt-4 flex flex-col items-center justify-center rounded-md border border-dashed border-border/50 bg-card/50 py-8 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
            <Briefcase className="h-5 w-5 text-muted-foreground" />
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            No recent sessions. Start practicing to see your history here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border/50 bg-card p-6 shadow-sm transition-all duration-200 ease-out hover:shadow-md hover:-translate-y-0.5 hover:border-border">
      <h3 className="text-lg font-semibold">Recent Sessions</h3>
      <ul className="mt-4 space-y-3" role="list">
        {sessions.map((session, index) => (
          <li
            key={`${session.createdAt}-${index}`}
            className="flex items-center justify-between rounded-md border border-border/50 px-4 py-3 transition-all duration-200 hover:bg-accent/5 hover:shadow-sm"
          >
            <div className="flex items-center gap-3">
              <SessionIcon type={session.sessionType} />
              <div>
                <p className="text-sm font-medium">
                  {formatSessionType(session.sessionType)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatDate(session.createdAt)}
                </p>
              </div>
            </div>
            <ScoreBadge score={session.overallScore} />
          </li>
        ))}
      </ul>
    </div>
  );
}

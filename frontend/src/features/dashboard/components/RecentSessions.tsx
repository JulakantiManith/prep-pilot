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
    return <Presentation className="h-4 w-4 text-muted-foreground" />;
  }
  return <Briefcase className="h-4 w-4 text-muted-foreground" />;
}

export function RecentSessions({ sessions }: RecentSessionsProps) {
  if (sessions.length === 0) {
    return (
      <div className="rounded-lg border bg-card p-6 shadow-sm">
        <h3 className="text-lg font-semibold">Recent Sessions</h3>
        <div className="mt-4 flex h-32 items-center justify-center">
          <p className="text-sm text-muted-foreground">
            No recent sessions. Start practicing to see your history here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <h3 className="text-lg font-semibold">Recent Sessions</h3>
      <ul className="mt-4 space-y-3" role="list">
        {sessions.map((session, index) => (
          <li
            key={`${session.createdAt}-${index}`}
            className="flex items-center justify-between rounded-md border px-4 py-3"
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
            <div className="text-right">
              <p className="text-sm font-semibold">
                {session.overallScore !== null ? `${session.overallScore}%` : "—"}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

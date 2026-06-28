import { Briefcase, Presentation, Clock, Loader2, AlertCircle } from "lucide-react";
import { cn } from "@/shared/lib/utils";
import type { SessionListItem } from "../services/historyService";

interface SessionCardProps {
  session: SessionListItem;
  onClick: (sessionId: string) => void;
}

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

function formatSessionType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function SessionIcon({ type }: { type: string }) {
  if (type === "presentation") {
    return <Presentation className="h-5 w-5 text-blue-500" />;
  }
  return <Briefcase className="h-5 w-5 text-purple-500" />;
}

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-sm text-muted-foreground">—</span>;

  const colorClass =
    score >= 80
      ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
      : score >= 60
        ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
        : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";

  return (
    <span
      className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", colorClass)}
    >
      {score}%
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === "completed") return null;

  if (status === "processing") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
        <Loader2 className="h-3 w-3 animate-spin" />
        Processing
      </span>
    );
  }

  if (status === "failed") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800 dark:bg-red-900/30 dark:text-red-400">
        <AlertCircle className="h-3 w-3" />
        Failed
      </span>
    );
  }

  return null;
}

export function SessionCard({ session, onClick }: SessionCardProps) {
  const isClickable = session.status === "completed";

  return (
    <button
      onClick={() => isClickable && onClick(session.id)}
      disabled={!isClickable}
      className={cn(
        "w-full rounded-lg border border-border/50 bg-card px-4 py-3 text-left shadow-sm transition-all duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        isClickable
          ? "hover:bg-accent/5 cursor-pointer"
          : "opacity-80 cursor-default"
      )}
      aria-label={
        isClickable
          ? `View ${formatSessionType(session.sessionType)} session from ${formatDate(session.createdAt)}`
          : `${formatSessionType(session.sessionType)} session — ${session.status}`
      }
    >
      <div className="flex items-center justify-between">
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
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            <span>{formatDuration(session.durationSeconds)}</span>
          </div>
          {session.status === "completed" ? (
            <ScoreBadge score={session.overallScore} />
          ) : (
            <StatusBadge status={session.status} />
          )}
        </div>
      </div>
      {session.status === "processing" && (
        <p className="mt-2 text-xs text-blue-600 dark:text-blue-400">
          Results are being generated...
        </p>
      )}
      {session.status === "failed" && (
        <p className="mt-2 text-xs text-red-600 dark:text-red-400">
          Evaluation failed. Please try again.
        </p>
      )}
    </button>
  );
}

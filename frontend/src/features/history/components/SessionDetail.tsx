import {
  Briefcase,
  Presentation,
  Clock,
  Calendar,
  Target,
  MessageSquare,
  TrendingUp,
  Award,
  AlertTriangle,
  Lightbulb,
} from "lucide-react";
import { cn } from "@/shared/lib/utils";
import type { SessionDetail as SessionDetailType } from "../services/historyService";

interface PresentationScoresData {
  speaking_speed?: number;
  clarity?: number;
  structure?: number;
  communication?: number;
  engagement?: number;
}

interface SessionDetailProps {
  session: SessionDetailType;
}

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
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

function ScoreCard({
  label,
  score,
  icon: Icon,
}: {
  label: string;
  score: number | null;
  icon: React.ComponentType<{ className?: string }>;
}) {
  if (score === null) return null;

  const colorClass =
    score >= 80
      ? "text-green-600 dark:text-green-400"
      : score >= 60
        ? "text-yellow-600 dark:text-yellow-400"
        : "text-red-600 dark:text-red-400";

  return (
    <div className="flex flex-col items-center gap-1 rounded-lg border bg-card p-4">
      <Icon className="h-5 w-5 text-muted-foreground" />
      <span className={cn("text-2xl font-bold", colorClass)}>{score}%</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

export function SessionDetail({ session }: SessionDetailProps) {
  return (
    <div className="space-y-6">
      {/* Session Header */}
      <div className="rounded-lg border bg-card p-6 shadow-sm">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {session.sessionType === "presentation" ? (
              <Presentation className="h-6 w-6 text-blue-500" />
            ) : (
              <Briefcase className="h-6 w-6 text-purple-500" />
            )}
            <div>
              <h2 className="text-xl font-semibold">
                {formatSessionType(session.sessionType)} Session
              </h2>
              {session.interviewType && (
                <p className="text-sm text-muted-foreground capitalize">
                  {session.interviewType} interview
                </p>
              )}
            </div>
          </div>
          {session.status && (
            <span className="inline-flex items-center rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium capitalize">
              {session.status.replace("_", " ")}
            </span>
          )}
        </div>

        {/* Metadata */}
        <div className="mt-4 flex flex-wrap gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <Calendar className="h-4 w-4" />
            <span>{formatDate(session.createdAt)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Clock className="h-4 w-4" />
            <span>{formatDuration(session.durationSeconds)}</span>
          </div>
          {session.role && (
            <div className="flex items-center gap-1.5">
              <Target className="h-4 w-4" />
              <span>{session.role}</span>
            </div>
          )}
          {session.topic && (
            <div className="flex items-center gap-1.5">
              <MessageSquare className="h-4 w-4" />
              <span>{session.topic}</span>
            </div>
          )}
          {session.difficulty && (
            <span className="inline-flex items-center rounded-full bg-secondary px-2 py-0.5 text-xs capitalize">
              {session.difficulty}
            </span>
          )}
        </div>
      </div>

      {/* Scores */}
      {session.sessionType === "presentation" && session.feedback?.presentationScores ? (
        // Presentation-specific scores (5 categories)
        <div className="space-y-3">
          <h3 className="text-lg font-semibold">Category Scores</h3>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            <ScoreCard
              label="Speaking Speed"
              score={(session.feedback.presentationScores as PresentationScoresData).speaking_speed ?? null}
              icon={Clock}
            />
            <ScoreCard
              label="Clarity"
              score={(session.feedback.presentationScores as PresentationScoresData).clarity ?? null}
              icon={MessageSquare}
            />
            <ScoreCard
              label="Structure"
              score={(session.feedback.presentationScores as PresentationScoresData).structure ?? null}
              icon={Target}
            />
            <ScoreCard
              label="Communication"
              score={(session.feedback.presentationScores as PresentationScoresData).communication ?? null}
              icon={TrendingUp}
            />
            <ScoreCard
              label="Engagement"
              score={(session.feedback.presentationScores as PresentationScoresData).engagement ?? null}
              icon={Award}
            />
          </div>
          {session.overallScore !== null && (
            <p className="text-center text-sm text-muted-foreground">
              Overall: <span className="font-semibold text-foreground">{session.overallScore}%</span>
            </p>
          )}
        </div>
      ) : (
        // Interview scores (3 metrics)
        (session.overallScore !== null ||
          session.confidenceScore !== null ||
          session.communicationScore !== null) && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <ScoreCard label="Overall" score={session.overallScore} icon={Award} />
            <ScoreCard label="Confidence" score={session.confidenceScore} icon={TrendingUp} />
            <ScoreCard label="Communication" score={session.communicationScore} icon={MessageSquare} />
          </div>
        )
      )}

      {/* AI Feedback */}
      {session.feedback && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">AI Feedback</h3>
          <div className="grid gap-4 md:grid-cols-3">
            {session.feedback.strengths && session.feedback.strengths.length > 0 && (
              <div className="rounded-lg border bg-green-50 p-4 dark:bg-green-900/10">
                <div className="mb-2 flex items-center gap-2">
                  <Award className="h-4 w-4 text-green-600 dark:text-green-400" />
                  <h4 className="text-sm font-medium text-green-800 dark:text-green-300">
                    Strengths
                  </h4>
                </div>
                <ul className="space-y-1">
                  {session.feedback.strengths.map((item, idx) => (
                    <li key={idx} className="text-sm text-green-700 dark:text-green-400">
                      • {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {session.feedback.weaknesses && session.feedback.weaknesses.length > 0 && (
              <div className="rounded-lg border bg-yellow-50 p-4 dark:bg-yellow-900/10">
                <div className="mb-2 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                  <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
                    Areas to Improve
                  </h4>
                </div>
                <ul className="space-y-1">
                  {session.feedback.weaknesses.map((item, idx) => (
                    <li key={idx} className="text-sm text-yellow-700 dark:text-yellow-400">
                      • {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {session.feedback.recommendations && session.feedback.recommendations.length > 0 && (
              <div className="rounded-lg border bg-blue-50 p-4 dark:bg-blue-900/10">
                <div className="mb-2 flex items-center gap-2">
                  <Lightbulb className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  <h4 className="text-sm font-medium text-blue-800 dark:text-blue-300">
                    Recommendations
                  </h4>
                </div>
                <ul className="space-y-1">
                  {session.feedback.recommendations.map((item, idx) => (
                    <li key={idx} className="text-sm text-blue-700 dark:text-blue-400">
                      • {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Answers/Transcript */}
      {session.answers.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">
            Transcript ({session.answers.length} {session.answers.length === 1 ? "answer" : "answers"})
          </h3>
          <div className="space-y-3">
            {session.answers.map((answer) => (
              <div
                key={answer.questionIndex}
                className="rounded-lg border bg-card p-4 shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium">
                      Question {answer.questionIndex + 1}
                      {answer.questionText && `: ${answer.questionText}`}
                    </p>
                    {answer.transcript && (
                      <p className="mt-2 text-sm text-muted-foreground whitespace-pre-wrap">
                        {answer.transcript}
                      </p>
                    )}
                    {answer.transcript && answer.communicationScore === 0 && answer.totalWords !== null && answer.totalWords <= 2 && (
                      <p className="mt-1 text-xs text-yellow-600 dark:text-yellow-400 italic">
                        ⚠ No meaningful speech detected — this may be background noise or silence
                      </p>
                    )}
                    {!answer.transcript && (
                      <p className="mt-2 text-xs text-muted-foreground italic">
                        No response recorded
                      </p>
                    )}
                  </div>
                </div>

                {/* Answer metrics */}
                {(answer.communicationScore !== null ||
                  answer.confidenceScore !== null ||
                  answer.wpm !== null) && (
                  <div className="mt-3 flex flex-wrap gap-3 border-t pt-3">
                    {answer.communicationScore !== null && (
                      <span className="text-xs text-muted-foreground">
                        Communication: {answer.communicationScore}%
                      </span>
                    )}
                    {answer.confidenceScore !== null && (
                      <span className="text-xs text-muted-foreground">
                        Confidence: {answer.confidenceScore}%
                      </span>
                    )}
                    {answer.wpm !== null && (
                      <span className="text-xs text-muted-foreground">
                        {Math.round(answer.wpm)} WPM
                      </span>
                    )}
                    {answer.fillerWordCount !== null && answer.fillerWordCount > 0 && (
                      <span className="text-xs text-muted-foreground">
                        Filler words: {answer.fillerWordCount}
                      </span>
                    )}
                  </div>
                )}

                {/* AI Evaluation for this answer */}
                {answer.aiEvaluation && typeof answer.aiEvaluation === "object" && (
                  <div className="mt-3 border-t pt-3">
                    <p className="text-xs font-medium text-muted-foreground">AI Evaluation</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {(answer.aiEvaluation as { feedback?: string }).feedback || "—"}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

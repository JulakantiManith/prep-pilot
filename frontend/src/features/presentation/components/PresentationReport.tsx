import {
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  BarChart3,
} from "lucide-react";
import type { CompletePresentationResponse } from "../services/presentationService";

interface PresentationReportProps {
  report: CompletePresentationResponse;
}

interface ScoreBarProps {
  label: string;
  score: number;
}

function ScoreBar({ label, score }: ScoreBarProps) {
  const getColorClass = (value: number): string => {
    if (value >= 80) return "bg-green-500 dark:bg-green-400";
    if (value >= 60) return "bg-yellow-500 dark:bg-yellow-400";
    if (value >= 40) return "bg-orange-500 dark:bg-orange-400";
    return "bg-red-500 dark:bg-red-400";
  };

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">{label}</span>
        <span className="text-sm font-semibold text-foreground">
          {score}/100
        </span>
      </div>
      <div className="h-3 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className={`h-full rounded-full transition-all duration-500 ${getColorClass(score)}`}
          style={{ width: `${score}%` }}
          role="progressbar"
          aria-valuenow={score}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${label}: ${score} out of 100`}
        />
      </div>
    </div>
  );
}

export function PresentationReport({ report }: PresentationReportProps) {
  const { scores, feedback, session } = report;

  const overallScore = scores
    ? Math.round(
        (scores.speaking_speed +
          scores.clarity +
          scores.structure +
          scores.communication +
          scores.engagement) /
          5
      )
    : session.overall_score ?? 0;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="space-y-2">
        <h2 className="text-xl font-bold">Presentation Report</h2>
        {session.title && (
          <p className="text-muted-foreground">{session.title}</p>
        )}
      </div>

      {/* Overall Score */}
      <div className="rounded-lg border border-border p-6 text-center">
        <p className="text-sm font-medium text-muted-foreground">
          Overall Score
        </p>
        <p className="mt-1 text-4xl font-bold text-foreground">
          {overallScore}
          <span className="text-lg text-muted-foreground">/100</span>
        </p>
      </div>

      {/* Category Scores */}
      {scores && (
        <div className="rounded-lg border border-border p-6 space-y-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-primary" />
            <h3 className="text-lg font-semibold">Category Scores</h3>
          </div>
          <div className="space-y-3">
            <ScoreBar label="Speaking Speed" score={scores.speaking_speed} />
            <ScoreBar label="Clarity" score={scores.clarity} />
            <ScoreBar label="Structure" score={scores.structure} />
            <ScoreBar label="Communication" score={scores.communication} />
            <ScoreBar label="Engagement" score={scores.engagement} />
          </div>
        </div>
      )}

      {/* Feedback Sections */}
      {feedback && (
        <div className="space-y-4">
          {/* Strengths */}
          {feedback.strengths.length > 0 && (
            <div className="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-950">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                <h3 className="text-sm font-semibold text-green-900 dark:text-green-100">
                  Strengths
                </h3>
              </div>
              <ul className="space-y-1">
                {feedback.strengths.map((item, index) => (
                  <li
                    key={index}
                    className="text-sm text-green-800 dark:text-green-200"
                  >
                    • {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Weaknesses */}
          {feedback.weaknesses.length > 0 && (
            <div className="rounded-lg border border-orange-200 bg-orange-50 p-4 dark:border-orange-800 dark:bg-orange-950">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                <h3 className="text-sm font-semibold text-orange-900 dark:text-orange-100">
                  Areas for Improvement
                </h3>
              </div>
              <ul className="space-y-1">
                {feedback.weaknesses.map((item, index) => (
                  <li
                    key={index}
                    className="text-sm text-orange-800 dark:text-orange-200"
                  >
                    • {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommendations */}
          {feedback.recommendations.length > 0 && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
              <div className="flex items-center gap-2 mb-3">
                <Lightbulb className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100">
                  Recommendations
                </h3>
              </div>
              <ul className="space-y-1">
                {feedback.recommendations.map((item, index) => (
                  <li
                    key={index}
                    className="text-sm text-blue-800 dark:text-blue-200"
                  >
                    • {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* No feedback state */}
      {!scores && !feedback && (
        <div className="rounded-lg border border-border p-6 text-center">
          <p className="text-muted-foreground">
            No detailed analysis available for this session.
          </p>
        </div>
      )}
    </div>
  );
}

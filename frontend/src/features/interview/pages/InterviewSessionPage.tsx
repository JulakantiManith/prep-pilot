import { useEffect } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { AlertCircle, Info } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import { QuestionDisplay } from "../components/QuestionDisplay";
import { AudioRecorder } from "../components/AudioRecorder";
import { AnswerFeedback } from "../components/AnswerFeedback";
import { SessionReport } from "../components/SessionReport";
import { useInterview } from "../hooks/useInterview";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import type { SessionQuestion } from "../services/interviewService";

interface LocationState {
  session: { id: string };
  questions: SessionQuestion[];
  questionSource: string;
  fallbackUsed: boolean;
  isTechnical: boolean;
}

export function InterviewSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = location.state as LocationState | null;

  const interview = useInterview(
    locationState
      ? {
          sessionId: locationState.session.id,
          questions: locationState.questions,
          questionSource: locationState.questionSource,
          fallbackUsed: locationState.fallbackUsed,
          isTechnical: locationState.isTechnical,
        }
      : undefined,
    sessionId
  );
  const recorder = useAudioRecorder();

  const currentQuestion = interview.questions[interview.currentQuestionIndex];
  const lastAnswer = interview.answers[interview.answers.length - 1];
  const isLastQuestion =
    interview.currentQuestionIndex >= interview.questions.length - 1;

  // Check if current question was already answered (e.g., after refresh)
  const currentQuestionAnswer = interview.answers.find(
    (a) => a.questionIndex === interview.currentQuestionIndex
  );
  const isCurrentQuestionAnswered = !!currentQuestionAnswer;

  const handleSubmitAnswer = async () => {
    if (!recorder.audioBlob) return;
    await interview.submitAnswer(recorder.audioBlob);
    recorder.resetRecorder();
  };

  // Auto-submit when recording stops (no manual Submit step needed)
  const handleStopRecording = () => {
    recorder.stopRecording();
  };

  // If no session is active and we navigated directly, redirect to setup
  useEffect(() => {
    if (!sessionId) {
      navigate("/interview", { replace: true });
    }
  }, [sessionId, navigate]);

  // Trigger auto-submit when audioBlob becomes available after stopping
  useEffect(() => {
    if (
      recorder.status === "stopped" &&
      recorder.audioBlob &&
      !interview.isLoading &&
      !isCurrentQuestionAnswered &&
      interview.phase === "in_progress"
    ) {
      handleSubmitAnswer();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recorder.status, recorder.audioBlob]);

  // If we have a session ID in URL but no session state, show start-from-setup message
  if (!interview.sessionId && !interview.isLoading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="space-y-4 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-muted-foreground" />
          <h2 className="text-xl font-semibold">Session Not Found</h2>
          <p className="text-sm text-muted-foreground">
            This session may have expired or was not started from this browser.
          </p>
          <Button onClick={() => navigate("/interview", { replace: true })}>
            Start New Session
          </Button>
        </div>
      </div>
    );
  }

  const handleNextQuestion = () => {
    interview.nextQuestion();
  };

  const handleCompleteSession = async () => {
    await interview.completeSession();
  };

  const handleReset = () => {
    interview.resetSession();
    navigate("/interview", { replace: true });
  };

  // Loading state
  if (interview.isLoading && interview.phase === "setup") {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <LoadingSpinner label="Creating session..." />
      </div>
    );
  }

  // Error state
  if (interview.error && interview.phase !== "in_progress") {
    return (
      <ErrorMessage
        title="Session Error"
        message={interview.error}
        retry={() => interview.clearError()}
        className="mx-auto max-w-lg mt-8"
      />
    );
  }

  // Completed state - show report
  if (
    interview.phase === "completed" &&
    (interview.sessionReport || interview.technicalEvaluation)
  ) {
    return (
      <div className="mx-auto max-w-2xl py-6">
        <SessionReport
          sessionReport={interview.sessionReport}
          technicalEvaluation={interview.technicalEvaluation}
          isTechnical={interview.isTechnical}
          onReset={handleReset}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 py-6">
      {/* Fallback notification */}
      {interview.fallbackUsed && (
        <div
          className="flex items-start gap-2 rounded-md border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800"
          role="status"
        >
          <Info className="mt-0.5 h-4 w-4 shrink-0" />
          <p>
            Using pre-loaded questions. AI-generated questions were unavailable.
          </p>
        </div>
      )}

      {/* Error banner */}
      {interview.error && (
        <div
          className="flex items-start gap-2 rounded-md bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive"
          role="alert"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{interview.error}</p>
        </div>
      )}

      {/* In progress - show question and recorder */}
      {interview.phase === "in_progress" && currentQuestion && (
        <div className="space-y-6">
          <QuestionDisplay
            questionText={currentQuestion.text}
            questionIndex={interview.currentQuestionIndex}
            totalQuestions={interview.questions.length}
          />

          {/* If already answered, show answer info and skip button */}
          {isCurrentQuestionAnswered ? (
            <div className="space-y-4">
              <div className="rounded-md border border-green-200 bg-green-50 dark:bg-green-900/20 dark:border-green-800 p-4 text-sm text-green-800 dark:text-green-300">
                <p className="font-medium">Already answered</p>
                <p className="mt-1 text-green-700 dark:text-green-400">
                  {currentQuestionAnswer.response &&
                    ("transcript" in currentQuestionAnswer.response
                      ? currentQuestionAnswer.response.transcript
                      : "")}
                </p>
              </div>
              {isLastQuestion ? (
                <Button onClick={handleCompleteSession} className="w-full">
                  Complete Session
                </Button>
              ) : (
                <Button onClick={handleNextQuestion} className="w-full">
                  Next Question
                </Button>
              )}
            </div>
          ) : (
            <>
              <AudioRecorder
                status={recorder.status}
                duration={recorder.duration}
                error={recorder.error}
                onStart={recorder.startRecording}
                onStop={handleStopRecording}
                disabled={interview.isLoading}
              />

              {/* Show submitting state after recording stops */}
              {recorder.status === "stopped" && interview.isLoading && (
                <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                  <LoadingSpinner size="sm" label="" />
                  <span>Submitting your answer...</span>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Reviewing - show feedback */}
      {interview.phase === "reviewing" && lastAnswer && (
        <AnswerFeedback
          answerResult={lastAnswer}
          isTechnical={interview.isTechnical}
          isLastQuestion={isLastQuestion}
          onNext={handleNextQuestion}
          onComplete={handleCompleteSession}
        />
      )}

      {/* Completed but waiting for report */}
      {interview.phase === "completed" &&
        !interview.sessionReport &&
        !interview.technicalEvaluation && (
          <div className="space-y-4">
            {interview.isLoading ? (
              <div className="flex flex-col items-center justify-center space-y-4 py-12">
                <LoadingSpinner label="" />
                <div className="text-center space-y-2">
                  <p className="text-sm font-medium text-foreground">
                    Processing interview results...
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Analyzing answers, scoring relevance, and generating feedback
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center space-y-4">
                <h2 className="text-xl font-semibold">All Questions Answered!</h2>
                <p className="text-sm text-muted-foreground">
                  Complete the session to get your performance report.
                </p>
                <Button onClick={handleCompleteSession} className="w-full">
                  Get Session Report
                </Button>
              </div>
            )}
          </div>
        )}
    </div>
  );
}

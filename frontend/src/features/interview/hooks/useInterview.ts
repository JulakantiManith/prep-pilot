import { useState, useCallback, useEffect, useRef } from "react";
import {
  createInterviewSession,
  createTechnicalSession,
  submitInterviewAnswer,
  submitTechnicalAnswer,
  completeInterviewSession,
  getTechnicalEvaluation,
} from "../services/interviewService";
import type {
  CreateInterviewSessionRequest,
  CreateTechnicalSessionRequest,
  SessionQuestion,
  SubmitAnswerResponse,
  TechnicalAnswerResponse,
  CompleteSessionResponse,
  TechnicalEvaluationResponse,
} from "../services/interviewService";

export type InterviewPhase = "setup" | "in_progress" | "reviewing" | "completed";

export interface AnswerResult {
  questionIndex: number;
  questionText: string;
  response: SubmitAnswerResponse | TechnicalAnswerResponse;
}

interface InterviewState {
  sessionId: string | null;
  questions: SessionQuestion[];
  currentQuestionIndex: number;
  phase: InterviewPhase;
  answers: AnswerResult[];
  questionSource: string | null;
  fallbackUsed: boolean;
  isTechnical: boolean;
  isLoading: boolean;
  error: string | null;
  sessionReport: CompleteSessionResponse | null;
  technicalEvaluation: TechnicalEvaluationResponse | null;
}

export interface UseInterviewInitialData {
  sessionId: string;
  questions: SessionQuestion[];
  questionSource: string;
  fallbackUsed: boolean;
  isTechnical: boolean;
}

// --- SessionStorage persistence ---
const STORAGE_KEY = "interview_session_state";

interface PersistedState {
  sessionId: string;
  questions: SessionQuestion[];
  currentQuestionIndex: number;
  phase: InterviewPhase;
  answers: AnswerResult[];
  questionSource: string | null;
  fallbackUsed: boolean;
  isTechnical: boolean;
}

function saveToStorage(state: InterviewState): void {
  if (!state.sessionId) return;
  try {
    const persisted: PersistedState = {
      sessionId: state.sessionId,
      questions: state.questions,
      currentQuestionIndex: state.currentQuestionIndex,
      phase: state.phase,
      answers: state.answers,
      questionSource: state.questionSource,
      fallbackUsed: state.fallbackUsed,
      isTechnical: state.isTechnical,
    };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(persisted));
  } catch {
    // Ignore storage errors
  }
}

function loadFromStorage(sessionId: string): PersistedState | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedState;
    // Only restore if it matches the current session
    if (parsed.sessionId === sessionId) {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
}

function clearStorage(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore
  }
}

// --- State initialization ---

function buildInitialState(
  initialData?: UseInterviewInitialData,
  urlSessionId?: string
): InterviewState {
  // First, try to restore from sessionStorage (covers both refresh AND
  // back-navigation where location.state is still present)
  const effectiveSessionId = urlSessionId || initialData?.sessionId;
  if (effectiveSessionId) {
    const persisted = loadFromStorage(effectiveSessionId);
    if (persisted) {
      // We have saved state for this session — always resume from storage
      const resumeIndex = persisted.currentQuestionIndex;
      let resumePhase: InterviewPhase = persisted.phase;

      // If phase was "reviewing", keep it so user sees the feedback
      if (resumePhase === "reviewing") {
        const hasAnswer = persisted.answers.some(
          (a) => a.questionIndex === resumeIndex
        );
        if (!hasAnswer) {
          resumePhase = "in_progress";
        }
      }

      return {
        sessionId: persisted.sessionId,
        questions: persisted.questions,
        currentQuestionIndex: resumeIndex,
        phase: resumePhase,
        answers: persisted.answers,
        questionSource: persisted.questionSource,
        fallbackUsed: persisted.fallbackUsed,
        isTechnical: persisted.isTechnical,
        isLoading: false,
        error: null,
        sessionReport: null,
        technicalEvaluation: null,
      };
    }
  }

  // No saved state — use fresh initial data from navigation (new session)
  if (initialData) {
    const freshState: InterviewState = {
      sessionId: initialData.sessionId,
      questions: initialData.questions,
      currentQuestionIndex: 0,
      phase: "in_progress",
      answers: [],
      questionSource: initialData.questionSource,
      fallbackUsed: initialData.fallbackUsed,
      isTechnical: initialData.isTechnical,
      isLoading: false,
      error: null,
      sessionReport: null,
      technicalEvaluation: null,
    };
    // Persist immediately so refresh right away will restore this state
    saveToStorage(freshState);
    return freshState;
  }

  return {
    sessionId: null,
    questions: [],
    currentQuestionIndex: 0,
    phase: "setup",
    answers: [],
    questionSource: null,
    fallbackUsed: false,
    isTechnical: false,
    isLoading: false,
    error: null,
    sessionReport: null,
    technicalEvaluation: null,
  };
}

export function useInterview(
  initialData?: UseInterviewInitialData,
  urlSessionId?: string
) {
  const [state, setState] = useState<InterviewState>(() =>
    buildInitialState(initialData, urlSessionId)
  );
  const completingRef = useRef(false);

  // Persist state changes to sessionStorage
  useEffect(() => {
    if (state.sessionId && state.phase !== "setup") {
      saveToStorage(state);
    }
  }, [
    state.sessionId,
    state.currentQuestionIndex,
    state.phase,
    state.answers,
    state.questions,
    state.questionSource,
    state.fallbackUsed,
    state.isTechnical,
  ]);

  const startInterviewSession = useCallback(
    async (data: CreateInterviewSessionRequest) => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));
      try {
        const result = await createInterviewSession(data);
        setState((prev) => ({
          ...prev,
          sessionId: result.session.id,
          questions: result.questions,
          questionSource: result.question_source,
          fallbackUsed: result.fallback_used,
          isTechnical: false,
          phase: "in_progress",
          currentQuestionIndex: 0,
          answers: [],
          isLoading: false,
        }));
        return result.session.id;
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Failed to create session";
        setState((prev) => ({ ...prev, isLoading: false, error: message }));
        throw err;
      }
    },
    []
  );

  const startTechnicalSession = useCallback(
    async (data: CreateTechnicalSessionRequest) => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));
      try {
        const result = await createTechnicalSession(data);
        setState((prev) => ({
          ...prev,
          sessionId: result.session.id,
          questions: result.questions,
          questionSource: result.question_source,
          fallbackUsed: result.fallback_used,
          isTechnical: true,
          phase: "in_progress",
          currentQuestionIndex: 0,
          answers: [],
          isLoading: false,
        }));
        return result.session.id;
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Failed to create session";
        setState((prev) => ({ ...prev, isLoading: false, error: message }));
        throw err;
      }
    },
    []
  );

  const submitAnswer = useCallback(
    async (audioBlob: Blob) => {
      if (!state.sessionId) return;

      const currentQuestion = state.questions[state.currentQuestionIndex];
      if (!currentQuestion) return;

      setState((prev) => ({ ...prev, isLoading: true, error: null }));
      try {
        let response: SubmitAnswerResponse | TechnicalAnswerResponse;

        if (state.isTechnical) {
          response = await submitTechnicalAnswer(
            state.sessionId,
            audioBlob,
            state.currentQuestionIndex,
            currentQuestion.text
          );
        } else {
          response = await submitInterviewAnswer(
            state.sessionId,
            audioBlob,
            state.currentQuestionIndex,
            currentQuestion.text
          );
        }

        const answerResult: AnswerResult = {
          questionIndex: state.currentQuestionIndex,
          questionText: currentQuestion.text,
          response,
        };

        setState((prev) => ({
          ...prev,
          answers: [...prev.answers, answerResult],
          phase: "reviewing",
          isLoading: false,
        }));

        return answerResult;
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Failed to submit answer";
        setState((prev) => ({ ...prev, isLoading: false, error: message }));
        throw err;
      }
    },
    [state.sessionId, state.questions, state.currentQuestionIndex, state.isTechnical]
  );

  const nextQuestion = useCallback(() => {
    setState((prev) => {
      const nextIndex = prev.currentQuestionIndex + 1;
      if (nextIndex >= prev.questions.length) {
        return { ...prev, phase: "completed" };
      }
      return {
        ...prev,
        currentQuestionIndex: nextIndex,
        phase: "in_progress",
      };
    });
  }, []);

  const completeSession = useCallback(async () => {
    if (!state.sessionId) return;
    if (state.isLoading) return; // Prevent double-call
    if (completingRef.current) return; // Ref-based guard for same-tick calls
    completingRef.current = true;

    // Immediately transition to completed+loading so user sees the processing state
    setState((prev) => ({ ...prev, isLoading: true, error: null, phase: "completed" }));
    try {
      if (state.isTechnical) {
        const evaluation = await getTechnicalEvaluation(state.sessionId);
        setState((prev) => ({
          ...prev,
          technicalEvaluation: evaluation,
          phase: "completed",
          isLoading: false,
        }));
        clearStorage();
        return evaluation;
      } else {
        const report = await completeInterviewSession(state.sessionId);
        setState((prev) => ({
          ...prev,
          sessionReport: report,
          phase: "completed",
          isLoading: false,
        }));
        clearStorage();
        return report;
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to complete session";
      setState((prev) => ({ ...prev, isLoading: false, error: message }));
      completingRef.current = false;
      throw err;
    }
  }, [state.sessionId, state.isTechnical, state.isLoading]);

  const resetSession = useCallback(() => {
    clearStorage();
    setState(buildInitialState());
  }, []);

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  return {
    ...state,
    startInterviewSession,
    startTechnicalSession,
    submitAnswer,
    nextQuestion,
    completeSession,
    resetSession,
    clearError,
  };
}

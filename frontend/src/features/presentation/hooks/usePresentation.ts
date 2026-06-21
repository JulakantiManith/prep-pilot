import { useState, useCallback } from "react";
import {
  createPresentationSession,
  uploadRecording,
  uploadMaterials,
  completePresentationSession,
} from "../services/presentationService";
import type {
  CreatePresentationSessionRequest,
  PresentationSession,
  CompletePresentationResponse,
} from "../services/presentationService";

export type PresentationPhase = "setup" | "recording" | "processing" | "report";

interface PresentationState {
  phase: PresentationPhase;
  session: PresentationSession | null;
  report: CompletePresentationResponse | null;
  isLoading: boolean;
  error: string | null;
}

export function usePresentation() {
  const [state, setState] = useState<PresentationState>({
    phase: "setup",
    session: null,
    report: null,
    isLoading: false,
    error: null,
  });

  const createSession = useCallback(
    async (data: CreatePresentationSessionRequest) => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));
      try {
        const result = await createPresentationSession(data);
        setState((prev) => ({
          ...prev,
          session: result.session,
          phase: "recording",
          isLoading: false,
        }));
        return result.session;
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Failed to create session";
        setState((prev) => ({ ...prev, isLoading: false, error: message }));
        return null;
      }
    },
    []
  );

  const submitRecording = useCallback(
    async (sessionId: string, blob: Blob) => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));
      try {
        await uploadRecording(sessionId, blob);
        setState((prev) => ({ ...prev, isLoading: false }));
        return true;
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Failed to upload recording";
        setState((prev) => ({ ...prev, isLoading: false, error: message }));
        return false;
      }
    },
    []
  );

  const submitMaterials = useCallback(
    async (sessionId: string, file: File) => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));
      try {
        await uploadMaterials(sessionId, file);
        setState((prev) => ({ ...prev, isLoading: false }));
        return true;
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Failed to upload materials";
        setState((prev) => ({ ...prev, isLoading: false, error: message }));
        return false;
      }
    },
    []
  );

  const completeSession = useCallback(async (sessionId: string) => {
    setState((prev) => ({ ...prev, phase: "processing", isLoading: true, error: null }));
    try {
      const result = await completePresentationSession(sessionId);
      setState((prev) => ({
        ...prev,
        report: result,
        session: result.session,
        phase: "report",
        isLoading: false,
      }));
      return result;
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to complete session";
      setState((prev) => ({
        ...prev,
        phase: "recording",
        isLoading: false,
        error: message,
      }));
      return null;
    }
  }, []);

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  return {
    ...state,
    createSession,
    submitRecording,
    submitMaterials,
    completeSession,
    clearError,
  };
}

import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { PresentationRecorder } from "../components/PresentationRecorder";
import { PresentationReport } from "../components/PresentationReport";
import {
  uploadRecording,
  uploadMaterials,
  completePresentationSession,
} from "../services/presentationService";
import type { CompletePresentationResponse } from "../services/presentationService";

type SessionPhase = "recording" | "processing" | "report";

export function PresentationSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [phase, setPhase] = useState<SessionPhase>("recording");
  const [isUploading, setIsUploading] = useState(false);
  const [materialsUploaded, setMaterialsUploaded] = useState(false);
  const [recordingBlob, setRecordingBlob] = useState<Blob | null>(null);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [report, setReport] = useState<CompletePresentationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCompleting, setIsCompleting] = useState(false);

  const handleRecordingComplete = useCallback(
    (blob: Blob, duration: number) => {
      setRecordingBlob(blob);
      setRecordingDuration(duration);
    },
    []
  );

  const handleMaterialsSelected = useCallback(
    async (file: File) => {
      if (!sessionId) return;
      setIsUploading(true);
      setError(null);
      try {
        await uploadMaterials(sessionId, file);
        setMaterialsUploaded(true);
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Failed to upload materials";
        setError(message);
      } finally {
        setIsUploading(false);
      }
    },
    [sessionId]
  );

  const handleFinishSession = async () => {
    if (!sessionId || !recordingBlob) return;

    setIsCompleting(true);
    setError(null);

    try {
      // Upload recording first
      await uploadRecording(sessionId, recordingBlob);

      // Then complete session
      setPhase("processing");
      const result = await completePresentationSession(sessionId);
      setReport(result);
      setPhase("report");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to complete session";
      setError(message);
      setPhase("recording");
    } finally {
      setIsCompleting(false);
    }
  };

  if (!sessionId) {
    return (
      <div className="py-6 text-center">
        <p className="text-muted-foreground">Invalid session. Please start a new presentation.</p>
        <Button className="mt-4" onClick={() => navigate("/presentation")}>
          Go Back
        </Button>
      </div>
    );
  }

  if (phase === "processing") {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
          <div>
            <p className="text-lg font-medium">Analyzing your presentation...</p>
            <p className="text-sm text-muted-foreground">
              This may take a moment while we evaluate your speaking speed, clarity,
              structure, communication, and engagement.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (phase === "report" && report) {
    return (
      <div className="py-6 space-y-6">
        <PresentationReport report={report} />
        <div className="mx-auto max-w-3xl flex justify-center">
          <Button onClick={() => navigate("/presentation")}>
            Start New Session
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="py-6 space-y-6">
      {error && (
        <div
          className="mx-auto max-w-3xl rounded-md bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive"
          role="alert"
        >
          {error}
        </div>
      )}

      <PresentationRecorder
        sessionId={sessionId}
        onRecordingComplete={handleRecordingComplete}
        onMaterialsSelected={handleMaterialsSelected}
        isUploading={isUploading}
        materialsUploaded={materialsUploaded}
      />

      {/* Finish Session Button */}
      {recordingBlob && (
        <div className="mx-auto max-w-3xl flex flex-col items-center gap-2">
          <p className="text-sm text-muted-foreground">
            Recording duration: {Math.floor(recordingDuration / 60)}m{" "}
            {recordingDuration % 60}s
          </p>
          <Button
            onClick={handleFinishSession}
            disabled={isCompleting}
            size="lg"
          >
            {isCompleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Finish & Get Analysis
          </Button>
        </div>
      )}
    </div>
  );
}

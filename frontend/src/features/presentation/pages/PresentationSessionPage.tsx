import { useState, useCallback, useRef, useEffect } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import {
  Loader2,
  Upload,
  FileText,
  CheckCircle2,
  Video,
  PartyPopper,
} from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { PresentationRecorder } from "../components/PresentationRecorder";
import {
  uploadRecording,
  uploadMaterials,
  completePresentationSession,
} from "../services/presentationService";

const ACCEPTED_MATERIAL_TYPES = [
  "application/pdf",
  "application/vnd.ms-powerpoint",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
];
const ACCEPTED_EXTENSIONS = ".pdf,.ppt,.pptx";

type SessionPhase = "prepare" | "recording" | "submitting" | "submitted";

export function PresentationSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  // Get user-chosen duration from navigation state (default 5 min)
  const durationMinutes: number =
    (location.state as { durationMinutes?: number } | null)?.durationMinutes || 5;

  const [phase, setPhase] = useState<SessionPhase>("prepare");
  const [isUploading, setIsUploading] = useState(false);
  const [materialsUploaded, setMaterialsUploaded] = useState(false);
  const [materialsFile, setMaterialsFile] = useState<File | null>(null);
  const [materialsError, setMaterialsError] = useState<string | null>(null);
  const [recordingBlob, setRecordingBlob] = useState<Blob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCompleting, setIsCompleting] = useState(false);
  const autoFinishRef = useRef(false);

  const handleMaterialsChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      setMaterialsError(null);
      const file = e.target.files?.[0];
      if (!file || !sessionId) return;

      if (!ACCEPTED_MATERIAL_TYPES.includes(file.type)) {
        setMaterialsError("Invalid file type. Please upload a PDF or PowerPoint file.");
        return;
      }

      if (file.size > 50 * 1024 * 1024) {
        setMaterialsError("File is too large. Maximum size is 50MB.");
        return;
      }

      setMaterialsFile(file);
      setIsUploading(true);
      try {
        await uploadMaterials(sessionId, file);
        setMaterialsUploaded(true);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Failed to upload materials";
        setMaterialsError(message);
        setMaterialsFile(null);
      } finally {
        setIsUploading(false);
      }
    },
    [sessionId]
  );

  const handleStartPresentation = () => {
    setPhase("recording");
  };

  const handleRecordingComplete = useCallback(
    (blob: Blob, _duration: number) => {
      setRecordingBlob(blob);
    },
    []
  );

  // Auto-finish session when recording completes via timer expiry
  useEffect(() => {
    if (recordingBlob && autoFinishRef.current && !isCompleting && sessionId) {
      autoFinishRef.current = false;
      handleFinishSession();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordingBlob]);

  const handleTimerExpired = useCallback(() => {
    autoFinishRef.current = true;
  }, []);

  const handleFinishSession = async () => {
    if (!sessionId || !recordingBlob) return;

    setIsCompleting(true);
    setPhase("submitting");
    setError(null);

    try {
      // Upload recording
      await uploadRecording(sessionId, recordingBlob);

      // Submit for background processing (returns immediately)
      await completePresentationSession(sessionId);

      // Show success
      setPhase("submitted");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to submit presentation";
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

  // Phase: Prepare — upload materials, then start presentation
  if (phase === "prepare") {
    return (
      <div className="py-6">
        <div className="mx-auto max-w-2xl space-y-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Video className="h-6 w-6 text-primary" />
              <h1 className="text-2xl font-bold">Prepare Your Presentation</h1>
            </div>
            <p className="text-muted-foreground">
              Upload your slides (optional), then start presenting. You have{" "}
              <span className="font-semibold text-foreground">{durationMinutes} minute{durationMinutes !== 1 ? "s" : ""}</span> to present.
            </p>
          </div>

          {error && (
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive" role="alert">
              {error}
            </div>
          )}

          {/* Materials Upload Section */}
          <div className="rounded-lg border border-border p-6 space-y-4">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-muted-foreground" />
              <h3 className="text-base font-medium">Upload Presentation Slides (optional)</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              Upload your PPT, PPTX, or PDF slides. The AI will evaluate how well you follow your slides during the presentation.
            </p>

            {materialsError && (
              <p className="text-sm text-destructive" role="alert">{materialsError}</p>
            )}

            {materialsUploaded ? (
              <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                <CheckCircle2 className="h-5 w-5" />
                <span className="font-medium">Uploaded: {materialsFile?.name}</span>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <label
                  htmlFor="materials-upload-prepare"
                  className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
                >
                  <Upload className="h-4 w-4" />
                  {materialsFile ? materialsFile.name : "Choose file"}
                </label>
                <input
                  id="materials-upload-prepare"
                  type="file"
                  accept={ACCEPTED_EXTENSIONS}
                  onChange={handleMaterialsChange}
                  className="sr-only"
                  aria-label="Upload presentation materials"
                />
                {isUploading && (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                )}
              </div>
            )}
          </div>

          {/* Session Info */}
          <div className="rounded-md border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
            <h3 className="text-sm font-medium text-blue-900 dark:text-blue-100">
              Session details
            </h3>
            <ul className="mt-2 space-y-1 text-sm text-blue-700 dark:text-blue-300">
              <li>• Duration: <strong>{durationMinutes} minute{durationMinutes !== 1 ? "s" : ""}</strong></li>
              <li>• Camera and microphone will be activated</li>
              <li>• Timer will count down — session auto-saves when time is up</li>
              <li>• You can also stop early and submit manually</li>
            </ul>
          </div>

          {/* Start Presentation Button */}
          <Button
            onClick={handleStartPresentation}
            size="lg"
            className="w-full"
            disabled={isUploading}
          >
            <Video className="mr-2 h-4 w-4" />
            Start Presentation
          </Button>
        </div>
      </div>
    );
  }

  // Phase: Submitting
  if (phase === "submitting") {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
          <div>
            <p className="text-lg font-medium">Submitting your presentation...</p>
            <p className="text-sm text-muted-foreground">Uploading recording and starting analysis.</p>
          </div>
        </div>
      </div>
    );
  }

  // Phase: Submitted — success screen
  if (phase === "submitted") {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="mx-auto max-w-md text-center space-y-6">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
            <PartyPopper className="h-8 w-8 text-green-600 dark:text-green-400" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold">Presentation Submitted!</h2>
            <p className="text-muted-foreground">
              Your results are currently being generated. This usually takes 1-2 minutes.
            </p>
            <p className="text-sm text-muted-foreground">
              You can start another session or check the History page later to view the completed results.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
            <Button onClick={() => navigate("/presentation")}>
              New Presentation
            </Button>
            <Button variant="outline" onClick={() => navigate("/history")}>
              Go to History
            </Button>
            <Button variant="outline" onClick={() => navigate("/dashboard")}>
              Dashboard
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Phase: Recording
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
        durationSeconds={durationMinutes * 60}
        onRecordingComplete={handleRecordingComplete}
        onTimerExpired={handleTimerExpired}
        onMaterialsSelected={() => {}}
        isUploading={false}
        materialsUploaded={materialsUploaded}
      />

      {/* Finish Session Button */}
      {recordingBlob && (
        <div className="mx-auto max-w-3xl flex flex-col items-center gap-2">
          <Button
            onClick={handleFinishSession}
            disabled={isCompleting}
            size="lg"
          >
            {isCompleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Submit Presentation
          </Button>
        </div>
      )}
    </div>
  );
}

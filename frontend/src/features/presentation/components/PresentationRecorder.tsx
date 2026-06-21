import { useRef, useEffect } from "react";
import {
  Loader2,
  Video,
  Square,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { useVideoRecorder } from "../hooks/useVideoRecorder";

interface PresentationRecorderProps {
  sessionId: string;
  durationSeconds: number;
  onRecordingComplete: (blob: Blob, duration: number) => void;
  onTimerExpired: () => void;
  onMaterialsSelected: (file: File) => void;
  isUploading: boolean;
  materialsUploaded: boolean;
}

export function PresentationRecorder({
  sessionId: _sessionId,
  durationSeconds,
  onRecordingComplete,
  onTimerExpired,
  onMaterialsSelected: _onMaterialsSelected,
  isUploading: _isUploading,
  materialsUploaded: _materialsUploaded,
}: PresentationRecorderProps) {
  const videoPreviewRef = useRef<HTMLVideoElement>(null);

  const {
    status,
    videoBlob,
    error,
    duration,
    previewUrl,
    startRecording,
    stopRecording,
    getStream,
  } = useVideoRecorder();

  // Connect live stream to video element for preview
  useEffect(() => {
    if (status === "recording" && videoPreviewRef.current) {
      const stream = getStream();
      if (stream) {
        videoPreviewRef.current.srcObject = stream;
      }
    }
  }, [status, getStream]);

  // Notify parent when recording completes
  useEffect(() => {
    if (status === "stopped" && videoBlob) {
      onRecordingComplete(videoBlob, duration);
    }
  }, [status, videoBlob, duration, onRecordingComplete]);

  // Auto-stop recording when user-chosen duration expires
  useEffect(() => {
    if (status === "recording" && duration >= durationSeconds) {
      stopRecording();
      onTimerExpired();
    }
  }, [status, duration, durationSeconds, stopRecording, onTimerExpired]);

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="space-y-2">
        <h2 className="text-xl font-bold">Recording Session</h2>
        <p className="text-muted-foreground">
          Record your presentation. Your camera and microphone will be used.
        </p>
      </div>

      {/* Error display */}
      {error && (
        <div
          className="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive"
          role="alert"
        >
          {error}
        </div>
      )}

      {/* Video Preview Area */}
      <div className="relative overflow-hidden rounded-lg border border-border bg-black aspect-video">
        {status === "recording" && (
          <video
            ref={videoPreviewRef}
            autoPlay
            muted
            playsInline
            className="h-full w-full object-cover"
            aria-label="Live camera preview"
          />
        )}

        {status === "stopped" && previewUrl && (
          <video
            src={previewUrl}
            controls
            className="h-full w-full object-cover"
            aria-label="Recorded video playback"
          />
        )}

        {(status === "idle" || status === "requesting") && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-white/70">
              <Video className="mx-auto h-12 w-12 mb-2" />
              <p className="text-sm">
                {status === "requesting"
                  ? "Requesting camera access..."
                  : "Click Start Recording to begin"}
              </p>
              <p className="mt-2 text-lg font-bold text-white/90">
                {formatDuration(durationSeconds)}
              </p>
              <p className="text-xs text-white/50">session duration</p>
            </div>
          </div>
        )}

        {/* Recording indicator with countdown timer */}
        {status === "recording" && (
          <>
            {/* Timer showing elapsed / chosen duration */}
            <div className="absolute top-4 left-4 flex items-center gap-2 rounded-full bg-red-600/90 px-3 py-1">
              <div className="h-2 w-2 animate-pulse rounded-full bg-white" />
              <span className="text-xs font-medium text-white">
                {formatDuration(duration)} / {formatDuration(durationSeconds)}
              </span>
            </div>
            {/* Warning when under 1 minute left */}
            {durationSeconds - duration <= 60 && durationSeconds - duration > 0 && (
              <div className="absolute top-4 right-4 flex items-center gap-1.5 rounded-full bg-yellow-500/90 px-3 py-1">
                <span className="text-xs font-medium text-white">
                  ⚠ {formatDuration(durationSeconds - duration)} left
                </span>
              </div>
            )}
          </>
        )}
      </div>

      {/* Countdown progress bar — always visible during session */}
      {(status === "idle" || status === "recording" || status === "error") && (
        <div className="space-y-1">
          <div className="h-3 w-full overflow-hidden rounded-full bg-secondary">
            <div
              className={`h-full rounded-full transition-all duration-1000 ${
                status !== "recording"
                  ? "bg-green-500"
                  : (durationSeconds - duration) / durationSeconds <= 0.1
                    ? "bg-red-500"
                    : (durationSeconds - duration) / durationSeconds <= 0.5
                      ? "bg-yellow-500"
                      : "bg-green-500"
              }`}
              style={{
                width: status === "recording"
                  ? `${Math.max(0, ((durationSeconds - duration) / durationSeconds) * 100)}%`
                  : "100%",
              }}
              role="progressbar"
              aria-valuenow={status === "recording" ? durationSeconds - duration : durationSeconds}
              aria-valuemin={0}
              aria-valuemax={durationSeconds}
              aria-label={`Time remaining: ${formatDuration(status === "recording" ? durationSeconds - duration : durationSeconds)}`}
            />
          </div>
          <p className="text-center text-sm font-medium text-foreground">
            {status === "recording"
              ? `⏱ ${formatDuration(durationSeconds - duration)} remaining`
              : `⏱ ${formatDuration(durationSeconds)} session`}
          </p>
        </div>
      )}

      {/* Recording Controls */}
      <div className="flex flex-col items-center gap-2">
        <div className="flex items-center justify-center gap-4">
          {(status === "idle" || status === "error") && (
            <Button onClick={startRecording} size="lg">
              <Video className="mr-2 h-4 w-4" />
              Start Recording
            </Button>
          )}

          {status === "requesting" && (
            <Button disabled size="lg">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Requesting Access...
            </Button>
          )}

          {status === "recording" && (
            <Button onClick={stopRecording} variant="destructive" size="lg">
              <Square className="mr-2 h-4 w-4" />
              Stop Recording
            </Button>
          )}

          {status === "stopped" && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span>Recording complete — {formatDuration(duration)}</span>
            </div>
          )}
        </div>

        {/* Duration info */}
        {(status === "idle" || status === "error" || status === "recording") && (
          <p className="text-xs text-muted-foreground">
            Session duration: {Math.floor(durationSeconds / 60)} minute{Math.floor(durationSeconds / 60) !== 1 ? "s" : ""}
            {status === "recording" ? " — recording will auto-save when time is up" : ""}
          </p>
        )}
      </div>
    </div>
  );
}

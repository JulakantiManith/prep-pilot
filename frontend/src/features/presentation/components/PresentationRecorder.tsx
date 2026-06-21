import { useRef, useEffect, useState, useCallback } from "react";
import {
  Loader2,
  Video,
  Square,
  Upload,
  FileText,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { useVideoRecorder } from "../hooks/useVideoRecorder";

const ACCEPTED_MATERIAL_TYPES = [
  "application/pdf",
  "application/vnd.ms-powerpoint",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
];

const ACCEPTED_EXTENSIONS = ".pdf,.ppt,.pptx";

interface PresentationRecorderProps {
  sessionId: string;
  onRecordingComplete: (blob: Blob, duration: number) => void;
  onMaterialsSelected: (file: File) => void;
  isUploading: boolean;
  materialsUploaded: boolean;
}

export function PresentationRecorder({
  sessionId: _sessionId,
  onRecordingComplete,
  onMaterialsSelected,
  isUploading,
  materialsUploaded,
}: PresentationRecorderProps) {
  const videoPreviewRef = useRef<HTMLVideoElement>(null);
  const [materialsFile, setMaterialsFile] = useState<File | null>(null);
  const [materialsError, setMaterialsError] = useState<string | null>(null);

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

  const handleMaterialsChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setMaterialsError(null);
      const file = e.target.files?.[0];
      if (!file) return;

      if (!ACCEPTED_MATERIAL_TYPES.includes(file.type)) {
        setMaterialsError(
          "Invalid file type. Please upload a PDF or PowerPoint file."
        );
        return;
      }

      // 50MB limit for materials
      if (file.size > 50 * 1024 * 1024) {
        setMaterialsError("File is too large. Maximum size is 50MB.");
        return;
      }

      setMaterialsFile(file);
      onMaterialsSelected(file);
    },
    [onMaterialsSelected]
  );

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
            </div>
          </div>
        )}

        {/* Recording indicator */}
        {status === "recording" && (
          <div className="absolute top-4 left-4 flex items-center gap-2 rounded-full bg-red-600/90 px-3 py-1">
            <div className="h-2 w-2 animate-pulse rounded-full bg-white" />
            <span className="text-xs font-medium text-white">
              {formatDuration(duration)}
            </span>
          </div>
        )}
      </div>

      {/* Recording Controls */}
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

      {/* Materials Upload */}
      <div className="rounded-lg border border-border p-4 space-y-3">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-muted-foreground" />
          <h3 className="text-sm font-medium">
            Presentation Materials (optional)
          </h3>
        </div>
        <p className="text-xs text-muted-foreground">
          Upload your slides (PPT, PPTX, or PDF) to associate with this session.
        </p>

        {materialsError && (
          <p className="text-xs text-destructive" role="alert">
            {materialsError}
          </p>
        )}

        {materialsUploaded ? (
          <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
            <CheckCircle2 className="h-4 w-4" />
            <span>Materials uploaded: {materialsFile?.name}</span>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <label
              htmlFor="materials-upload"
              className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              <Upload className="h-4 w-4" />
              {materialsFile ? materialsFile.name : "Choose file"}
            </label>
            <input
              id="materials-upload"
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
    </div>
  );
}

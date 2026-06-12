import { useCallback, useRef, useState } from "react";
import { Upload, FileText, AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { cn } from "@/shared/lib/utils";
import { useUploadResume, useResumeMetadata } from "../hooks/useProfile";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const ACCEPTED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const ACCEPTED_EXTENSIONS = ".pdf,.docx";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ResumeUpload() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const uploadResume = useUploadResume();
  const { data: resumeMetadata, isLoading: isMetadataLoading } = useResumeMetadata();

  const validateFile = (file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return "Invalid file type. Please upload a PDF or DOCX file.";
    }
    if (file.size > MAX_FILE_SIZE) {
      return `File size exceeds 10 MB limit. Your file is ${formatFileSize(file.size)}.`;
    }
    return null;
  };

  const handleUpload = useCallback(
    async (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }

      setError(null);
      setSuccessMessage(null);
      setUploadProgress(0);

      try {
        await uploadResume.mutateAsync({
          file,
          onProgress: (percent) => setUploadProgress(percent),
        });
        setSuccessMessage("Resume uploaded successfully.");
        setTimeout(() => setSuccessMessage(null), 3000);
      } catch (err: unknown) {
        if (err && typeof err === "object" && "response" in err) {
          const axiosError = err as { response?: { data?: { detail?: string } } };
          setError(axiosError.response?.data?.detail ?? "Failed to upload resume.");
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to upload resume. Please try again.");
        }
      } finally {
        setUploadProgress(null);
      }
    },
    [uploadResume]
  );

  const onFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      handleUpload(file);
    }
    // Reset input so the same file can be re-selected
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const onDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) {
      handleUpload(file);
    }
  };

  const onDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  const isUploading = uploadProgress !== null;

  return (
    <div className="space-y-4">
      {error && (
        <div
          className="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive flex items-center gap-2"
          role="alert"
        >
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {successMessage && (
        <div
          className="rounded-md bg-green-50 border border-green-200 p-3 text-sm text-green-800 flex items-center gap-2 dark:bg-green-950/20 dark:border-green-900 dark:text-green-400"
          role="status"
        >
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          {successMessage}
        </div>
      )}

      {/* Drop zone */}
      <div
        className={cn(
          "border-2 border-dashed rounded-lg p-6 text-center transition-colors",
          isUploading
            ? "border-primary/50 bg-primary/5"
            : "border-input hover:border-primary/50 hover:bg-accent/50"
        )}
        onDrop={onDrop}
        onDragOver={onDragOver}
        role="region"
        aria-label="Resume upload area"
      >
        {isUploading ? (
          <div className="space-y-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
            <p className="text-sm text-muted-foreground">Uploading...</p>
            <div className="w-full max-w-xs mx-auto">
              <div className="h-2 bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                  role="progressbar"
                  aria-valuenow={uploadProgress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Upload progress"
                />
              </div>
              <p className="text-xs text-muted-foreground mt-1">{uploadProgress}%</p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <Upload className="h-8 w-8 text-muted-foreground mx-auto" />
            <div>
              <p className="text-sm font-medium text-foreground">
                Drop your resume here or click to browse
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                PDF or DOCX, max 10 MB
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
            >
              Choose File
            </Button>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS}
          onChange={onFileChange}
          className="hidden"
          aria-label="Upload resume file"
        />
      </div>

      {/* Current resume info */}
      {isMetadataLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading resume info...
        </div>
      )}

      {resumeMetadata && (
        <div className="rounded-md border border-input p-3 flex items-center gap-3">
          <FileText className="h-5 w-5 text-muted-foreground shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-foreground truncate">
              {resumeMetadata.fileName}
            </p>
            <p className="text-xs text-muted-foreground">
              {formatFileSize(resumeMetadata.fileSize)} &middot; Uploaded{" "}
              {new Date(resumeMetadata.uploadedAt).toLocaleDateString()}
            </p>
          </div>
          <span
            className={cn(
              "text-xs px-2 py-0.5 rounded-full",
              resumeMetadata.extractionStatus === "completed"
                ? "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-400"
                : resumeMetadata.extractionStatus === "failed"
                  ? "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-400"
                  : "bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-400"
            )}
          >
            {resumeMetadata.extractionStatus}
          </span>
        </div>
      )}
    </div>
  );
}

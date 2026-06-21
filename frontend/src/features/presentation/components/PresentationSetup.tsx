import { useState } from "react";
import { Loader2, Video } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { cn } from "@/shared/lib/utils";

interface PresentationSetupData {
  title?: string;
  topic?: string;
  duration_estimate_minutes?: number;
}

interface PresentationSetupProps {
  onStart: (data: PresentationSetupData) => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

export function PresentationSetup({
  onStart,
  isLoading,
  error,
}: PresentationSetupProps) {
  const [title, setTitle] = useState("");
  const [topic, setTopic] = useState("");
  const [duration, setDuration] = useState<string>("5");
  const [durationError, setDurationError] = useState<string | null>(null);

  const validateDuration = (value: string): boolean => {
    if (!value) {
      setDurationError(null);
      return true;
    }
    const num = Number(value);
    if (isNaN(num) || num < 1 || num > 20) {
      setDurationError("Duration must be between 1 and 20 minutes.");
      return false;
    }
    setDurationError(null);
    return true;
  };

  const handleDurationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setDuration(value);
    validateDuration(value);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateDuration(duration)) return;

    const data: PresentationSetupData = {};
    if (title.trim()) data.title = title.trim();
    if (topic.trim()) data.topic = topic.trim();
    if (duration && Number(duration) > 0) {
      data.duration_estimate_minutes = Number(duration);
    } else {
      data.duration_estimate_minutes = 5; // Default
    }

    await onStart(data);
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Video className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">Presentation Practice</h1>
        </div>
        <p className="text-muted-foreground">
          Practice your presentation skills with live video recording and receive
          AI-powered feedback on speaking speed, clarity, structure,
          communication, and engagement.
        </p>
      </div>

      {error && (
        <div
          className="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive"
          role="alert"
        >
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {/* Title */}
        <div className="space-y-2">
          <label
            htmlFor="presentation-title"
            className="text-sm font-medium text-foreground"
          >
            Title (optional)
          </label>
          <input
            id="presentation-title"
            type="text"
            placeholder="e.g. Q4 Product Update"
            maxLength={200}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
        </div>

        {/* Topic */}
        <div className="space-y-2">
          <label
            htmlFor="presentation-topic"
            className="text-sm font-medium text-foreground"
          >
            Topic (optional)
          </label>
          <input
            id="presentation-topic"
            type="text"
            placeholder="e.g. Machine Learning Basics"
            maxLength={200}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
        </div>

        {/* Duration Estimate */}
        <div className="space-y-2">
          <label
            htmlFor="presentation-duration"
            className="text-sm font-medium text-foreground"
          >
            Estimated Duration (minutes)
          </label>
          <input
            id="presentation-duration"
            type="number"
            min={1}
            max={20}
            placeholder="5"
            value={duration}
            onChange={handleDurationChange}
            className={cn(
              "flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              durationError
                ? "border-destructive"
                : "border-input"
            )}
            aria-invalid={!!durationError}
            aria-describedby="duration-hint"
          />
          {durationError ? (
            <p className="text-xs text-destructive" role="alert">
              {durationError}
            </p>
          ) : (
            <p id="duration-hint" className="text-xs text-muted-foreground">
              Between 1 and 20 minutes (default: 5)
            </p>
          )}
        </div>

        {/* Info Box */}
        <div className="rounded-md border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
          <h3 className="text-sm font-medium text-blue-900 dark:text-blue-100">
            What to expect
          </h3>
          <ul className="mt-2 space-y-1 text-sm text-blue-700 dark:text-blue-300">
            <li>• Your camera and microphone will be activated for recording</li>
            <li>• You can optionally upload presentation materials (PPT/PDF)</li>
            <li>• After recording, you will receive scores on 5 categories</li>
            <li>• AI will provide personalized improvement suggestions</li>
          </ul>
        </div>

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Start Recording
        </Button>
      </form>
    </div>
  );
}

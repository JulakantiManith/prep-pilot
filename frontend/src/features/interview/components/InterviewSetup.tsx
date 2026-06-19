import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { cn } from "@/shared/lib/utils";
import {
  interviewSetupSchema,
  technicalSetupSchema,
  TECHNICAL_TOPICS,
} from "../schemas/interviewSchemas";
import type {
  InterviewSetupFormData,
  TechnicalSetupFormData,
} from "../schemas/interviewSchemas";

type SessionMode = "interview" | "technical" | "resume_based";

interface InterviewSetupProps {
  onStartInterview: (data: InterviewSetupFormData) => Promise<void>;
  onStartTechnical: (data: TechnicalSetupFormData) => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

export function InterviewSetup({
  onStartInterview,
  onStartTechnical,
  isLoading,
  error,
}: InterviewSetupProps) {
  const [mode, setMode] = useState<SessionMode>("interview");
  const navigate = useNavigate();

  const interviewForm = useForm<InterviewSetupFormData>({
    resolver: zodResolver(interviewSetupSchema),
    defaultValues: {
      interviewType: "hr",
      role: "",
      numQuestions: 5,
    },
  });

  const technicalForm = useForm<TechnicalSetupFormData>({
    resolver: zodResolver(technicalSetupSchema),
    defaultValues: {
      topic: "Data Structures",
      difficulty: "intermediate",
      role: "",
      numQuestions: 5,
    },
  });

  const handleInterviewSubmit = async (data: InterviewSetupFormData) => {
    await onStartInterview(data);
  };

  const handleTechnicalSubmit = async (data: TechnicalSetupFormData) => {
    await onStartTechnical(data);
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold">Start Interview Practice</h1>
        <p className="text-muted-foreground">
          Configure your practice session and get AI-generated questions.
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

      {/* Mode Selector */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">Session Mode</label>
        <div className="flex gap-2" role="radiogroup" aria-label="Session mode">
          <button
            type="button"
            role="radio"
            aria-checked={mode === "interview"}
            onClick={() => setMode("interview")}
            className={cn(
              "flex-1 rounded-md border px-4 py-2 text-sm font-medium transition-colors",
              mode === "interview"
                ? "border-primary bg-primary text-primary-foreground"
                : "border-input bg-background hover:bg-accent hover:text-accent-foreground"
            )}
          >
            Interview
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={mode === "technical"}
            onClick={() => setMode("technical")}
            className={cn(
              "flex-1 rounded-md border px-4 py-2 text-sm font-medium transition-colors",
              mode === "technical"
                ? "border-primary bg-primary text-primary-foreground"
                : "border-input bg-background hover:bg-accent hover:text-accent-foreground"
            )}
          >
            Technical
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={mode === "resume_based"}
            onClick={() => {
              setMode("resume_based");
              navigate("/interview/resume");
            }}
            className={cn(
              "flex-1 rounded-md border px-4 py-2 text-sm font-medium transition-colors",
              mode === "resume_based"
                ? "border-primary bg-primary text-primary-foreground"
                : "border-input bg-background hover:bg-accent hover:text-accent-foreground"
            )}
          >
            Resume-Based
          </button>
        </div>
      </div>

      {mode === "interview" ? (
        <form
          onSubmit={interviewForm.handleSubmit(handleInterviewSubmit)}
          className="space-y-4"
          noValidate
        >
          {/* Interview Type */}
          <div className="space-y-2">
            <label htmlFor="interviewType" className="text-sm font-medium text-foreground">
              Interview Type
            </label>
            <select
              id="interviewType"
              className={cn(
                "flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                interviewForm.formState.errors.interviewType
                  ? "border-destructive"
                  : "border-input"
              )}
              aria-invalid={interviewForm.formState.errors.interviewType ? "true" : undefined}
              aria-describedby={
                interviewForm.formState.errors.interviewType ? "interviewType-error" : undefined
              }
              {...interviewForm.register("interviewType")}
            >
              <option value="hr">HR / General</option>
              <option value="behavioral">Behavioral</option>
              <option value="technical">Technical</option>
              <option value="custom">Custom</option>
            </select>
            {interviewForm.formState.errors.interviewType && (
              <p id="interviewType-error" className="text-xs text-destructive">
                {interviewForm.formState.errors.interviewType.message}
              </p>
            )}
          </div>

          {/* Role */}
          <div className="space-y-2">
            <label htmlFor="interview-role" className="text-sm font-medium text-foreground">
              Target Role
            </label>
            <input
              id="interview-role"
              type="text"
              placeholder="e.g. Frontend Developer"
              className={cn(
                "flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                interviewForm.formState.errors.role ? "border-destructive" : "border-input"
              )}
              aria-invalid={interviewForm.formState.errors.role ? "true" : undefined}
              aria-describedby={interviewForm.formState.errors.role ? "interview-role-error" : undefined}
              {...interviewForm.register("role")}
            />
            {interviewForm.formState.errors.role && (
              <p id="interview-role-error" className="text-xs text-destructive">
                {interviewForm.formState.errors.role.message}
              </p>
            )}
          </div>

          {/* Topic (optional) */}
          <div className="space-y-2">
            <label htmlFor="interview-topic" className="text-sm font-medium text-foreground">
              Topic (optional)
            </label>
            <input
              id="interview-topic"
              type="text"
              placeholder="e.g. System Design, APIs"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              {...interviewForm.register("topic")}
            />
          </div>

          {/* Difficulty */}
          <div className="space-y-2">
            <label htmlFor="interview-difficulty" className="text-sm font-medium text-foreground">
              Difficulty
            </label>
            <select
              id="interview-difficulty"
              className={cn(
                "flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                interviewForm.formState.errors.difficulty
                  ? "border-destructive"
                  : "border-input"
              )}
              aria-invalid={interviewForm.formState.errors.difficulty ? "true" : undefined}
              aria-describedby={
                interviewForm.formState.errors.difficulty ? "interview-difficulty-error" : undefined
              }
              {...interviewForm.register("difficulty")}
            >
              <option value="">Select difficulty...</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
            {interviewForm.formState.errors.difficulty && (
              <p id="interview-difficulty-error" className="text-xs text-destructive">
                {interviewForm.formState.errors.difficulty.message}
              </p>
            )}
          </div>

          {/* Number of Questions */}
          <div className="space-y-2">
            <label htmlFor="interview-numQuestions" className="text-sm font-medium text-foreground">
              Number of Questions ({interviewForm.watch("numQuestions")})
            </label>
            <input
              id="interview-numQuestions"
              type="range"
              min={1}
              max={20}
              className="w-full"
              aria-valuemin={1}
              aria-valuemax={20}
              aria-valuenow={interviewForm.watch("numQuestions")}
              {...interviewForm.register("numQuestions", { valueAsNumber: true })}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>1</span>
              <span>20</span>
            </div>
            {interviewForm.formState.errors.numQuestions && (
              <p className="text-xs text-destructive">
                {interviewForm.formState.errors.numQuestions.message}
              </p>
            )}
          </div>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Start Interview
          </Button>
        </form>
      ) : (
        <form
          onSubmit={technicalForm.handleSubmit(handleTechnicalSubmit)}
          className="space-y-4"
          noValidate
        >
          {/* Technical Topic */}
          <div className="space-y-2">
            <label htmlFor="technical-topic" className="text-sm font-medium text-foreground">
              Technical Topic
            </label>
            <select
              id="technical-topic"
              className={cn(
                "flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                technicalForm.formState.errors.topic ? "border-destructive" : "border-input"
              )}
              aria-invalid={technicalForm.formState.errors.topic ? "true" : undefined}
              aria-describedby={technicalForm.formState.errors.topic ? "technical-topic-error" : undefined}
              {...technicalForm.register("topic")}
            >
              {TECHNICAL_TOPICS.map((topic) => (
                <option key={topic} value={topic}>
                  {topic}
                </option>
              ))}
            </select>
            {technicalForm.formState.errors.topic && (
              <p id="technical-topic-error" className="text-xs text-destructive">
                {technicalForm.formState.errors.topic.message}
              </p>
            )}
          </div>

          {/* Difficulty */}
          <div className="space-y-2">
            <label htmlFor="technical-difficulty" className="text-sm font-medium text-foreground">
              Difficulty
            </label>
            <select
              id="technical-difficulty"
              className={cn(
                "flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                technicalForm.formState.errors.difficulty ? "border-destructive" : "border-input"
              )}
              aria-invalid={technicalForm.formState.errors.difficulty ? "true" : undefined}
              aria-describedby={
                technicalForm.formState.errors.difficulty ? "technical-difficulty-error" : undefined
              }
              {...technicalForm.register("difficulty")}
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
            {technicalForm.formState.errors.difficulty && (
              <p id="technical-difficulty-error" className="text-xs text-destructive">
                {technicalForm.formState.errors.difficulty.message}
              </p>
            )}
          </div>

          {/* Role */}
          <div className="space-y-2">
            <label htmlFor="technical-role" className="text-sm font-medium text-foreground">
              Target Role
            </label>
            <input
              id="technical-role"
              type="text"
              placeholder="e.g. Backend Engineer"
              className={cn(
                "flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                technicalForm.formState.errors.role ? "border-destructive" : "border-input"
              )}
              aria-invalid={technicalForm.formState.errors.role ? "true" : undefined}
              aria-describedby={technicalForm.formState.errors.role ? "technical-role-error" : undefined}
              {...technicalForm.register("role")}
            />
            {technicalForm.formState.errors.role && (
              <p id="technical-role-error" className="text-xs text-destructive">
                {technicalForm.formState.errors.role.message}
              </p>
            )}
          </div>

          {/* Number of Questions */}
          <div className="space-y-2">
            <label htmlFor="technical-numQuestions" className="text-sm font-medium text-foreground">
              Number of Questions ({technicalForm.watch("numQuestions")})
            </label>
            <input
              id="technical-numQuestions"
              type="range"
              min={1}
              max={20}
              className="w-full"
              aria-valuemin={1}
              aria-valuemax={20}
              aria-valuenow={technicalForm.watch("numQuestions")}
              {...technicalForm.register("numQuestions", { valueAsNumber: true })}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>1</span>
              <span>20</span>
            </div>
            {technicalForm.formState.errors.numQuestions && (
              <p className="text-xs text-destructive">
                {technicalForm.formState.errors.numQuestions.message}
              </p>
            )}
          </div>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Start Technical Session
          </Button>
        </form>
      )}
    </div>
  );
}

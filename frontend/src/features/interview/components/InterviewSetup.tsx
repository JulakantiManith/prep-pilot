import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Loader2,
  Users,
  Code2,
  FileText,
  Brain,
  MessageCircle,
  Sparkles,
} from "lucide-react";
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

const SESSION_MODES = [
  {
    id: "interview" as SessionMode,
    label: "Interview",
    description: "HR, Behavioral & Custom",
    icon: MessageCircle,
    gradient: "from-blue-500/10 to-indigo-500/10 dark:from-blue-500/20 dark:to-indigo-500/20",
    borderActive: "border-blue-500 dark:border-blue-400",
    iconColor: "text-blue-600 dark:text-blue-400",
  },
  {
    id: "technical" as SessionMode,
    label: "Technical",
    description: "CS Topics & Coding",
    icon: Code2,
    gradient: "from-emerald-500/10 to-teal-500/10 dark:from-emerald-500/20 dark:to-teal-500/20",
    borderActive: "border-emerald-500 dark:border-emerald-400",
    iconColor: "text-emerald-600 dark:text-emerald-400",
  },
  {
    id: "resume_based" as SessionMode,
    label: "Resume-Based",
    description: "Personalized Questions",
    icon: FileText,
    gradient: "from-purple-500/10 to-pink-500/10 dark:from-purple-500/20 dark:to-pink-500/20",
    borderActive: "border-purple-500 dark:border-purple-400",
    iconColor: "text-purple-600 dark:text-purple-400",
  },
];

const INTERVIEW_TYPES = [
  { value: "hr", label: "HR / General", icon: Users, color: "blue" },
  { value: "behavioral", label: "Behavioral", icon: Brain, color: "amber" },
  { value: "technical", label: "Technical", icon: Code2, color: "emerald" },
  { value: "custom", label: "Custom", icon: Sparkles, color: "purple" },
];

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

  const handleModeChange = (newMode: SessionMode) => {
    setMode(newMode);
    if (newMode === "resume_based") {
      navigate("/interview/resume");
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="space-y-2 text-center">
        <h1 className="text-3xl font-bold tracking-tight">Start Interview Practice</h1>
        <p className="text-muted-foreground">
          Configure your practice session and get AI-generated questions.
        </p>
      </div>

      {error && (
        <div
          className="rounded-lg bg-destructive/10 border border-destructive/20 p-4 text-sm text-destructive animate-in fade-in slide-in-from-top-2 duration-300"
          role="alert"
        >
          {error}
        </div>
      )}

      {/* Mode Selector - Card Style */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-foreground">Session Mode</label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3" role="radiogroup" aria-label="Session mode">
          {SESSION_MODES.map((modeOption) => {
            const Icon = modeOption.icon;
            const isSelected = mode === modeOption.id;
            return (
              <button
                key={modeOption.id}
                type="button"
                role="radio"
                aria-checked={isSelected}
                onClick={() => handleModeChange(modeOption.id)}
                className={cn(
                  "relative flex flex-col items-center gap-2 rounded-xl border-2 p-4 text-center transition-all duration-200",
                  "hover:shadow-md hover:-translate-y-0.5",
                  isSelected
                    ? cn("bg-gradient-to-br shadow-sm", modeOption.gradient, modeOption.borderActive)
                    : "border-input bg-background hover:border-muted-foreground/30"
                )}
              >
                <div className={cn(
                  "rounded-lg p-2 transition-colors duration-200",
                  isSelected ? modeOption.iconColor : "text-muted-foreground"
                )}>
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <p className={cn(
                    "text-sm font-semibold transition-colors duration-200",
                    isSelected ? "text-foreground" : "text-foreground"
                  )}>
                    {modeOption.label}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {modeOption.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {mode === "interview" ? (
        <form
          onSubmit={interviewForm.handleSubmit(handleInterviewSubmit)}
          className="space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-300"
          noValidate
        >
          {/* Interview Type - Card Grid */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-foreground">
              Interview Type
            </label>
            <div className="grid grid-cols-2 gap-2">
              {INTERVIEW_TYPES.map((type) => {
                const Icon = type.icon;
                const isSelected = interviewForm.watch("interviewType") === type.value;
                const colorClasses: Record<string, { bg: string; border: string; icon: string }> = {
                  blue: {
                    bg: "from-blue-500/10 to-blue-600/5 dark:from-blue-500/20 dark:to-blue-600/10",
                    border: "border-blue-500 dark:border-blue-400",
                    icon: "text-blue-600 dark:text-blue-400",
                  },
                  amber: {
                    bg: "from-amber-500/10 to-amber-600/5 dark:from-amber-500/20 dark:to-amber-600/10",
                    border: "border-amber-500 dark:border-amber-400",
                    icon: "text-amber-600 dark:text-amber-400",
                  },
                  emerald: {
                    bg: "from-emerald-500/10 to-emerald-600/5 dark:from-emerald-500/20 dark:to-emerald-600/10",
                    border: "border-emerald-500 dark:border-emerald-400",
                    icon: "text-emerald-600 dark:text-emerald-400",
                  },
                  purple: {
                    bg: "from-purple-500/10 to-purple-600/5 dark:from-purple-500/20 dark:to-purple-600/10",
                    border: "border-purple-500 dark:border-purple-400",
                    icon: "text-purple-600 dark:text-purple-400",
                  },
                };
                const colors = colorClasses[type.color] ?? {
                  bg: "from-blue-500/10 to-blue-600/5 dark:from-blue-500/20 dark:to-blue-600/10",
                  border: "border-blue-500 dark:border-blue-400",
                  icon: "text-blue-600 dark:text-blue-400",
                };
                return (
                  <button
                    key={type.value}
                    type="button"
                    onClick={() => interviewForm.setValue("interviewType", type.value as InterviewSetupFormData["interviewType"])}
                    className={cn(
                      "flex items-center gap-3 rounded-lg border-2 p-3 text-left transition-all duration-200",
                      "hover:shadow-sm hover:-translate-y-0.5",
                      isSelected
                        ? cn("bg-gradient-to-br shadow-sm", colors.bg, colors.border)
                        : "border-input bg-background hover:border-muted-foreground/30"
                    )}
                  >
                    <Icon className={cn("h-4 w-4 shrink-0", isSelected ? colors.icon : "text-muted-foreground")} />
                    <span className="text-sm font-medium">{type.label}</span>
                  </button>
                );
              })}
            </div>
            {interviewForm.formState.errors.interviewType && (
              <p className="text-xs text-destructive">
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
                "flex h-10 w-full rounded-lg border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-colors duration-200",
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
              className="flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-colors duration-200"
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
                "flex h-10 w-full rounded-lg border bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-colors duration-200",
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
              className="w-full accent-primary"
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

          <Button type="submit" className="w-full h-11 text-base font-medium" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Start Interview
          </Button>
        </form>
      ) : (
        <form
          onSubmit={technicalForm.handleSubmit(handleTechnicalSubmit)}
          className="space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-300"
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
                "flex h-10 w-full rounded-lg border bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-colors duration-200",
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
                "flex h-10 w-full rounded-lg border bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-colors duration-200",
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
                "flex h-10 w-full rounded-lg border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-colors duration-200",
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
              className="w-full accent-primary"
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

          <Button type="submit" className="w-full h-11 text-base font-medium" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Start Technical Session
          </Button>
        </form>
      )}
    </div>
  );
}

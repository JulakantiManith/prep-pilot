import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, FileWarning, CheckCircle2, ArrowLeft } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { cn } from "@/shared/lib/utils";
import { ResumeDataForm } from "./ResumeDataForm";
import {
  parseResume,
  getExtractedData,
  editExtractedData,
  confirmExtractedData,
} from "../services/resumeInterviewService";
import { createInterviewSession } from "../services/interviewService";
import type { ExtractedResumeData } from "../services/resumeInterviewService";

type FlowStep = "setup" | "loading" | "parsing" | "editing" | "confirming" | "generating" | "error";

interface ResumeInterviewFlowProps {
  resumeId: string;
  resumeFileName: string;
}

export function ResumeInterviewFlow({ resumeId, resumeFileName }: ResumeInterviewFlowProps) {
  const navigate = useNavigate();
  const [step, setStep] = useState<FlowStep>("setup");
  const [extractedData, setExtractedData] = useState<ExtractedResumeData | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isAlreadyConfirmed, setIsAlreadyConfirmed] = useState(false);

  // Setup form state
  const [interviewType, setInterviewType] = useState<string>("hr");
  const [role, setRole] = useState<string>("");
  const [difficulty, setDifficulty] = useState<string>("");
  const [numQuestions, setNumQuestions] = useState<number>(5);

  const loadExtractedData = useCallback(async () => {
    try {
      setStep("loading");
      const response = await getExtractedData(resumeId);

      if (response.extraction_status === "completed" && response.extracted_data) {
        setExtractedData(response.extracted_data);
        setConfidence(response.extraction_confidence);
        setIsAlreadyConfirmed(response.user_confirmed);
        // Pre-fill role from resume experience if user hasn't set one
        if (!role && response.extracted_data.experience?.length > 0) {
          setRole(response.extracted_data.experience[0].title || "");
        }
        setStep("editing");
      } else if (response.extraction_status === "failed") {
        setError("Resume extraction failed. Please try re-uploading a properly formatted resume (PDF or DOCX).");
        setStep("error");
      } else if (response.extraction_status === "processing") {
        await triggerParsing();
      } else {
        await triggerParsing();
      }
    } catch {
      await triggerParsing();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resumeId]);

  const triggerParsing = async () => {
    try {
      setStep("parsing");
      const result = await parseResume(resumeId);

      if (result.extraction_status === "completed" && result.extracted_data) {
        setExtractedData(result.extracted_data);
        setConfidence(result.extraction_confidence);
        if (!role && result.extracted_data.experience?.length > 0) {
          setRole(result.extracted_data.experience[0].title || "");
        }
        setStep("editing");
      } else {
        setError(
          result.message ||
          "Failed to extract data from resume. Please try re-uploading a properly formatted resume (PDF or DOCX)."
        );
        setStep("error");
      }
    } catch {
      setError("An error occurred while parsing the resume. Please try again.");
      setStep("error");
    }
  };

  const handleNext = () => {
    if (!role.trim()) {
      setError("Please enter a target role.");
      return;
    }
    setError(null);
    loadExtractedData();
  };

  const handleSaveEdits = async () => {
    if (!extractedData || isAlreadyConfirmed) return;
    setIsSaving(true);
    try {
      const response = await editExtractedData(resumeId, extractedData);
      if (response.extracted_data) {
        setExtractedData(response.extracted_data);
      }
    } catch {
      setError("Failed to save edits. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleConfirm = async () => {
    if (!extractedData) return;

    setIsSaving(true);

    // Only save edits if the resume hasn't been confirmed yet
    if (!isAlreadyConfirmed) {
      try {
        await editExtractedData(resumeId, extractedData);
      } catch {
        setError("Failed to save edits before confirmation.");
        setIsSaving(false);
        return;
      }

      setStep("confirming");
      try {
        await confirmExtractedData(resumeId);
      } catch {
        setError("Failed to confirm resume data. Please try again.");
        setStep("editing");
        setIsSaving(false);
        return;
      }
    }

    // Start the session
    setStep("generating");
    await startSession();
    setIsSaving(false);
  };

  const startSession = async () => {
    try {
      setStep("generating");
      const result = await createInterviewSession({
        interview_type: "resume_based",
        role: role || extractedData?.experience?.[0]?.title || "Software Developer",
        topic: interviewType,
        difficulty: difficulty || undefined,
        num_questions: numQuestions,
      });
      navigate(`/interview/session/${result.session.id}`, {
        state: {
          session: result.session,
          questions: result.questions,
          questionSource: result.question_source,
          fallbackUsed: result.fallback_used,
          isTechnical: false,
        },
      });
    } catch {
      setError("Failed to generate interview questions. Please try again.");
      setStep("editing");
    }
  };

  // Don't auto-load on mount — wait for user to click Next
  useEffect(() => {
    // No auto-loading; user starts at "setup" step
  }, []);

  // ===================== STEP: SETUP =====================
  if (step === "setup") {
    return (
      <div className="space-y-4">
        {error && (
          <div
            className="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive"
            role="alert"
          >
            {error}
          </div>
        )}

        {/* Interview Type */}
        <div className="space-y-2">
          <label htmlFor="resume-interview-type" className="text-sm font-medium text-foreground">
            Interview Type
          </label>
          <select
            id="resume-interview-type"
            value={interviewType}
            onChange={(e) => setInterviewType(e.target.value)}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <option value="hr">HR / General</option>
            <option value="behavioral">Behavioral</option>
            <option value="technical">Technical</option>
          </select>
        </div>

        {/* Target Role */}
        <div className="space-y-2">
          <label htmlFor="resume-role" className="text-sm font-medium text-foreground">
            Target Role
          </label>
          <input
            id="resume-role"
            type="text"
            placeholder="e.g. Frontend Developer"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
        </div>

        {/* Difficulty */}
        <div className="space-y-2">
          <label htmlFor="resume-difficulty" className="text-sm font-medium text-foreground">
            Difficulty (optional)
          </label>
          <select
            id="resume-difficulty"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <option value="">Any</option>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>

        {/* Number of Questions */}
        <div className="space-y-2">
          <label htmlFor="resume-num-questions" className="text-sm font-medium text-foreground">
            Number of Questions ({numQuestions})
          </label>
          <input
            id="resume-num-questions"
            type="range"
            min={1}
            max={20}
            value={numQuestions}
            onChange={(e) => setNumQuestions(Number(e.target.value))}
            className="w-full"
            aria-valuemin={1}
            aria-valuemax={20}
            aria-valuenow={numQuestions}
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>1</span>
            <span>20</span>
          </div>
        </div>

        <div className="flex items-center gap-3 border-t pt-4">
          <Button variant="outline" onClick={() => navigate("/interview")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <Button onClick={handleNext}>
            Next — Review Resume Data
          </Button>
        </div>
      </div>
    );
  }

  // ===================== STEP: LOADING / PARSING =====================
  if (step === "loading" || step === "parsing") {
    return (
      <div className="flex flex-col items-center justify-center space-y-4 py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">
          {step === "loading" ? "Loading resume data..." : "Extracting data from your resume..."}
        </p>
        <p className="text-xs text-muted-foreground">
          This may take up to 60 seconds
        </p>
      </div>
    );
  }

  // ===================== STEP: ERROR =====================
  if (step === "error") {
    return (
      <div className="space-y-4 py-6">
        <div className="flex flex-col items-center space-y-3 rounded-md border border-destructive/20 bg-destructive/5 p-6">
          <FileWarning className="h-10 w-10 text-destructive" />
          <p className="text-center text-sm text-destructive">{error}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate("/profile")}>
            Go to Profile to Re-upload
          </Button>
          <Button variant="outline" onClick={() => navigate("/interview")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Interview Setup
          </Button>
        </div>
      </div>
    );
  }

  // ===================== STEP: CONFIRMING / GENERATING =====================
  if (step === "confirming" || step === "generating") {
    return (
      <div className="flex flex-col items-center justify-center space-y-4 py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">
          {step === "confirming"
            ? "Confirming your resume data..."
            : "Generating personalized interview questions..."}
        </p>
      </div>
    );
  }

  // ===================== STEP: EDITING (resume data review) =====================
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-green-500" />
          <h2 className="text-lg font-semibold">Resume Data Extracted</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          From: <span className="font-medium">{resumeFileName}</span>
        </p>
        <p className="text-sm text-muted-foreground">
          Review and edit the extracted data below. Once you confirm, personalized
          interview questions will be generated based on your resume.
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

      {extractedData && (
        <ResumeDataForm
          data={extractedData}
          confidence={confidence}
          onChange={setExtractedData}
        />
      )}

      <div className="flex items-center gap-3 border-t pt-4">
        <Button variant="outline" onClick={() => setStep("setup")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        {!isAlreadyConfirmed && (
          <Button variant="secondary" onClick={handleSaveEdits} disabled={isSaving}>
            {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Edits
          </Button>
        )}
        <Button onClick={handleConfirm} disabled={isSaving}>
          {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isAlreadyConfirmed ? "Start Interview" : "Confirm & Generate Questions"}
        </Button>
      </div>
    </div>
  );
}

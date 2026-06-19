import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, FileX } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { ResumeInterviewFlow } from "../components/ResumeInterviewFlow";
import { getResumeMetadata } from "@/features/profile/services/profileService";

export function ResumeInterviewPage() {
  const navigate = useNavigate();
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [resumeFileName, setResumeFileName] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [noResume, setNoResume] = useState(false);

  useEffect(() => {
    async function loadResume() {
      try {
        const metadata = await getResumeMetadata();
        if (metadata) {
          setResumeId(metadata.id);
          setResumeFileName(metadata.fileName);
        } else {
          setNoResume(true);
        }
      } catch {
        setNoResume(true);
      } finally {
        setIsLoading(false);
      }
    }
    loadResume();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (noResume) {
    return (
      <div className="mx-auto max-w-2xl py-6">
        <div className="flex flex-col items-center space-y-4 rounded-md border border-input p-8">
          <FileX className="h-12 w-12 text-muted-foreground" />
          <h2 className="text-lg font-semibold">No Resume Found</h2>
          <p className="text-center text-sm text-muted-foreground">
            You need to upload a resume before starting a resume-based interview.
            Go to your profile to upload a resume (PDF or DOCX).
          </p>
          <div className="flex gap-3">
            <Button onClick={() => navigate("/profile")}>
              Upload Resume
            </Button>
            <Button variant="outline" onClick={() => navigate("/interview")}>
              Back to Interview Setup
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl py-6">
      <div className="space-y-2 mb-6">
        <h1 className="text-2xl font-bold">Resume-Based Interview</h1>
        <p className="text-muted-foreground">
          Practice with personalized questions based on your resume.
        </p>
      </div>

      {resumeId && (
        <ResumeInterviewFlow
          resumeId={resumeId}
          resumeFileName={resumeFileName}
        />
      )}
    </div>
  );
}

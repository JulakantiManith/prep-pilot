import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PresentationSetup } from "../components/PresentationSetup";
import { createPresentationSession } from "../services/presentationService";
import type { CreatePresentationSessionRequest } from "../services/presentationService";

export function PresentationSetupPage() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStart = async (data: CreatePresentationSessionRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await createPresentationSession(data);
      navigate(`/presentation/session/${result.session.id}`, {
        state: { durationMinutes: data.duration_estimate_minutes || 5 },
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to create presentation session";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="py-6">
      <PresentationSetup
        onStart={handleStart}
        isLoading={isLoading}
        error={error}
      />
    </div>
  );
}

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, CheckCircle2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { cn } from "@/shared/lib/utils";
import { useProfile, useUpdateProfile } from "../hooks/useProfile";

const EXPERIENCE_LEVELS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
  { value: "senior", label: "Senior" },
  { value: "lead", label: "Lead" },
] as const;

const profileSchema = z.object({
  targetRole: z.string().max(200, "Target role must be at most 200 characters").optional(),
  experienceLevel: z
    .enum(["", "beginner", "intermediate", "advanced", "senior", "lead"])
    .optional(),
  skills: z.string().optional(),
});

type ProfileFormData = z.infer<typeof profileSchema>;

export function ProfileForm() {
  const { data: profile, isLoading: isProfileLoading } = useProfile();
  const updateProfile = useUpdateProfile();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      targetRole: "",
      experienceLevel: "",
      skills: "",
    },
  });

  // Pre-populate form when profile data loads
  useEffect(() => {
    if (profile) {
      reset({
        targetRole: profile.targetRole ?? "",
        experienceLevel: (profile.experienceLevel as ProfileFormData["experienceLevel"]) ?? "",
        skills: profile.skills.join(", "),
      });
    }
  }, [profile, reset]);

  const onSubmit = async (data: ProfileFormData) => {
    setFormError(null);
    setSuccessMessage(null);

    try {
      const skills = data.skills
        ? data.skills.split(",").map((s) => s.trim()).filter((s) => s.length > 0)
        : undefined;

      await updateProfile.mutateAsync({
        targetRole: data.targetRole || undefined,
        experienceLevel: data.experienceLevel || undefined,
        skills,
      });

      setSuccessMessage("Profile updated successfully.");
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (error: unknown) {
      if (error && typeof error === "object" && "response" in error) {
        const axiosError = error as { response?: { data?: { detail?: string } } };
        setFormError(axiosError.response?.data?.detail ?? "Failed to update profile.");
      } else if (error instanceof Error) {
        setFormError(error.message);
      } else {
        setFormError("Failed to update profile. Please try again.");
      }
    }
  };

  if (isProfileLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Loading profile...</span>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {formError && (
        <div
          className="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive"
          role="alert"
        >
          {formError}
        </div>
      )}

      {successMessage && (
        <div
          className="rounded-md bg-green-50 border border-green-200 p-3 text-sm text-green-800 flex items-center gap-2 dark:bg-green-950/20 dark:border-green-900 dark:text-green-400"
          role="status"
        >
          <CheckCircle2 className="h-4 w-4" />
          {successMessage}
        </div>
      )}

      <div className="space-y-2">
        <label htmlFor="targetRole" className="text-sm font-medium text-foreground">
          Target Role
        </label>
        <input
          id="targetRole"
          type="text"
          placeholder="e.g. Senior Frontend Engineer"
          className={cn(
            "flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
            errors.targetRole ? "border-destructive" : "border-input"
          )}
          aria-invalid={errors.targetRole ? "true" : undefined}
          aria-describedby={errors.targetRole ? "targetRole-error" : undefined}
          {...register("targetRole")}
        />
        {errors.targetRole && (
          <p id="targetRole-error" className="text-xs text-destructive">
            {errors.targetRole.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <label htmlFor="experienceLevel" className="text-sm font-medium text-foreground">
          Experience Level
        </label>
        <select
          id="experienceLevel"
          className={cn(
            "flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
            errors.experienceLevel ? "border-destructive" : "border-input"
          )}
          aria-invalid={errors.experienceLevel ? "true" : undefined}
          aria-describedby={errors.experienceLevel ? "experienceLevel-error" : undefined}
          {...register("experienceLevel")}
        >
          <option value="">Select experience level</option>
          {EXPERIENCE_LEVELS.map((level) => (
            <option key={level.value} value={level.value}>
              {level.label}
            </option>
          ))}
        </select>
        {errors.experienceLevel && (
          <p id="experienceLevel-error" className="text-xs text-destructive">
            {errors.experienceLevel.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <label htmlFor="skills" className="text-sm font-medium text-foreground">
          Skills
        </label>
        <input
          id="skills"
          type="text"
          placeholder="e.g. React, TypeScript, Node.js"
          className={cn(
            "flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
            errors.skills ? "border-destructive" : "border-input"
          )}
          aria-invalid={errors.skills ? "true" : undefined}
          aria-describedby={errors.skills ? "skills-error" : "skills-hint"}
          {...register("skills")}
        />
        <p id="skills-hint" className="text-xs text-muted-foreground">
          Separate multiple skills with commas.
        </p>
        {errors.skills && (
          <p id="skills-error" className="text-xs text-destructive">
            {errors.skills.message}
          </p>
        )}
      </div>

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Save Profile
      </Button>
    </form>
  );
}

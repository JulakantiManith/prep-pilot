import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2, CheckCircle2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { cn } from "@/shared/lib/utils";
import { supabase } from "@/shared/lib/supabase";
import { z } from "zod";

const passwordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters")
  .regex(/[A-Z]/, "Must contain at least one uppercase letter")
  .regex(/[a-z]/, "Must contain at least one lowercase letter")
  .regex(/[0-9]/, "Must contain at least one number");

const resetFormSchema = z.object({
  newPassword: passwordSchema,
});

type ResetFormData = z.infer<typeof resetFormSchema>;

export function ResetPasswordForm() {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isRecoverySession, setIsRecoverySession] = useState(false);
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetFormData>({
    resolver: zodResolver(resetFormSchema),
  });

  // Detect if we arrived via a Supabase recovery redirect
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        if (event === "PASSWORD_RECOVERY" && session) {
          setIsRecoverySession(true);
          setIsCheckingSession(false);
        }
      }
    );

    // Also check if there's already an active session (user might have
    // arrived here with tokens in the URL hash already processed)
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        // Check if the URL hash contains recovery indicators
        const hash = window.location.hash;
        if (hash.includes("type=recovery") || hash.includes("type=magiclink")) {
          setIsRecoverySession(true);
        } else {
          // User has a session — they likely came from the recovery email
          setIsRecoverySession(true);
        }
      }
      setIsCheckingSession(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const onSubmit = async (data: ResetFormData) => {
    setFormError(null);
    setSuccessMessage(null);
    try {
      if (isRecoverySession) {
        // Use Supabase client directly to update password with the active recovery session
        const { error } = await supabase.auth.updateUser({
          password: data.newPassword,
        });
        if (error) {
          setFormError(error.message || "Failed to reset password. Please try again.");
          return;
        }
      } else {
        setFormError("Invalid reset session. Please request a new password reset link.");
        return;
      }
      setSuccessMessage("Your password has been reset successfully.");
    } catch (error) {
      if (error instanceof Error) {
        setFormError(error.message);
      } else {
        setFormError("The reset link is invalid or has expired. Please request a new one.");
      }
    }
  };

  if (isCheckingSession) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!isRecoverySession) {
    return (
      <div className="space-y-4 text-center">
        <p className="text-sm text-destructive">
          Invalid or expired reset link. Please request a new one.
        </p>
        <Link
          to="/forgot-password"
          className="inline-block text-sm text-primary hover:underline font-medium"
        >
          Request a new reset link
        </Link>
      </div>
    );
  }

  if (successMessage) {
    return (
      <div className="space-y-4 text-center">
        <CheckCircle2 className="mx-auto h-12 w-12 text-green-500" />
        <p className="text-sm text-muted-foreground">{successMessage}</p>
        <Link
          to="/login"
          className="inline-block text-sm text-primary hover:underline font-medium"
          onClick={async (e) => {
            e.preventDefault();
            await supabase.auth.signOut();
            navigate("/login");
          }}
        >
          Sign in with your new password
        </Link>
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

      <div className="space-y-2">
        <label htmlFor="newPassword" className="text-sm font-medium text-foreground">
          New Password
        </label>
        <div className="relative">
          <input
            id="newPassword"
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            placeholder="Enter your new password"
            className={cn(
              "input-focus-glow flex h-10 w-full rounded-lg border bg-background px-3 py-2 pr-10 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200",
              errors.newPassword ? "border-destructive" : "border-input"
            )}
            aria-invalid={errors.newPassword ? "true" : undefined}
            aria-describedby={errors.newPassword ? "newPassword-error" : undefined}
            {...register("newPassword")}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        {errors.newPassword && (
          <p id="newPassword-error" className="text-xs text-destructive">
            {errors.newPassword.message}
          </p>
        )}
        <p className="text-xs text-muted-foreground">
          At least 8 characters with uppercase, lowercase, and a number.
        </p>
      </div>

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Reset Password
      </Button>
    </form>
  );
}

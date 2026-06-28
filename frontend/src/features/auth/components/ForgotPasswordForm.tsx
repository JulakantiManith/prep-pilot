import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link } from "react-router-dom";
import { Loader2, CheckCircle2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { cn } from "@/shared/lib/utils";
import { forgotPasswordSchema } from "../schemas/authSchemas";
import type { ForgotPasswordFormData } from "../schemas/authSchemas";
import { useAuth } from "../hooks/useAuth";

export function ForgotPasswordForm() {
  const { forgotPassword } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordFormData) => {
    setFormError(null);
    setSuccessMessage(null);
    try {
      await forgotPassword(data.email);
      setSuccessMessage(
        "If an account exists with that email, you will receive a password reset link shortly."
      );
    } catch {
      // Always show success for security (prevent email enumeration)
      setSuccessMessage(
        "If an account exists with that email, you will receive a password reset link shortly."
      );
    }
  };

  if (successMessage) {
    return (
      <div className="space-y-4 text-center">
        <CheckCircle2 className="mx-auto h-12 w-12 text-green-500" />
        <p className="text-sm text-muted-foreground">{successMessage}</p>
        <Link
          to="/login"
          className="inline-block text-sm text-primary hover:underline font-medium"
        >
          Back to sign in
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

      <p className="text-sm text-muted-foreground">
        Enter your email address and we&apos;ll send you a link to reset your password.
      </p>

      <div className="space-y-2">
        <label htmlFor="email" className="text-sm font-medium text-foreground">
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          className={cn(
            "input-focus-glow flex h-10 w-full rounded-lg border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200",
            errors.email ? "border-destructive" : "border-input"
          )}
          aria-invalid={errors.email ? "true" : undefined}
          aria-describedby={errors.email ? "email-error" : undefined}
          {...register("email")}
        />
        {errors.email && (
          <p id="email-error" className="text-xs text-destructive">
            {errors.email.message}
          </p>
        )}
      </div>

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Send Reset Link
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        Remember your password?{" "}
        <Link to="/login" className="text-primary hover:underline font-medium">
          Sign in
        </Link>
      </p>
    </form>
  );
}

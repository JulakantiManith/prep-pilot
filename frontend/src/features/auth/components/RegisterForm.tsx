import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { cn } from "@/shared/lib/utils";
import { registerSchema } from "../schemas/authSchemas";
import type { RegisterFormData } from "../schemas/authSchemas";
import { useAuth } from "../hooks/useAuth";

export function RegisterForm() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    setFormError(null);
    try {
      await registerUser(data);
      navigate("/login", {
        state: { message: "Account created! Please check your email to verify your account." },
      });
    } catch (error) {
      const err = error as { code?: string; message?: string };
      if (err.code === "over_email_send_rate_limit") {
        setFormError("Too many attempts. Please wait a few minutes before trying again.");
      } else if (error instanceof Error) {
        setFormError(error.message);
      } else {
        setFormError("Registration failed. Please try again.");
      }
    }
  };

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
        <label htmlFor="fullName" className="text-sm font-medium text-foreground">
          Full Name
        </label>
        <input
          id="fullName"
          type="text"
          autoComplete="name"
          placeholder="John Doe"
          className={cn(
            "input-focus-glow flex h-10 w-full rounded-lg border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200",
            errors.fullName ? "border-destructive" : "border-input"
          )}
          aria-invalid={errors.fullName ? "true" : undefined}
          aria-describedby={errors.fullName ? "fullName-error" : undefined}
          {...register("fullName")}
        />
        {errors.fullName && (
          <p id="fullName-error" className="text-xs text-destructive">
            {errors.fullName.message}
          </p>
        )}
      </div>

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

      <div className="space-y-2">
        <label htmlFor="password" className="text-sm font-medium text-foreground">
          Password
        </label>
        <div className="relative">
          <input
            id="password"
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            placeholder="Create a strong password"
            className={cn(
              "input-focus-glow flex h-10 w-full rounded-lg border bg-background px-3 py-2 pr-10 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200",
              errors.password ? "border-destructive" : "border-input"
            )}
            aria-invalid={errors.password ? "true" : undefined}
            aria-describedby={errors.password ? "password-error" : undefined}
            {...register("password")}
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
        {errors.password && (
          <p id="password-error" className="text-xs text-destructive">
            {errors.password.message}
          </p>
        )}
        <p className="text-xs text-muted-foreground">
          At least 8 characters with uppercase, lowercase, and a number.
        </p>
      </div>

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Create Account
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link to="/login" className="text-primary hover:underline font-medium">
          Sign in
        </Link>
      </p>
    </form>
  );
}

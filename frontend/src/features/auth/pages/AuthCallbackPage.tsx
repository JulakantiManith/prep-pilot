import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/shared/lib/supabase";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";

/**
 * Handles Supabase auth redirects (email verification, magic links, etc.).
 *
 * When Supabase redirects back after email verification, it appends tokens
 * to the URL. The Supabase client automatically detects and exchanges them.
 * This page waits for that exchange to complete, then navigates the user
 * to the dashboard (or login on failure).
 */
export function AuthCallbackPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function handleAuthCallback() {
      try {
        // Supabase JS client auto-detects tokens in URL hash/query params
        // and exchanges them for a session. We just need to verify it worked.
        const { data, error: sessionError } = await supabase.auth.getSession();

        if (sessionError) {
          console.error("[Auth Callback] Session error:", sessionError.message);
          setError("Verification failed. Please try logging in.");
          setTimeout(() => navigate("/login", { replace: true }), 3000);
          return;
        }

        if (data.session) {
          // Session established — user is verified and logged in
          navigate("/dashboard", { replace: true });
        } else {
          // No session yet — might still be exchanging token, listen for changes
          const { data: { subscription } } = supabase.auth.onAuthStateChange(
            (_event, session) => {
              if (session) {
                subscription.unsubscribe();
                navigate("/dashboard", { replace: true });
              }
            }
          );

          // Timeout: if no session after 5s, redirect to login
          setTimeout(() => {
            subscription.unsubscribe();
            navigate("/login", { replace: true });
          }, 5000);
        }
      } catch (err) {
        console.error("[Auth Callback] Unexpected error:", err);
        setError("Something went wrong. Redirecting to login...");
        setTimeout(() => navigate("/login", { replace: true }), 3000);
      }
    }

    handleAuthCallback();
  }, [navigate]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="text-center space-y-4">
          <p className="text-destructive">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <LoadingSpinner size="lg" label="Verifying your account..." />
    </div>
  );
}

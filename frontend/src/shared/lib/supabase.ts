import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "Missing Supabase environment variables. Please set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY."
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// --- Auth Redirect Helpers ---

/**
 * Basic RFC 1123 hostname validation.
 * Labels must be 1-63 chars, alphanumeric + hyphens (no leading/trailing hyphen).
 * Total hostname max 253 chars.
 */
export function isValidHostname(hostname: string): boolean {
  if (!hostname || hostname.length > 253) {
    return false;
  }
  const labels = hostname.split(".");
  if (labels.length < 1) {
    return false;
  }
  const labelRegex = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$/;
  return labels.every((label) => labelRegex.test(label));
}

/**
 * Resolve the application domain for auth redirects.
 * Returns `https://{viteAppDomain}` if viteAppDomain is a valid hostname,
 * otherwise returns windowOrigin as the fallback.
 * Logs a console.warn when viteAppDomain is set but invalid.
 */
export function resolveAppDomain(
  viteAppDomain: string | undefined,
  windowOrigin: string
): string {
  if (!viteAppDomain) {
    return windowOrigin;
  }
  if (isValidHostname(viteAppDomain)) {
    return `https://${viteAppDomain}`;
  }
  console.warn(
    `[Auth] VITE_APP_DOMAIN is set but invalid: "${viteAppDomain}". Falling back to window origin.`
  );
  return windowOrigin;
}

/**
 * Build an auth redirect URL by combining the resolved domain with a path.
 * Ensures no double slashes between base and path.
 */
export function buildAuthRedirectUrl(path: string): string {
  const base = resolveAppDomain(
    import.meta.env.VITE_APP_DOMAIN as string | undefined,
    window.location.origin
  );
  const normalizedBase = base.endsWith("/") ? base.slice(0, -1) : base;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

/**
 * Get the email verification redirect URL.
 */
export function getEmailVerificationUrl(): string {
  return buildAuthRedirectUrl("/auth/callback");
}

/**
 * Get the password reset redirect URL.
 */
export function getPasswordResetUrl(): string {
  return buildAuthRedirectUrl("/reset-password");
}

# Requirements Document

## Introduction

This feature establishes a domain-independent infrastructure layer for the AI Interview & Presentation Coach application. The system must operate correctly regardless of whether a custom domain is configured, expired, or intentionally removed. All URL references and service configurations are driven exclusively by environment variables, ensuring that domain changes require no code modifications — only environment variable updates, deployment settings, and Supabase configuration changes.

## Glossary

- **Frontend**: The React + Vite + TypeScript client application deployed to Vercel
- **Backend**: The FastAPI + Python server application deployed to Render
- **URL_Resolver**: The module responsible for computing application URLs from environment variables at runtime
- **Auth_Redirect_Builder**: The component that constructs authentication callback and redirect URLs from environment configuration
- **CORS_Configuration**: The middleware configuration that controls which origins the Backend accepts requests from
- **SMTP_Configuration**: The set of environment variables controlling email sending (host, port, credentials, sender identity)
- **Fallback_URL**: The default platform-provided URL (Vercel deployment URL for Frontend, Render deployment URL for Backend) used when no custom domain is configured
- **Custom_Domain**: An optional user-owned domain name pointed at the application via DNS records
- **Environment_Variables**: Runtime configuration values injected at deployment time, not hardcoded in source

## Requirements

### Requirement 1: Environment-Driven URL Resolution

**User Story:** As a developer, I want all application URLs to be resolved from environment variables, so that switching domains requires no code changes.

#### Acceptance Criteria

1. THE URL_Resolver SHALL read the FRONTEND_URL environment variable and use its value as the Frontend base URL, stripping any trailing slash before use
2. THE URL_Resolver SHALL read the BACKEND_URL environment variable and use its value as the Backend base URL, stripping any trailing slash before use
3. THE Frontend SHALL read VITE_APP_DOMAIN and use its value as the base URL for constructing redirect URLs and displaying the application domain in the UI
4. WHEN VITE_APP_DOMAIN is not set or is empty, THE Frontend SHALL use the current window origin (the default Vercel deployment URL) as the base URL
5. THE Backend SHALL read APP_DOMAIN, FRONTEND_URL, and BACKEND_URL from environment variables exclusively, with no domain strings hardcoded in source code
6. WHEN FRONTEND_URL is not set or is empty, THE Backend SHALL fall back to http://localhost:5173 as the Frontend base URL
7. WHEN BACKEND_URL is not set or is empty, THE Backend SHALL fall back to http://localhost:8000 as the Backend base URL
8. IF FRONTEND_URL or BACKEND_URL is set to a value that does not begin with http:// or https://, THEN THE Backend SHALL log an error message indicating the invalid URL format and fail to start
9. IF APP_DOMAIN is set but FRONTEND_URL is not set, THEN THE Backend SHALL log a warning at startup indicating that FRONTEND_URL is missing while APP_DOMAIN is configured

### Requirement 2: Zero Hardcoded Domain References

**User Story:** As a developer, I want no hardcoded domain references in the codebase, so that domain changes do not require searching and replacing strings in source files.

#### Acceptance Criteria

1. THE Frontend SHALL contain zero hardcoded references to any Custom_Domain name in source files, where a Custom_Domain reference is any user-owned domain string (excluding localhost URLs and platform-provided Fallback_URLs such as *.vercel.app)
2. THE Backend SHALL contain zero hardcoded references to any Custom_Domain name in source files, where a Custom_Domain reference is any user-owned domain string (excluding localhost URLs and platform-provided Fallback_URLs such as *.onrender.com)
3. THE CORS_Configuration SHALL derive allowed origins exclusively from environment variables, with no Custom_Domain literals present in source code
4. WHEN a new origin needs to be allowed, THE CORS_Configuration SHALL require only an environment variable update and redeployment, with no source file modifications
5. IF a static analysis scan of Frontend source files (.ts, .tsx, .js, .jsx, .css, .html excluding node_modules and build output) detects a Custom_Domain string literal, THEN THE scan SHALL report a failure
6. IF a static analysis scan of Backend source files (.py excluding __pycache__ and virtual environments) detects a Custom_Domain string literal, THEN THE scan SHALL report a failure

### Requirement 3: Domain-Independent Authentication Redirects

**User Story:** As a user, I want authentication flows (registration, login, password reset) to work regardless of which domain the application is served from, so that I can always access my account.

#### Acceptance Criteria

1. THE Auth_Redirect_Builder SHALL construct all authentication redirect URLs by prepending "https://" to VITE_APP_DOMAIN when VITE_APP_DOMAIN is set and non-empty, or by using the Fallback_URL when VITE_APP_DOMAIN is not set or is empty
2. WHEN a user registers, THE Auth_Redirect_Builder SHALL generate the email verification callback URL by appending the verification path to the resolved base URL from criterion 1
3. WHEN a user requests a password reset, THE Auth_Redirect_Builder SHALL generate the reset link URL by appending the password reset path to the resolved base URL from criterion 1
4. WHEN VITE_APP_DOMAIN changes from a custom domain to empty, THE Auth_Redirect_Builder SHALL generate redirect URLs using the Fallback_URL without code changes
5. THE Frontend SHALL pass redirect URLs derived from the Auth_Redirect_Builder in signUp, resetPasswordForEmail, and signInWithOtp calls to Supabase Auth as the emailRedirectTo option
6. IF VITE_APP_DOMAIN is set but contains an invalid domain value that does not match a valid hostname format, THEN THE Auth_Redirect_Builder SHALL fall back to the Fallback_URL and log a warning to the browser console

### Requirement 4: Domain-Independent SMTP and Email Configuration

**User Story:** As an operator, I want email sending to be independent of the application domain, so that I can switch email providers or recover from domain expiration without code changes.

#### Acceptance Criteria

1. THE SMTP_Configuration SHALL be configurable independently from APP_DOMAIN via separate environment variables: SMTP_HOST, SMTP_PORT (valid range: 1–65535), SMTP_USERNAME, SMTP_PASSWORD, SMTP_SENDER_EMAIL (maximum 254 characters), and SMTP_SENDER_NAME (maximum 78 characters)
2. WHEN SMTP environment variables are updated and the Backend is redeployed, THE Backend SHALL use the new SMTP configuration for all subsequent email operations without requiring source code changes
3. THE Backend SHALL not derive SMTP sender email or host from APP_DOMAIN programmatically
4. WHEN any of the required SMTP environment variables (SMTP_HOST, SMTP_PORT, SMTP_SENDER_EMAIL) are missing or empty at startup, THE Backend SHALL disable all email-sending features, continue serving non-email API requests, and log a warning message indicating which SMTP variables are missing
5. IF a request is made to an endpoint that requires email sending while email features are disabled, THEN THE Backend SHALL return an error response indicating that email functionality is unavailable
6. WHEN all required SMTP environment variables are present at startup, THE Backend SHALL log a confirmation message indicating that email sending is active with the configured SMTP_HOST and SMTP_SENDER_EMAIL values

### Requirement 5: Graceful Degradation on Domain Removal

**User Story:** As an operator, I want the application to continue functioning if the custom domain is removed or expires, so that users are not locked out of the service.

#### Acceptance Criteria

1. WHEN APP_DOMAIN is removed or set to empty, THE Backend SHALL continue to respond to API requests on the Render deployment URL with the same HTTP status codes as when APP_DOMAIN is configured
2. WHEN VITE_APP_DOMAIN is removed or set to empty, THE Frontend SHALL render all application routes and navigation links using the Vercel deployment URL as the base URL without displaying error pages or unresolvable links
3. IF the custom domain is removed and the Fallback_URL is included in the ALLOWED_ORIGINS environment variable, THEN THE CORS_Configuration SHALL accept cross-origin requests from the Fallback_URL origin
4. IF a configured FRONTEND_URL or BACKEND_URL fails to respond within 5 seconds during startup reachability check, THEN THE Backend SHALL log a warning message identifying the unreachable URL and continue to operate normally
5. WHEN VITE_APP_DOMAIN is unset or empty, THE Frontend SHALL generate all internal links and navigation targets using the Vercel deployment URL, resulting in zero links that resolve to an undefined or empty host

### Requirement 6: CORS Configuration Flexibility

**User Story:** As a developer, I want CORS allowed origins to be environment-driven and support multiple origins, so that I can run the app on both custom domains and default deployment URLs simultaneously.

#### Acceptance Criteria

1. THE CORS_Configuration SHALL accept a comma-separated list of allowed origins from the ALLOWED_ORIGINS environment variable, trimming whitespace from each entry
2. WHEN ALLOWED_ORIGINS contains multiple comma-separated values, THE CORS_Configuration SHALL allow cross-origin requests from each listed origin independently
3. WHEN FRONTEND_URL is set to a custom domain value, THE CORS_Configuration SHALL automatically include the FRONTEND_URL origin in the allowed origins list in addition to any values in ALLOWED_ORIGINS
4. WHEN ALLOWED_ORIGINS is not set or is empty, THE CORS_Configuration SHALL default to allowing http://localhost:5173 as the sole allowed origin
5. IF ALLOWED_ORIGINS contains entries that do not begin with http:// or https://, THEN THE CORS_Configuration SHALL ignore those entries and log a warning identifying the invalid origin value

### Requirement 7: Recovery Without Code Changes

**User Story:** As an operator, I want to recover full application functionality after a domain expiration by updating only environment variables, deployment settings, and Supabase configuration, so that no developer intervention is required for code changes.

#### Acceptance Criteria

1. WHEN a custom domain expires, THE application SHALL be recoverable to full functionality — defined as: Frontend loads, Backend responds to API requests, authentication flows (login, registration, password reset) complete, and CORS permits Frontend-to-Backend communication — by updating environment variables (APP_DOMAIN, FRONTEND_URL, BACKEND_URL, VITE_APP_DOMAIN, ALLOWED_ORIGINS), Supabase Auth redirect URLs, and redeploying the Frontend and Backend services
2. THE application SHALL not require any source code modifications, database schema changes, or infrastructure recreation to switch between a custom domain and default deployment URLs
3. THE Backend SHALL validate the presence of APP_DOMAIN, FRONTEND_URL, and BACKEND_URL at startup and log one message per missing variable at WARNING level, specifying the variable name and the fallback value being used
4. WHEN switching from custom domain to Fallback_URL, THE application SHALL require only environment variable updates, Supabase Auth redirect URL updates, and redeployment of the Frontend and Backend to complete the transition within 3 configuration changes per service (excluding Supabase dashboard)
5. IF the Backend starts with none of the optional domain variables (APP_DOMAIN, FRONTEND_URL, BACKEND_URL) configured, THEN THE Backend SHALL start successfully using fallback values and log a summary message indicating the application is running in default-URL mode

### Requirement 8: Platform URL Preservation

**User Story:** As an operator, I want the original Vercel and Render deployment URLs to remain functional even when a custom domain is configured, so that I always have an emergency recovery path.

#### Acceptance Criteria

1. WHILE a Custom_Domain is configured, THE application SHALL serve requests and respond to both the Custom_Domain URLs and the original Vercel and Render platform deployment URLs, including API endpoints, static assets, and authentication flows
2. WHEN a Custom_Domain is configured, THE application SHALL NOT require disabling or removing the platform-provided deployment URLs
3. THE deployment documentation SHALL include a recovery procedure that specifies: updating FRONTEND_URL, BACKEND_URL, APP_DOMAIN, and VITE_APP_DOMAIN environment variables to platform deployment URLs, updating Supabase Auth redirect URLs to include the platform deployment URLs, and redeploying both Frontend and Backend
4. IF a Custom_Domain expires or DNS becomes misconfigured, THEN operators SHALL restore full application functionality — including user authentication, API access, and Frontend rendering — through the original platform deployment URLs by updating only environment variables, Supabase redirect URL configuration, and redeploying
5. THE Backend health check endpoint SHALL return a response containing the configured APP_DOMAIN value (or empty if unset), the FRONTEND_URL value, the BACKEND_URL value, and a domain_mode field indicating one of: "custom_domain", "platform_url", or "both"
6. WHEN recovering from Custom_Domain failure, THE application SHALL NOT require database schema changes, source code changes, or infrastructure recreation

### Requirement 9: Testable Domain Configuration Scenarios

**User Story:** As a developer, I want to verify the application works in all domain configurations (custom domain, no custom domain, default URLs only), so that I have confidence in the domain-independence guarantees.

#### Acceptance Criteria

1. THE Backend SHALL expose a health check endpoint that reports the currently configured FRONTEND_URL, BACKEND_URL, and APP_DOMAIN values in the response body
2. THE URL_Resolver SHALL accept environment variable values as input parameters, enabling invocation in tests without requiring real environment variables, external services, or network access
3. WHEN FRONTEND_URL, BACKEND_URL, and APP_DOMAIN are set to custom domain values, THE URL_Resolver SHALL produce base URLs matching the configured custom domain values
4. WHEN FRONTEND_URL, BACKEND_URL, and APP_DOMAIN are empty or unset, THE URL_Resolver SHALL produce base URLs matching the Fallback_URL values (localhost defaults for Backend, Vercel deployment URL for Frontend)
5. THE Auth_Redirect_Builder SHALL accept domain configuration as input parameters, enabling invocation in tests without requiring real environment variables, external services, or network access
6. WHEN the Auth_Redirect_Builder is invoked with custom domain configuration, THEN it SHALL produce redirect URLs with the custom domain as the host
7. WHEN the Auth_Redirect_Builder is invoked with empty domain configuration, THEN it SHALL produce redirect URLs with the Fallback_URL as the host
8. THE application SHALL be testable under three domain configurations: custom domain set (all domain variables populated), no custom domain (all domain variables empty or unset), and mixed (FRONTEND_URL set to custom domain while APP_DOMAIN is empty)

# Requirements Document

## Introduction

This feature introduces a provider abstraction layer for AI services and adds OpenRouter's `openrouter/free` router as a fallback provider. The goal is to decouple AI-powered features from a single provider (Gemini), reduce downtime caused by Gemini free-tier rate limits, and improve application reliability. When Gemini is unavailable, rate-limited, or returns errors, the system automatically falls back to OpenRouter to maintain uninterrupted service for resume parsing, interview question generation, resume-based interview generation, and AI feedback generation.

## Glossary

- **AI_Provider**: An external service that accepts prompts and returns generated text responses (e.g., Gemini, OpenRouter).
- **Provider_Abstraction_Layer**: A module that provides a unified interface to multiple AI providers, hiding provider-specific implementation details from consuming services.
- **Fallback_Provider**: A secondary AI provider that is used when the primary provider is unavailable or fails.
- **Primary_Provider**: The preferred AI provider used for all requests under normal operating conditions (Gemini).
- **OpenRouter_Client**: An integration client that communicates with the OpenRouter API using the `openrouter/free` model router.
- **Response_Normalizer**: A component that transforms provider-specific response formats into a consistent internal format.
- **JSON_Validator**: A component that validates structured JSON outputs against expected schemas and attempts repair of malformed responses.
- **Provider_Health_Monitor**: A component that tracks provider availability, failures, and recovery to inform routing decisions.
- **Gemini_Client**: The existing integration client for Google's Gemini API.
- **Resume_Parser**: The service responsible for extracting structured data (skills, projects, experience, education) from uploaded resumes.
- **Question_Generator**: The service responsible for generating interview questions.
- **AI_Feedback_Service**: The service responsible for generating AI-powered feedback reports for interview sessions.

## Requirements

### Requirement 1: Provider Abstraction Layer

**User Story:** As a developer, I want AI features to use a provider-agnostic interface, so that I can add, remove, or switch AI providers without modifying consuming services.

#### Acceptance Criteria

1. THE Provider_Abstraction_Layer SHALL expose a unified interface for sending prompts and receiving text responses, independent of the underlying AI_Provider.
2. WHEN a consuming service calls the Provider_Abstraction_Layer, THE Provider_Abstraction_Layer SHALL route the request to the configured Primary_Provider.
3. THE Provider_Abstraction_Layer SHALL allow registration of multiple AI_Provider implementations without requiring changes to consuming services.
4. THE Question_Generator, AI_Feedback_Service, and Resume_Parser SHALL use the Provider_Abstraction_Layer instead of directly referencing the Gemini_Client.

### Requirement 2: OpenRouter Client Integration

**User Story:** As a developer, I want an OpenRouter client that uses the `openrouter/free` model router, so that the application has access to a free fallback AI provider.

#### Acceptance Criteria

1. THE OpenRouter_Client SHALL communicate with the OpenRouter API using the `openrouter/free` model endpoint.
2. THE OpenRouter_Client SHALL authenticate requests using an API key loaded from the `OPENROUTER_API_KEY` environment variable.
3. THE OpenRouter_Client SHALL implement the same unified interface as the Gemini_Client within the Provider_Abstraction_Layer.
4. WHEN the OpenRouter API returns an error, THE OpenRouter_Client SHALL raise a provider-specific error that the Provider_Abstraction_Layer can handle.
5. THE OpenRouter_Client SHALL enforce a 45-second timeout per request, consistent with the Gemini_Client timeout.

### Requirement 3: Fallback Routing

**User Story:** As a user, I want the application to automatically switch to a backup AI provider when Gemini fails, so that my interview preparation is not interrupted by provider outages.

#### Acceptance Criteria

1. THE Provider_Abstraction_Layer SHALL be configured with Gemini as the Primary_Provider and OpenRouter as the Fallback_Provider.
2. WHEN the Primary_Provider returns a rate-limit error (HTTP 429 or ResourceExhausted), THE Provider_Abstraction_Layer SHALL route the request to the Fallback_Provider.
3. WHEN the Primary_Provider returns a service-unavailable error, THE Provider_Abstraction_Layer SHALL route the request to the Fallback_Provider.
4. WHEN the Primary_Provider request times out after 45 seconds, THE Provider_Abstraction_Layer SHALL route the request to the Fallback_Provider.
5. WHEN the Primary_Provider returns any other API error after exhausting retries, THE Provider_Abstraction_Layer SHALL route the request to the Fallback_Provider.
6. THE Provider_Abstraction_Layer SHALL attempt one retry with exponential backoff on the Primary_Provider before falling back.

### Requirement 4: Response Normalization

**User Story:** As a developer, I want all AI provider responses to be in a consistent format, so that consuming services do not need provider-specific parsing logic.

#### Acceptance Criteria

1. THE Response_Normalizer SHALL transform responses from each AI_Provider into a uniform text string format before returning to the consuming service.
2. WHEN the Gemini_Client returns a response, THE Response_Normalizer SHALL extract the text content and strip any provider-specific metadata.
3. WHEN the OpenRouter_Client returns a response, THE Response_Normalizer SHALL extract the text content from the OpenAI-compatible response format.
4. THE Response_Normalizer SHALL preserve the complete generated text without truncation or modification of content.

### Requirement 5: JSON Output Validation and Repair

**User Story:** As a developer, I want structured JSON outputs to be validated and repaired when possible, so that malformed AI responses do not cause downstream failures.

#### Acceptance Criteria

1. WHEN a consuming service requests structured JSON output, THE JSON_Validator SHALL validate the response against the expected schema.
2. WHEN a response contains valid JSON wrapped in markdown code fences, THE JSON_Validator SHALL strip the code fences and extract the JSON content.
3. WHEN a response contains trailing commas, unquoted keys, or single-quoted strings, THE JSON_Validator SHALL attempt to repair the JSON into valid format.
4. IF the JSON_Validator cannot repair a malformed response, THEN THE Provider_Abstraction_Layer SHALL retry the request once with the same provider before escalating to fallback.
5. WHEN the JSON_Validator successfully repairs a malformed response, THE JSON_Validator SHALL log a warning with the original and repaired content for debugging.

### Requirement 6: Resume Parsing Accuracy Across Providers

**User Story:** As a user, I want my resume data to be accurately extracted regardless of which AI provider processes it, so that my interview preparation is based on correct information.

#### Acceptance Criteria

1. THE Resume_Parser SHALL validate that extracted skills, projects, experience, and education fields conform to the expected schema before storing results.
2. WHEN extracted_data contains empty required fields (skills as empty array AND experience as empty array AND education as empty array), THE Resume_Parser SHALL reject the extraction and retry with the Fallback_Provider.
3. THE Resume_Parser SHALL validate that each experience entry contains non-empty title and company fields.
4. THE Resume_Parser SHALL validate that each education entry contains non-empty degree and institution fields.
5. IF the Resume_Parser receives extraction results that fail validation from both providers, THEN THE Resume_Parser SHALL set the extraction status to "failed" and return a descriptive error.
6. THE Resume_Parser SHALL validate the confidence score is between 0.0 and 1.0, and reject extractions with confidence below 0.2 for re-extraction with the Fallback_Provider.

### Requirement 7: Service Continuity

**User Story:** As a user, I want all AI-powered features to continue working when Gemini is unavailable, so that I can prepare for interviews without interruption.

#### Acceptance Criteria

1. WHEN the Primary_Provider is unavailable, THE Question_Generator SHALL generate questions using the Fallback_Provider before resorting to the predefined question bank.
2. WHEN the Primary_Provider is unavailable, THE AI_Feedback_Service SHALL generate feedback using the Fallback_Provider before resorting to algorithmic feedback.
3. WHEN the Primary_Provider is unavailable, THE Resume_Parser SHALL extract resume data using the Fallback_Provider.
4. WHEN both the Primary_Provider and Fallback_Provider are unavailable, THE Question_Generator SHALL use the predefined question bank fallback.
5. WHEN both the Primary_Provider and Fallback_Provider are unavailable, THE AI_Feedback_Service SHALL use the algorithmic feedback fallback.

### Requirement 8: Provider Usage Logging

**User Story:** As a developer, I want detailed logging of provider usage and fallback events, so that I can monitor system health and debug provider issues.

#### Acceptance Criteria

1. WHEN a request is routed to any AI_Provider, THE Provider_Abstraction_Layer SHALL log the provider name, request type, and timestamp.
2. WHEN a request fails on the Primary_Provider, THE Provider_Abstraction_Layer SHALL log the failure reason, provider name, and whether fallback was triggered.
3. WHEN a fallback event occurs, THE Provider_Abstraction_Layer SHALL log the original provider, fallback provider, failure reason, and request type.
4. WHEN a retry is attempted, THE Provider_Abstraction_Layer SHALL log the retry attempt number, backoff duration, and provider name.
5. THE Provider_Abstraction_Layer SHALL log the total response time for each request including any retry and fallback durations.
6. WHEN the JSON_Validator repairs or rejects a response, THE Provider_Abstraction_Layer SHALL log the validation outcome and provider that produced the response.

### Requirement 9: Configuration Management

**User Story:** As a developer, I want provider configuration to be centralized and environment-driven, so that I can easily adjust provider settings across environments.

#### Acceptance Criteria

1. THE Settings SHALL include an `openrouter_api_key` field loaded from the `OPENROUTER_API_KEY` environment variable.
2. THE Settings SHALL include an `ai_primary_provider` field with a default value of "gemini".
3. THE Settings SHALL include an `ai_fallback_provider` field with a default value of "openrouter".
4. WHEN the `OPENROUTER_API_KEY` environment variable is empty or missing, THE Provider_Abstraction_Layer SHALL skip OpenRouter as a fallback option and log a warning at startup.
5. THE Settings SHALL include an `ai_request_timeout` field with a default value of 45 seconds.

### Requirement 10: Retry Logic

**User Story:** As a developer, I want consistent retry behavior across all AI providers, so that transient failures are handled gracefully without unnecessary fallback switches.

#### Acceptance Criteria

1. THE Provider_Abstraction_Layer SHALL retry failed requests once with exponential backoff (2-second base delay) before triggering fallback.
2. WHEN a rate-limit error includes a retry-after header, THE Provider_Abstraction_Layer SHALL use the specified delay instead of the default backoff.
3. THE Provider_Abstraction_Layer SHALL track consecutive failures per provider to avoid retrying a provider that has failed multiple times in quick succession.
4. WHEN a provider has failed 3 consecutive times within a 60-second window, THE Provider_Abstraction_Layer SHALL skip retries on that provider and route directly to the Fallback_Provider for subsequent requests until the window expires.

### Requirement 11: Provider Capability Routing

**User Story:** As a developer, I want requests to be routed to providers based on their capabilities, so that each task is handled by a provider suited to that type of work.

#### Acceptance Criteria

1. THE Provider_Abstraction_Layer SHALL maintain a capability registry that maps each AI_Provider to its supported task types (question generation, feedback generation, resume extraction).
2. WHEN a request is made for a specific task type, THE Provider_Abstraction_Layer SHALL verify the target provider supports that task type before routing.
3. WHEN the Primary_Provider does not support a requested task type, THE Provider_Abstraction_Layer SHALL route the request directly to the next provider in the chain that supports the task type.
4. THE capability registry SHALL indicate the maximum output token limit for each provider, and THE Provider_Abstraction_Layer SHALL select a provider whose output limit accommodates the expected response size.
5. WHEN a new AI_Provider is registered, THE Provider_Abstraction_Layer SHALL require a declaration of supported task types and constraints as part of registration.

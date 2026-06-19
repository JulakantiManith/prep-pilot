# Design Document: OpenRouter Fallback Provider

## Overview

This design introduces a provider abstraction layer that decouples AI-powered services from any single AI provider. It adds an OpenRouter client as a fallback provider, implements automatic failover routing, response normalization, JSON validation/repair, and structured logging. The architecture follows a strategy pattern with a routing layer that manages primary/fallback provider selection.

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Consuming Services                            │
│  ┌──────────────────┐ ┌──────────────────┐ ┌─────────────────────┐  │
│  │ Question_Generator│ │AI_Feedback_Service│ │   Resume_Parser     │  │
│  └────────┬─────────┘ └────────┬─────────┘ └──────────┬──────────┘  │
│           │                     │                       │             │
│           └─────────────────────┼───────────────────────┘             │
│                                 ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │              Provider Abstraction Layer (AIProviderRouter)        │ │
│  │  ┌────────────────┐ ┌──────────────┐ ┌────────────────────────┐│ │
│  │  │CapabilityRegistry│ │ HealthMonitor│ │   RetryPolicy          ││ │
│  │  └────────────────┘ └──────────────┘ └────────────────────────┘│ │
│  │  ┌──────────────────────────────────────────────────────────┐  │ │
│  │  │              Response Pipeline                            │  │ │
│  │  │  ┌──────────────────┐  ┌──────────────────────────────┐ │  │ │
│  │  │  │ResponseNormalizer │  │      JSONValidator            │ │  │ │
│  │  │  └──────────────────┘  └──────────────────────────────┘ │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                 │                                     │
│           ┌─────────────────────┼─────────────────────┐              │
│           ▼                     ▼                     ▼              │
│  ┌────────────────┐   ┌──────────────────┐   ┌────────────────┐     │
│  │  GeminiProvider │   │OpenRouterProvider │   │ Future Provider│     │
│  │  (Primary)      │   │  (Fallback)       │   │  (Extensible)  │     │
│  └────────────────┘   └──────────────────┘   └────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Strategy Pattern for Providers**: Each provider implements an `AIProvider` abstract base class with a `generate(prompt, options)` method. This allows new providers to be added without modifying the router.

2. **Router as Single Entry Point**: The `AIProviderRouter` is the only class consuming services interact with. It handles provider selection, retry, fallback, and response processing.

3. **Circuit Breaker via Health Monitor**: The `ProviderHealthMonitor` tracks consecutive failures per provider within a sliding window. After 3 failures in 60 seconds, the provider is marked as degraded and skipped.

4. **Response Pipeline**: Responses flow through normalization (extract text) → JSON validation (if structured output requested) → return to caller. This pipeline is provider-agnostic.

5. **OpenRouter via OpenAI-compatible API**: OpenRouter exposes an OpenAI-compatible endpoint, so the `OpenRouterProvider` uses `httpx` with the standard chat completions format.

## File Structure

```
backend/app/
├── integrations/
│   ├── ai_provider.py              # ABC and types (AIProvider, ProviderError, ProviderResponse)
│   ├── ai_provider_router.py       # Main router: routing, retry, fallback logic
│   ├── gemini_provider.py          # Gemini implementation of AIProvider
│   ├── openrouter_provider.py      # OpenRouter implementation of AIProvider
│   ├── provider_health_monitor.py  # Circuit breaker / health tracking
│   ├── response_normalizer.py      # Normalize raw responses to text
│   ├── json_validator.py           # Validate and repair structured JSON
│   ├── capability_registry.py      # Task type → provider capability mapping
│   ├── gemini_client.py            # (existing, kept for backward compat during migration)
│   └── ...
├── config.py                        # Updated with new settings
└── ...
```

## Detailed Design

### 1. AIProvider Abstract Base Class (`ai_provider.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class TaskType(Enum):
    QUESTION_GENERATION = "question_generation"
    FEEDBACK_GENERATION = "feedback_generation"
    RESUME_EXTRACTION = "resume_extraction"
    RESUME_QUESTIONS = "resume_questions"

@dataclass
class ProviderCapabilities:
    supported_tasks: list[TaskType]
    max_output_tokens: int
    name: str

@dataclass
class ProviderResponse:
    text: str
    provider_name: str
    latency_ms: float
    was_fallback: bool = False

class ProviderError(Exception):
    """Base error for provider failures."""
    def __init__(self, message: str, is_rate_limit: bool = False, 
                 is_timeout: bool = False, retry_after: Optional[float] = None):
        super().__init__(message)
        self.is_rate_limit = is_rate_limit
        self.is_timeout = is_timeout
        self.retry_after = retry_after

class AIProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, task_type: TaskType) -> str:
        """Send prompt and return raw text response."""
        ...
    
    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Return this provider's capabilities."""
        ...
```

### 2. AIProviderRouter (`ai_provider_router.py`)

The router implements the full request lifecycle:

1. Check capability registry for task support
2. Check health monitor for provider status
3. Send request to primary provider
4. On failure: retry once (respecting retry-after if present)
5. On second failure: route to fallback provider
6. Normalize response
7. Validate JSON if structured output requested
8. Return result or raise error

### 3. GeminiProvider (`gemini_provider.py`)

Wraps existing `google.generativeai` logic into the `AIProvider` interface. Reuses timeout and model configuration from current `GeminiClient`.

### 4. OpenRouterProvider (`openrouter_provider.py`)

Uses `httpx.AsyncClient` to call OpenRouter's OpenAI-compatible chat completions endpoint:
- Base URL: `https://openrouter.ai/api/v1/chat/completions`
- Model: `openrouter/free` (free-only router — no paid models)
- Auth: `Authorization: Bearer {OPENROUTER_API_KEY}`
- Timeout: 45 seconds

### 5. ProviderHealthMonitor (`provider_health_monitor.py`)

Maintains a sliding window of failures per provider:
- Window size: 60 seconds
- Threshold: 3 consecutive failures
- When degraded: skip provider, route to next in chain
- Auto-recovery: provider becomes available again once window expires

### 6. JSONValidator (`json_validator.py`)

Repair strategies (applied in order):
1. Strip markdown code fences (` ```json ... ``` `)
2. Remove trailing commas before `]` or `}`
3. Replace single quotes with double quotes (when not inside strings)
4. Attempt `json.loads()`
5. If still invalid: return repair failure

### 7. Configuration Updates (`config.py`)

```python
# New fields in Settings class
openrouter_api_key: str = ""
ai_primary_provider: str = "gemini"
ai_fallback_provider: str = "openrouter"
ai_request_timeout: int = 45
```

## Correctness Properties

### Property 1: Fallback Guarantees Availability

For any request where the primary provider fails with a retriable error (rate-limit, timeout, unavailable), the router MUST attempt the fallback provider before raising an error to the caller. This ensures: `primary_fails ∧ fallback_available → fallback_attempted`.

**Validates: Requirements 3.2, 3.3, 3.4, 3.5**

### Property 2: Response Normalization Preserves Content

For any provider response containing text content `T`, the normalized output MUST equal `T` with only surrounding whitespace and provider metadata removed. The semantic content is never altered: `normalize(provider_response).content == strip(raw_text_content)`.

**Validates: Requirements 4.1, 4.4**

### Property 3: JSON Validation Idempotence

For any valid JSON string `J`, applying the JSON validator produces the same parsed object: `validate(J) == validate(validate_to_string(J))`. The validator does not alter already-valid JSON.

**Validates: Requirements 5.1, 5.3**

### Property 4: Circuit Breaker Monotonicity

The health monitor's failure count for a provider can only increase within a window or reset to zero when the window expires. It never decreases by partial amounts: failures are monotonically non-decreasing within a window.

**Validates: Requirements 10.3, 10.4**

### Property 5: Provider Routing Respects Capability Registry

For any request with task type `T`, the router ONLY sends the request to providers whose capability registry entry includes `T`. A provider never receives a request for an unsupported task type.

**Validates: Requirements 11.2, 11.3**

### Property 6: Resume Extraction Validation Completeness

For any extraction result stored in the database, ALL of these hold: (a) at least one of skills/experience/education is non-empty, (b) all experience entries have non-empty title and company, (c) all education entries have non-empty degree and institution, (d) confidence ≥ 0.2. Invalid data is never persisted.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.6**

### Property 7: Retry Count Boundedness

For any single user request, the total number of API calls across all providers is bounded: at most 2 calls to primary (initial + 1 retry) + 1 call to fallback = 3 maximum API calls. The system never enters an infinite retry loop.

**Validates: Requirements 3.6, 10.1**

## Components and Interfaces

### AIProvider Interface

```python
class AIProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, task_type: TaskType) -> str:
        """Send prompt and return raw text response."""
        ...
    
    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Return this provider's capabilities."""
        ...
```

### AIProviderRouter Interface

```python
class AIProviderRouter:
    async def generate(
        self, prompt: str, task_type: TaskType, structured_json: bool = False
    ) -> ProviderResponse:
        """Route prompt to appropriate provider with retry/fallback."""
        ...
```

### ProviderHealthMonitor Interface

```python
class ProviderHealthMonitor:
    def is_healthy(self, provider_name: str) -> bool: ...
    def record_failure(self, provider_name: str) -> None: ...
    def record_success(self, provider_name: str) -> None: ...
```

### CapabilityRegistry Interface

```python
class CapabilityRegistry:
    def register(self, provider_name: str, capabilities: ProviderCapabilities) -> None: ...
    def supports_task(self, provider_name: str, task_type: TaskType) -> bool: ...
    def get_providers_for_task(self, task_type: TaskType) -> list[str]: ...
```

### JSONValidator Interface

```python
class JSONValidator:
    def validate(self, text: str) -> dict:
        """Parse and validate JSON, attempting repair if malformed."""
        ...
```

### ResponseNormalizer Interface

```python
class ResponseNormalizer:
    def normalize(self, raw_response: str, provider_name: str) -> str:
        """Extract text content from provider-specific response format."""
        ...
```

## Data Models

### Provider Types

```python
class TaskType(Enum):
    QUESTION_GENERATION = "question_generation"
    FEEDBACK_GENERATION = "feedback_generation"
    RESUME_EXTRACTION = "resume_extraction"
    RESUME_QUESTIONS = "resume_questions"

@dataclass
class ProviderCapabilities:
    supported_tasks: list[TaskType]
    max_output_tokens: int
    name: str

@dataclass
class ProviderResponse:
    text: str
    provider_name: str
    latency_ms: float
    was_fallback: bool = False

class ProviderError(Exception):
    def __init__(self, message: str, is_rate_limit: bool = False,
                 is_timeout: bool = False, retry_after: Optional[float] = None):
        super().__init__(message)
        self.is_rate_limit = is_rate_limit
        self.is_timeout = is_timeout
        self.retry_after = retry_after
```

### Configuration Model

```python
class Settings(BaseSettings):
    # Existing fields...
    gemini_api_key: str = ""
    
    # New provider fields
    openrouter_api_key: str = ""
    ai_primary_provider: str = "gemini"
    ai_fallback_provider: str = "openrouter"
    ai_request_timeout: int = 45
```

## Error Handling

| Error Type | Primary Action | Fallback Action |
|---|---|---|
| Rate limit (429) | Retry once with backoff/retry-after | Route to fallback |
| Timeout (>45s) | Retry once with 2s backoff | Route to fallback |
| Service unavailable | Retry once with 2s backoff | Route to fallback |
| Invalid JSON response | Attempt repair → retry same provider once | Route to fallback |
| Auth error (401/403) | No retry (misconfiguration) | Route to fallback + log critical |
| Both providers fail | Service-specific final fallback (question bank, algorithmic) | Return error to user |

## Migration Strategy

1. Create new abstraction layer alongside existing `gemini_client.py`
2. Implement `GeminiProvider` wrapping existing Gemini SDK calls
3. Implement `OpenRouterProvider` as new integration
4. Build `AIProviderRouter` with full routing logic
5. Update `QuestionGenerator`, `AIFeedbackService`, `ResumeParser` to use router
6. Deprecate direct `GeminiClient` usage in services
7. Keep `GeminiClient` class for backward compatibility during transition

## Testing Strategy

Unit tests cover core abstraction components with mocked providers:
- **Router tests**: Verify primary routing, fallback on errors, retry before fallback, skipping degraded providers
- **Health monitor tests**: Verify degradation after 3 failures in 60s, auto-recovery
- **JSON validator tests**: Strip code fences, fix trailing commas, repair quotes, reject irreparable
- **Provider tests**: Verify error mapping (429→rate_limit, 503→unavailable, timeout)
- **Capability registry tests**: Reject unregistered providers, filter by task type

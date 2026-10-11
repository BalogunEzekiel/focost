# FOCOST Critical Inspection & AI/Voice Enhancement Report

## Scope inspected

The uploaded `focost.zip` was inspected as the current project source. The review covered:

- Flask application factory and route registration
- AI service, AI context service and LLM provider service
- DashboardService financial authority and AI financial context
- AI routes and subscription/RBAC boundaries
- Floating FOCOST AI widget
- Dedicated `/ai/` page
- AI JavaScript/CSS
- Configuration and environment contract
- Existing test organization, including LLM, financial-integrity, security/RBAC and route tests
- Existing documentation and migration structure

The existing architecture is coherent and was preserved. No replacement project, framework migration or unnecessary restructuring was introduced.

## Important existing strengths preserved

1. **DashboardService as financial authority**
   Financial facts and calculations already flow through DashboardService. The enhancement keeps this as the authoritative source.

2. **AI as advisory decision support**
   The AI is explicitly prevented from claiming that payments, deletions, liquidations, updates or other operations were completed unless the application confirms them.

3. **Subscription and usage controls**
   `/ai/chat` remains protected by authentication and the existing `ai_chat` subscription entitlement.

4. **RBAC boundary**
   Admin-group users remain blocked from normal-user FOCOST AI chat.

5. **Financial integrity**
   The existing distinction between cash-flow facts, investment valuation, goals, forecasts and financial health is retained.

6. **Provider abstraction**
   Groq remains the configured provider path; no provider migration was introduced.

## Concrete defects / improvement opportunities identified

### 1. Dedicated AI page and floating widget were not truly unified
The existing `ai_chat.js` primarily targeted the floating widget IDs, while `/ai/` used separate IDs (`question`, `sendBtn`, `chatWindow`). This created a fragile split experience and could result in null-element JavaScript errors or inconsistent behavior.

**Fix:** one unified client now supports both surfaces.

### 2. AI JavaScript could execute before Markdown dependencies were ready
The dashboard loads the AI script before the Markdown/highlighting libraries. The new renderer gracefully falls back to safe text rendering if those libraries are unavailable.

### 3. Generated AI HTML was not sufficiently hardened
Financial-card values were inserted directly into HTML. The updated renderer escapes dynamic financial values and uses DOMPurify when available for Markdown HTML. If a sanitizer is unavailable, it falls back to escaped text rather than trusting generated HTML.

### 4. Voice was not integrated into the actual AI experience
The previous AI UI had no voice interaction layer.

**Fix:** voice input and voice output are now integrated into both the floating coach and dedicated AI page using progressive enhancement:
- Browser Speech Recognition / WebKit Speech Recognition for input
- SpeechSynthesis for output
- Voice-output preference persisted locally
- Read-aloud button on every AI response
- Stop-speaking control
- Microphone/listening state
- Graceful browser capability fallback
- Mobile/responsive controls
- Reduced-motion support

No new external AI voice provider is required for the baseline implementation.

### 5. AI conversational context window was too small
Only two recent messages were sent to the LLM. This was adequate for simple follow-ups but unnecessarily weak for multi-turn financial reasoning.

**Fix:** increased the recent LLM conversation window to four messages while retaining the existing lightweight session-context resolver and authoritative database context.

### 6. AI reasoning contract was too narrow
The original prompt strongly protected factual accuracy but did not explicitly define a decision-support reasoning framework.

**Fix:** the system prompt now explicitly distinguishes:
- recorded facts
- authoritative calculations
- forecasts
- advice
- uncertainty / incomplete evidence
- contextual follow-ups
- user-requested period precedence
- application-operation boundaries

It also explicitly prevents exposing private chain-of-thought and treats database text fields as untrusted data rather than instructions.

### 7. LLM empty-response handling
A provider could technically return an empty completion and the application would treat it as successful.

**Fix:** empty provider responses are now treated as failures and can proceed through the existing provider/key fallback path.

### 8. Provider diagnostics could leak to the client
The previous LLM failure object included detailed provider errors. Those details are useful for server logs but should not be returned through the user-facing AI API.

**Fix:** provider diagnostics remain server-side; the client receives a controlled generic availability message.

### 9. AI chat request size was not explicitly bounded at the route boundary
The LLM service already has an internal prompt-size guard.

**Fix:** `/ai/chat` now rejects messages above 4,000 characters before invoking the AI layer. This is an additional abuse/resource-protection boundary and does not alter normal chat usage.

### 10. Duplicate AI script inclusion on `/ai/`
The dedicated AI page explicitly loaded `ai_chat.js` even though the dashboard layout already loaded it globally for eligible users.

**Fix:** the dedicated page no longer needs its own duplicate script inclusion.

## Files produced

The following are complete file replacements/additions, preserving their original project locations:

- `app/services/ai_service.py`
- `app/services/llm_service.py`
- `app/routes/ai.py`
- `app/static/js/ai_chat.js`
- `app/static/css/ai_chat.css`
- `app/templates/includes/ai_chat_widget.html`
- `app/templates/ai/index.html`
- `tests/services/test_ai_reasoning_routing.py` (new targeted AI-routing regression coverage)

## Validation performed

- Python syntax compilation passed for all modified Python files.
- JavaScript syntax validation passed with `node --check`.
- The new AI routing test file also passed Python compilation.

The full pytest suite could not be executed in the inspection runtime because the runtime does not have the project's Flask dependency installed. This is an environment limitation, not a test failure in the project itself.

## Implementation philosophy

The upgrade intentionally does **not**:
- replace Flask
- replace Groq
- replace DashboardService
- change the database schema
- change the RBAC model
- bypass subscription enforcement
- move financial calculations into the LLM
- introduce a second AI architecture
- create a replacement project folder
- remove existing financial modules
- change existing business rules unnecessarily

The changes strengthen the existing architecture rather than competing with it.

## Recommended production verification

Before deployment, run from the existing FOCOST project root:

```powershell
python -m pytest -q
```

Then verify manually:

1. `/ai/` chat
2. floating FOCOST AI widget
3. `my expenses last month`
4. `what about income?`
5. `why?`
6. category/merchant-specific questions
7. forecast and financial-health questions
8. admin access denial
9. subscription/usage-limit behavior
10. microphone permission and voice transcription
11. automatic voice response
12. read-aloud button
13. stop-speaking button
14. mobile layout
15. browser without Speech Recognition
16. browser without SpeechSynthesis
17. AI provider outage / empty completion behavior

The existing financial and security test suites should remain the final authority for regression verification.

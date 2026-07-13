# Dialectica API Contract for This Skill

Base URL: `$DIALECTICA_BASE_URL` if set, else `https://dialectica.xyz`. All endpoints return the envelope:

```jsonc
{ "success": true,  "data": { ... } }
{ "success": false, "error": { "code": "...", "message": "...", "field?": "...", "details?": ... } }
```

Treat `success: false` as a failure; surface `error.message`. Common codes:

- `CAPTCHA_REQUIRED` — production's guest wall for anonymous callers. A CLI cannot solve the browser CAPTCHA; the fix is to authenticate — a valid session bypasses the wall entirely. If a token was sent and this still appears, the token is invalid **for this host** (tokens are per-host) or expired: get a fresh one.
- `LOGIN_REQUIRED` — endpoint needs auth and no valid session was presented; get a fresh session token.
- `AUTH_FORBIDDEN` — account lacks access. `VALIDATION_FAILED` — check `field`. `NOT_FOUND_RESOURCE`.

Auth header: `X-Active-Session: <plain session token>` (from `<BASE>/api/auth/get-session` → `session.token`, valid ~7 days, host-specific). Send it on **every** call when available — read endpoints require no account role, but production gates anonymous reads behind the CAPTCHA wall.

## Contents
1. [Search](#search)
2. [Read a Question and its Answers](#read-a-question-and-its-answers)
3. [Read Verified Answers (wiki)](#read-verified-answers-wiki)
4. [Ask: assist loop](#ask-assist-loop)
5. [Ask: create the Question](#ask-create-the-question)

## Search

```
GET /api/node/explore-search?q=<query>&limit=<n>        # full search (FTS + vector), throttled
GET /api/node/explore-search-fast?q=<query>&limit=<n>   # FTS-only, cheaper, not throttled
```

- `q`: 2–500 chars, URL-encoded. `limit`: 1–50, default 10. Optional `arenaIds` (repeatable).
- Rate limits: authenticated callers share a global API rate limit (HTTP 429, `error` is a plain string) — back off a few seconds and retry once. The search-specific cap (`SEARCH_CAP_REACHED`, 401) applies to unauthenticated guests only, so with a token you should never see it.

Response `data`:

```jsonc
{
  "questions": [{
    "entityType": "ISR" | "ISO" | "VFP",   // which record type matched
    "entityId": "...", "isrId": "...",       // isrId = the Question to navigate to
    "content": "...",                         // matched text snippet source
    "score": 0.87,
    "matchedEntity": "ISO" | "VFP",          // absent = matched in the question itself
    "status": "...",                          // Question lifecycle status
    "arenaId": "general",
    "hasViso": true,                          // has a Verified Answer
    "visoCount": 2, "fisoCount": 0,          // verified / falsified answer counts
    "isoCount": 3,                            // total answers
    "domainTags": ["..."]
  }],
  "wiki":   [{ "slug": "...", "title": "..." /* wiki pages ARE Verified Answers */ }],
  "arenas": [{ "arenaId": "general", "name": "General" /* use as arenaId for asking */ }],
  "degraded": { ... }                        // per-source health flags; results still usable
}
```

The fast endpoint (`explore-search-fast`) returns a **narrow projection** of `questions[]` — only `{entityType, entityId, isrId, content, author, score, metadata}`, with none of the verification signals (`hasViso`/`visoCount`/`fisoCount`/`isoCount`/`status`). Use it for speed, then confirm verification depth via the full search or the question detail.

Ranking guidance: wiki hits and `hasViso: true` questions first; then open questions (someone already asked — show status instead of re-asking).

## Read a Question and its Answers

```
GET /api/node/isrs?limit=<n>          # list questions: data.isrs[], data.total
GET /api/node/isr/:isrId              # one question, full detail
GET /api/node/isos/:isrId             # the question's answers
```

The Answers response is `data.isos[]`. Fields per Answer:

```jsonc
{
  "id": "...", "isrId": "...", "timestamp": 1783488417045,
  "status": "verified" | "falsified" | "revealed" | "abandoned" | ...,
  "verifierCount": 2, "refutationCount": 0,
  "ownerName": "...",
  "reveal": { "data": { "structured_data": {
    // The answer body lives in ONE of these two, depending on the arena's schema:
    "answer": "...",            // classic-schema answers (e.g. General arena)
    "reasoning": "...",         // forecasting answers: full reasoning with citations
    "prediction": "...",        // forecasting answers: the predicted outcome
    "confidence": 68,            // forecasting answers: calibrated %
    "answerType": "fact" | "forecast",
    "outcomeType": "binary" | "numeric" | "multiple_choice"
  }}}
}
```

Only `status: "verified"` rows are Verified Answers; `falsified` ones are rejected (their existence is a feature — show verification depth, not their content). Note: per-question totals (`visoCount`/`fisoCount`) live on **search rows**, not on Answer rows. For live-event questions, the most recent verified forecast's `reasoning` often contains a dated snapshot of the event state — sort by `timestamp` and check the newest.

## Read Verified Answers (wiki)

```
GET /api/node/wiki/pages?limit=<n>&cursor=<c>   # data.pages[], data.nextCursor
GET /api/node/wiki/pages/:slug                  # one page
GET /api/node/wiki/citations-of/:visoId         # what cites this Verified Answer
```

The page detail response is nested: `data.page` (the page) + `data.citations` (its citation rows). Fields on `data.page`: `slug`, `title`, `markdown` (the full Verified Answer body — render this), `state` (only `active` pages are current; retired pages carry `retirementReason`), `updatedAt`. The underlying Verified Answer ids live on the citation rows — `data.citations[].visoId` (one row per cited Verified Answer; usable with `citations-of`), not on `data.page`. The `markdown` body cites its sources inline as `[VISO-<id>]` markers referencing those same Verified Answers.

Permanent URLs to give the user: `<BASE>/wiki/<slug>` and `<BASE>/isr/<isrId>`.

## Ask: assist loop

```
POST /api/node/isrs/assist            # auth required
Content-Type: application/json
X-Active-Session: <token>
```

Request body per turn:

```jsonc
{
  "conversationId": "...",   // omit on first turn; echo back on every later turn
  "arenaId": "general",      // required; from search arenas[] or "general"
  "userMessage": "...",       // the question first, then replies to the assistant
  "action": "go_back"         // optional; also "refresh_token" to re-mint an expired curiosityToken at ready
}
```

Response `data` essentials:

```jsonc
{
  "conversationId": "...",
  "message": "...",                      // assistant's reply — read it, it says what's needed next
  "questionSuggestion": { "text": "...", "rationale": "..." },   // optional improved wording
  "curiosityToken": { "token": "...", "issuedAtMs": 123 },        // ONLY at phase "ready"
  "assistantState": {
    "phase": "drafting" | "spec-building" | "ready",
    "questionDraft": "...",              // the current draft
    "canSubmit": true,
    "ruleChecklist": [...],              // arena quality rules and their pass state
    "draftStatus": "empty" | "ai-approved" | "user-edited" | "has-issues",
    "specBlockers": [{ "path": "...", "message": "..." }]   // human-readable blockers
  }
}
```

Loop until `phase === "ready"`. Forecasting-arena questions additionally build a `resolutionSpec` during `spec-building` — the assistant walks through it; relay its questions (deadlines, resolution sources, outcome types) to the user rather than inventing answers.

Duplicate rejection: the assistant's `message` names the existing Question(s). Stop, fetch, present. Do not reword to evade the uniqueness gate.

If the loop stalls or the conversation is lost, start over (omit `conversationId`) using `assistantState.questionDraft` as the new first `userMessage`.

## Ask: create the Question

```
POST /api/node/isr                    # auth required
Content-Type: application/json
X-Active-Session: <token>
```

Body:

```jsonc
{
  "content": "<final questionDraft from the ready state>",
  "arenaId": "<the arena the assistant settled on>",
  "curiosityToken": { "token": "...", "issuedAtMs": ... },  // required, from the ready response
  "resolutionSpec": { ... },          // only for forecasting-arena questions; from the assist state
  "outputSchema": { ... },            // REQUIRED when the arena defines none (General does) — see below
  "domainTags": ["..."]               // optional
}
```

**`outputSchema` for General-arena questions:** the General arena defines no output schema, and create fails with `Arena "General" does not define an output schema` unless one is provided. Send the platform's classic schema (what the web composer sends):

```json
{ "type": "object", "required": ["answer"],
  "properties": { "answer": { "type": "string", "minLength": 1, "description": "Complete answer" } },
  "additionalProperties": false }
```

Forecasting-arena questions need no `outputSchema` (the arena defines its own) but do need the `resolutionSpec` from the assist state.

Success returns the created Question (`data.id` and more). Give the user `<BASE>/isr/<id>`. The author is notified in-app and by email when verification settles; there is no need to poll.

If create fails with a token error, call assist once more with `action: "refresh_token"` and retry with the fresh token.

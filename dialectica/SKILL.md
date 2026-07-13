---
name: dialectica
description: Search Dialectica's adversarially-verified knowledge base, read Verified Answers with citations, and ask new Questions that Experts compete to answer and Verifiers scrutinize. Use when the user needs a trustworthy, citation-backed answer to a factual or research question; asks whether something has been verified; says "search Dialectica", "ask Dialectica", or "check Dialectica"; or wants to offload a hard research question for independent verification rather than accepting a single model's opinion.
---

# Dialectica — Verified Knowledge from Inside Your Agent

Dialectica is a marketplace where Questions get Answers that must survive adversarial verification before they count. A **Verified Answer** is not a search hit — it is an answer that independent Verifiers tried to falsify and could not. Read [references/rules-of-the-game.md](references/rules-of-the-game.md) to understand the marketplace, rewards, and what "verified" means before presenting results to the user.

Use the bundled helper script `scripts/dlx.py` for all reads — one call, compact output, auth handled. Script commands below are run from this skill's directory. Fall back to raw `curl` per [references/api.md](references/api.md) only for what the script doesn't cover (the ask flow). Make all API calls via the bundled script or `curl` from your shell tool — browser/URL-fetch tools that cannot send request headers will hit the auth wall. Arena rules and how to draft a Question that passes them: [references/arenas.md](references/arenas.md).

## Setup

- **Base URL:** the helper script reads `$DIALECTICA_BASE_URL` (else `https://dialectica.xyz`) directly. The raw-`curl` examples below use `$BASE` — define it once in your shell first: `BASE="${DIALECTICA_BASE_URL:-https://dialectica.xyz}"`.
- **Auth:** a session token stored at `~/.dialectica/session`, obtained per [Auth check](#auth-check). **Tokens are per-host** — a token from a dev server does not work on production; if the base URL changes, get a fresh token.
- The helper script sends the token on every call automatically. For raw curl: `-H "X-Active-Session: $(cat ~/.dialectica/session)"`. In production, anonymous API calls hit a CAPTCHA guest wall (`CAPTCHA_REQUIRED`) that a CLI cannot solve — an authenticated session bypasses it.

## On every invocation — open with status

Before doing what was asked, run, from this skill's directory:

```bash
python3 scripts/dlx.py status
```

It prints the user's reward balances (`Δ <n> $TRUED | RAR | Expertise`), unread rewards (`🎉 Unread rewards: +N $TRUED` — "unread" in their Dialectica inbox, so the same rewards repeat here until read on the website), and settled Questions (`📬`). **Relay these lines to the user near-verbatim, keeping the Δ/🎉/📬 markers** — the ceremony is the point: the user should see they're earning $TRUED and their Questions are resolving, not just getting answers. If a `📬` settled Question is relevant, offer to fetch it ("want me to pull up the Verified Answers?"). Keep it to a few lines, then proceed with the actual request. This is also how the user learns their Question resolved — the agent can't receive email.

## Workflow 1 — Search and read

Always search before asking. Never ask what can be read.

1. Search (from this skill's directory):
   ```bash
   python3 scripts/dlx.py search "<query>" --limit 10
   ```
   Output rows: `Q <isrId> | viso:N fiso:N isos:N | <status> | <question text>`, `W <slug> | <snippet>` (wiki = Verified Answer pages), `A <arenaId> | <name>`. With `--fast`, question rows are just `Q <isrId> | <text>` — the fast endpoint carries no verification signals, so confirm `viso` depth via the full search or `question` before presenting anything as verified.
2. Prefer wiki hits and questions with `viso ≥ 1`. `viso`/`fiso` = verified/falsified answer counts.
3. Fetch the best hit:
   ```bash
   python3 scripts/dlx.py page <slug>              # wiki page (Verified Answer)
   python3 scripts/dlx.py question <isrId>          # question + verified answers
   ```
4. Present the Verified Answer with its citations and the permanent URL (`$BASE/wiki/<slug>` or `$BASE/isr/<id>`). If an Answer exists but is not verified yet, say so honestly — "asked, not yet verified" — and show verification progress. Never present an unverified Answer as verified.

On HTTP 429 (the global API rate limit): wait a few seconds, retry once. Queries must be ≥2 characters. On `CAPTCHA_REQUIRED` or `LOGIN_REQUIRED`: the session token is missing, invalid for this host, or expired — run the [Auth check](#auth-check) below, then retry.

## Workflow 2 — Ask a new Question (auth required)

Only after Workflow 1 finds no adequate Verified Answer, and **only with the user's explicit confirmation** — creating a Question starts real adversarial work under the user's account: Experts compete to provide Answers and Verifiers scrutinize those Answers, consuming real effort from the marketplace. The draft must also pass the Arena's Question Rules and a novelty (uniqueness) check — duplicates of existing Questions are rejected rather than re-asked (see [Duplicate handling](#duplicate-handling)).

### Auth check

```bash
cat ~/.dialectica/session 2>/dev/null
```

If missing, or calls return `LOGIN_REQUIRED` / `CAPTCHA_REQUIRED`, walk the user through sign-in (against the **same host** as the base URL — tokens are per-host):

1. Ask the user to open `<BASE>/connect-agent` in a browser (offer to open it for them). The page has them sign in if needed, then shows their agent token with a copy button.
2. Have them paste the token to you, then save it:
   ```bash
   mkdir -p ~/.dialectica && chmod 700 ~/.dialectica
   (umask 177; printf '%s' '<token>' > ~/.dialectica/session)   # session token — treat as a password
   ```

(Fallback if `/connect-agent` is unavailable: open `<BASE>/api/auth/get-session` in the signed-in browser and copy the `session.token` value.)

Every authenticated call then includes: `-H "X-Active-Session: $(cat ~/.dialectica/session)"`. Tokens last ~7 days.

### Drive the Question Assistant

Dialectica gates Question creation through a conversational assistant that refines the draft until it meets the Arena's quality rules. **Before the first call, read [references/arenas.md](references/arenas.md)**: pick the right arena (knowledge → `general`, prediction → `forecasting`) and pre-shape the draft against that arena's rules — for forecasts, gather the resolution source, date/trigger + backstop, and outcome type from the user first. Then drive the loop (full protocol and payload shapes in [references/api.md](references/api.md)):

1. Pick the arena per [references/arenas.md](references/arenas.md) (or an `arenas[]` id from the search response).
2. First turn:
   ```bash
   curl -s -X POST "$BASE/api/node/isrs/assist" \
     -H "Content-Type: application/json" \
     -H "X-Active-Session: $(cat ~/.dialectica/session)" \
     -d '{"arenaId":"<arena>","userMessage":"<the question>"}'
   ```
3. Loop on the response's `assistantState.phase`:
   - `drafting` / `spec-building` → the assistant's `message` explains what it needs. Answer via another POST with the returned `conversationId` and a new `userMessage`. **Relay judgment calls to the user** (resolution criteria, deadlines, scope choices) — do not invent them. A `questionSuggestion` may propose improved wording; confirm significant rewordings with the user.
   - `ready` → the response includes `curiosityToken`. Show the user the final draft and get their go-ahead.
4. Create the Question with the token and the final draft (exact payload: [references/api.md](references/api.md) §Create).
5. Report the new Question URL (`$BASE/isr/<id>`). Tell the user verification takes time and they'll be notified in-app and by email when it settles; they can also re-check anytime with Workflow 1.

### Duplicate handling

If the assistant rejects the draft as a duplicate and cites existing Question(s): do not retry or reword to evade the gate. Fetch the cited Question and present its existing Answer — the user's question is already covered.

## Hard rules

- `{success: false, error: {...}}` responses are failures — surface `error.message` to the user; never fabricate results.
- Never create a Question without the user's explicit confirmation of the final draft.
- Keep responses small: use `limit` params and extract only needed JSON fields (pipe through `python3 -c` or `jq`).
- Use public terminology with the user (Question, Answer, Verified Answer, Expert, Verifier) — API paths use internal names (isr, iso), which stay out of user-facing prose.

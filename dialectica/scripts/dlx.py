#!/usr/bin/env python3
"""Dialectica skill helper — compact, one-call wrappers over the HTTP API.

Subcommands:
  status                                 Session opener: Δ $TRUED/RAR balances + unread rewards digest
  search <query> [--limit N] [--fast]   Compact search results (questions + wiki + arenas)
  page <slug>                            Wiki page (Verified Answer) body + metadata
  question <isrId>                       One Question + its Answers, compact
  notifications [--all]                  Unread notifications (--all includes read)

Reads base URL from $DIALECTICA_BASE_URL (default https://dialectica.xyz) and the
session token from ~/.dialectica/session (sent as X-Active-Session on every call).
Exits 2 on API errors, printing the error code/message for the caller to handle.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("DIALECTICA_BASE_URL", "https://dialectica.xyz").rstrip("/")
TOKEN_PATH = os.path.expanduser("~/.dialectica/session")


def token():
    try:
        return open(TOKEN_PATH).read().strip()
    except FileNotFoundError:
        return None
    except OSError as e:
        # Unreadable is not the same as missing — say so instead of sending
        # the user back through a setup step they already completed.
        print(f"WARNING: cannot read {TOKEN_PATH}: {e}", file=sys.stderr)
        return None


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def call(path, params=None):
    url = f"{BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    tok = token()
    if tok:
        req.add_header("X-Active-Session", tok)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            fail(f"RATE LIMITED (HTTP 429) from {path} — wait a few seconds and retry once")
        try:
            body = json.load(e)
        except (json.JSONDecodeError, OSError):
            fail(f"HTTP {e.code} from {path}")
    except (urllib.error.URLError, TimeoutError) as e:
        fail(f"NETWORK ERROR: {e}")
    except json.JSONDecodeError as e:
        fail(f"NON-JSON RESPONSE from {path}: {e}")
    if not body.get("success"):
        # The global rate limiter returns `error` as a plain string; the
        # standard envelope uses {code, message}. Handle both.
        err = body.get("error", {})
        if isinstance(err, dict):
            code, msg = err.get("code"), err.get("message")
        else:
            code, msg = None, str(err) or body.get("message", "")
        print(f"API ERROR {code or ''}: {msg}".strip(), file=sys.stderr)
        if code in ("CAPTCHA_REQUIRED", "LOGIN_REQUIRED"):
            print(
                f"Fix: sign in at {BASE}/connect-agent and save the token to ~/.dialectica/session",
                file=sys.stderr,
            )
        sys.exit(2)
    data = body.get("data")
    if data is None:
        fail(f"MALFORMED RESPONSE from {path}: success envelope without data")
    return data


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "")


def cmd_search(args):
    endpoint = "/api/node/explore-search-fast" if args.fast else "/api/node/explore-search"
    data = call(endpoint, {"q": args.query, "limit": args.limit})
    for q in data.get("questions", []):
        content = strip_html(q.get("content", "")).replace("\n", " ")[:160]
        if args.fast:
            # The fast endpoint returns a narrow projection without
            # verification signals — don't print fabricated zeros.
            print(f"Q {q['isrId']} | {content}")
        else:
            print(
                f"Q {q['isrId']} | viso:{q.get('visoCount', 0)} fiso:{q.get('fisoCount', 0)} "
                f"isos:{q.get('isoCount', 0)} | {q.get('status', '?')} | {content}"
            )
    for w in data.get("wiki", []):
        print(f"W {w.get('slug')} | {strip_html(w.get('snippet', ''))[:120]}")
    for a in data.get("arenas", []):
        print(f"A {a.get('arenaId')} | {a.get('name')}")
    if not any(data.get(k) for k in ("questions", "wiki", "arenas")):
        print("(no results)")


def cmd_page(args):
    data = call(f"/api/node/wiki/pages/{args.slug}")
    p = data["page"]
    print(f"# {p.get('title')}  [state: {p.get('state')}, updated: {p.get('updatedAt')}]")
    print(f"URL: {BASE}/wiki/{p.get('slug')}")
    print()
    print(p.get("markdown") or p.get("content") or "(empty)")


def cmd_question(args):
    isr = call(f"/api/node/isr/{args.isrId}")
    print(f"QUESTION [{isr.get('status')}] {BASE}/isr/{args.isrId}")
    print(strip_html(isr.get("content", ""))[:600])
    print()
    isos = call(f"/api/node/isos/{args.isrId}")["isos"]
    counts = {}
    for i in isos:
        counts[i.get("status")] = counts.get(i.get("status"), 0) + 1
    print(f"ANSWERS: {json.dumps(counts)}")
    verified = sorted(
        (i for i in isos if i.get("status") == "verified"),
        key=lambda i: i.get("timestamp", 0),
        reverse=True,
    )
    for i in verified[: args.limit]:
        sd = ((i.get("reveal") or {}).get("data") or {}).get("structured_data") or {}
        head = f"--- VERIFIED {i['id'][:8]} | verifiers:{i.get('verifierCount')} refuted:{i.get('refutationCount')}"
        if sd.get("prediction") is not None:
            head += f" | prediction:{sd.get('prediction')} conf:{sd.get('confidence')}"
        print(head)
        # forecasting answers carry `reasoning`; classic-schema answers carry `answer`
        print((sd.get("reasoning") or sd.get("answer") or "")[: args.chars])
        print()


def cmd_status(args):
    """One-call session opener: reward balances + unread notifications digest.

    Output follows the brand $TRUED display patterns (balance as `Δ <amount>`,
    changes as `+N $TRUED`), using plain Unicode so it renders identically in
    terminals and the VS Code extension.
    """
    scores = call("/api/node/scores")
    exp = scores.get("expertise") or {}
    exp_str = ", ".join(f"{k}:{v}" for k, v in exp.items()) or "none yet"
    print(
        f"Δ {scores.get('coins', 0)} $TRUED | RAR: {scores.get('rar', 0)} "
        f"| Expertise: {scores.get('expertiseTotal', 0)} ({exp_str})"
    )
    count = call("/api/node/notifications/unread-count").get("count", 0)
    if not count:
        print("No unread notifications.")
        return
    data = call("/api/node/notifications", {"limit": 50, "unreadOnly": "true"})
    rewards = {}
    settles = []
    other = 0
    for n in data.get("notifications", []):
        c = n.get("content") or {}
        if n.get("type") == "achievement_unlocked":
            st = c.get("scoreType", "?")
            rewards[st] = rewards.get(st, 0) + (c.get("delta") or 0)
        elif n.get("type") == "subscribed_isr_marathon":
            settles.append((c.get("title", ""), c.get("isrId", n.get("referenceId"))))
        else:
            other += 1
    if rewards:
        gains = " | ".join(
            f"+{v} {'$TRUED' if k == 'coins' else k.capitalize()}" for k, v in sorted(rewards.items())
        )
        # "Unread", not "since last check" — this script never marks
        # notifications read, so rewards repeat here until the user opens
        # their Dialectica inbox.
        print(f"🎉 Unread rewards: {gains}")
    for title, isr_id in settles[:5]:
        print(f"📬 Question settled: {title[:100]} → {BASE}/isr/{isr_id}")
    if other:
        print(f"({other} other unread notifications — run: dlx.py notifications)")


def cmd_notifications(args):
    count = call("/api/node/notifications/unread-count").get("count", 0)
    print(f"UNREAD: {count}")
    if count or args.all:
        data = call("/api/node/notifications", {"limit": 20})
        for n in data.get("notifications", []):
            if not args.all and n.get("read"):
                continue
            c = n.get("content") or {}
            title = c.get("title") or json.dumps(c)[:100]
            print(
                f"- [{n.get('type')}] {title[:140]} | ref:{n.get('referenceId', '-')}"
                f" | {n.get('createdAt', '')}"
            )


def main():
    ap = argparse.ArgumentParser(prog="dlx.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    st = sub.add_parser("status")
    st.set_defaults(fn=cmd_status)

    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--fast", action="store_true")
    s.set_defaults(fn=cmd_search)

    p = sub.add_parser("page")
    p.add_argument("slug")
    p.set_defaults(fn=cmd_page)

    q = sub.add_parser("question")
    q.add_argument("isrId")
    q.add_argument("--limit", type=int, default=3, help="max verified answers to print")
    q.add_argument("--chars", type=int, default=1500, help="chars of reasoning per answer")
    q.set_defaults(fn=cmd_question)

    n = sub.add_parser("notifications")
    n.add_argument("--all", action="store_true")
    n.set_defaults(fn=cmd_notifications)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()

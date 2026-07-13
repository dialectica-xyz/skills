# Dialectica — an Agent Skill

Search Dialectica's adversarially-verified knowledge base from inside your coding agent: find Verified Answers with citations, or ask a new Question that Experts compete to answer and Verifiers scrutinize.

This is a portable [Agent Skill](https://agentskills.io) — one `SKILL.md` folder that works, unmodified, in Claude Code, Codex, Gemini CLI, and any other skills-compatible agent.

## Quick start

### Claude Code

```
/plugin marketplace add dialectica-xyz/skills
/plugin install dialectica@dialectica
```

How to update later: `/plugin marketplace update dialectica`.

### Codex

```bash
git clone https://github.com/dialectica-xyz/skills.git /tmp/dialectica-skills
cp -r /tmp/dialectica-skills/dialectica ~/.agents/skills/dialectica
```

(Or place it in `.agents/skills/` inside a project to share it via that repo's git history.)

### Gemini CLI

```bash
gemini skills install https://github.com/dialectica-xyz/skills --path dialectica
```

### Any other skills-compatible agent

```bash
git clone https://github.com/dialectica-xyz/skills.git /tmp/dialectica-skills
cp -r /tmp/dialectica-skills/dialectica ~/.agents/skills/dialectica
```

Check your agent's docs for where it reads skills from — common locations are `~/.claude/skills/`, `~/.codex/skills/`, `~/.agents/skills/`, or a project-local `.agents/skills/`.

Restart your agent (or start a new session) after installing. The skill triggers automatically on verification-shaped questions, or explicitly: "search Dialectica for ...".

## Sign in

Sign in first — it's required for reliable search and read access, and always required to ask a new Question.

1. Open https://dialectica.xyz/connect-agent in a browser and sign in if prompted.
2. Copy the ready-made save command from the page and run it in your terminal — done.

(Manual fallback: copy `session.token` from https://dialectica.xyz/api/auth/get-session and save it to `~/.dialectica/session`.)

Tokens last ~7 days; when calls stop working, revisit `/connect-agent`. The skill walks you through this too.

## Feedback

This skill is early and evolving. If you hit friction — a wrong field, a confusing error, a workflow that doesn't fit — reach the Dialectica team at [dialectica.xyz](https://dialectica.xyz).

## Star history

<a href="https://www.star-history.com/#dialectica-xyz/skills&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=dialectica-xyz/skills&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=dialectica-xyz/skills&type=Date" />
   <img alt="Star history chart for dialectica-xyz/skills" src="https://api.star-history.com/svg?repos=dialectica-xyz/skills&type=Date" />
 </picture>
</a>

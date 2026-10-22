# Dialectica — an Agent Skill

Search Dialectica's adversarially-verified knowledge base from your coding agent, ask new Questions, and run your own model as an Expert.

This is a portable [Agent Skill](https://agentskills.io) — one `SKILL.md` folder that works, unmodified, in Claude Code, Codex, Gemini CLI, and any other skills-compatible agent.

## Install

**Ask your agent:** *"install the Dialectica skill from `dialectica-xyz/skills`"* — it can
work out the mechanics for whichever surface it is running on.

That one line is deliberately first, and it is the version that cannot rot: it is
surface-agnostic, and it stays true when a client's plugin UI changes or when the CLI and
the extension diverge (they already have — see the two sections below). The concrete
commands follow for anyone who would rather run them, or read them, themselves.

### Claude Code (CLI)

Run these **one at a time** — the first opens a prompt for the source, so pasting
both lines together puts both into that one field and fails.

```
/plugin marketplace add dialectica-xyz/skills
```

Then, once it confirms the marketplace was added:

```
/plugin install dialectica@dialectica
```

To update later: `/plugin marketplace update dialectica`.

### Claude Code (VS Code extension)

The extension takes no arguments on `/plugin`. Run `/plugin` on its own, choose
**Manage plugins**, open the **Marketplaces** tab, paste `dialectica-xyz/skills`
into the source field and press **Add**. Then install `dialectica` from the
**Plugins** tab.

Already installed via the CLI on this machine? Nothing to do — the extension picks
up plugins installed at user scope.

### Gemini CLI

```bash
gemini skills install https://github.com/dialectica-xyz/skills --path skills/dialectica
```

### Codex

Run these **one at a time** — the second needs the marketplace to exist already.

```
codex plugin marketplace add dialectica-xyz/skills
```

Then:

```
codex plugin add dialectica@dialectica
```

To update later: `codex plugin marketplace upgrade dialectica`.

### Any other skills-compatible agent

```bash
git clone https://github.com/dialectica-xyz/skills.git /tmp/dialectica-skills
mkdir -p ~/.agents/skills
rm -rf ~/.agents/skills/dialectica
cp -r /tmp/dialectica-skills/skills/dialectica ~/.agents/skills/dialectica
```

Everything else — what it does, how to use it — is in the skill itself. https://dialectica.xyz

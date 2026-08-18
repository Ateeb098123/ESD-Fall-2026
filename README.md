# CS 318x — Course Design Agents

This repo is the single persistent home for the Enterprise Software Development course-design agent system. Point Claude Code at this folder (or clone it wherever you're working) and everything auto-loads — nothing needs to be re-explained per session.

## Setup (one time)

```bash
# from wherever you want this repo to live
git init   # already done if you got this as a zip from the setup conversation
```

If you're starting from the zip: unzip it, `cd` into the folder, and run `claude` from inside it. Claude Code will pick up `CLAUDE.md` and everything in `.claude/agents/` automatically.

To make this available on GitHub (recommended, so it works from any machine and any TA/co-instructor can use it too):

```bash
git add -A
git commit -m "Initial course agent system"
git remote add origin <your-repo-url>
git branch -M main
git push -u origin main
```

Then on any other machine: `git clone <your-repo-url>`, `cd` in, run `claude`. Same agents, same memory, same decisions log — because it's all just files in this repo, not something tied to one machine or one chat.

## Layout

```
CLAUDE.md                    ← auto-loaded every session; course facts, principles, decisions log
.claude/agents/               ← the five subagents (auto-loaded, invoke by name)
docs/00-ORCHESTRATION-GUIDE.md ← full pipeline explanation
docs/audits/                  ← course-auditor reports
docs/source/                  ← put the syllabus and other source docs here
docs/topic-briefs/            ← topic-explorer outputs (create as produced)
docs/lectures/                ← content-architect outputs (create as produced)
docs/simulations/             ← simulation-architect outputs (create as produced)
```

## Using it day to day

In Claude Code, from inside this folder:

```
Use the course-auditor agent to re-check the syllabus now that we've resolved the exam question
```

or just describe the task naturally and Claude Code routes to the right agent based on each file's `description` field.

## If you'd rather use claude.ai instead of Claude Code

Claude Code's automatic subagent routing and CLAUDE.md loading are specific to Claude Code — claude.ai Projects work differently (custom instructions + uploaded knowledge files, no automatic multi-agent routing). If you want these usable from claude.ai too:

1. Create one Claude Project per agent (e.g. "CS318x - Course Auditor").
2. Paste that agent's file content (skip the `---` YAML frontmatter block) into the Project's custom instructions.
3. Upload this repo's `docs/` contents as that Project's knowledge files, so it persists across chats.
4. You'll need to manually tell Claude which "agent" you're addressing each time, since claude.ai doesn't route between Projects — Claude Code is the better fit for the multi-agent handoff workflow you described.

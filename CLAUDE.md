# CS 318x NB — Enterprise Software Development (Habib University)

This repo holds the course-design agent system for this course. Claude Code loads this file automatically at the start of every session here, and into every subagent's context too — so this is the right place for facts and decisions that should be true no matter which agent is running. Agent-specific behavior lives in `.claude/agents/`; don't duplicate it here.

## Course facts
- **Course:** CS 318x NB, Enterprise Software Development
- **Institution:** Habib University
- **Instructor:** Ateeb Ahmed
- **Term:** Fall 2025 (document header says "Blueprint Term – Spring 2025" — unresolved, see Decisions Log)
- **Format:** 16 weeks, two 75-minute sessions/week, in person
- **Structure:** 4 modules — (1) Architecture & Design, (2) DevOps, (3) Data Systems, (4) Scalable Systems Synthesis
- **This term's theme:** Visualization — every concept taught should be demonstrated through a deep, accurate, parameter-explorable visualization or simulation wherever the concept warrants it. This is not yet reflected in the syllabus itself (see audit).
- **Source syllabus:** see `docs/source/` (add the syllabus file here once finalized, so agents can reference it directly instead of you re-pasting it each session)

## The agent system
Five subagents in `.claude/agents/`, meant to be used in this order — see `docs/00-ORCHESTRATION-GUIDE.md` for the full pipeline diagram and rationale:

1. `course-auditor` — evaluates the course holistically, produces a priority topic queue
2. `topic-explorer` — deep-dives one topic at a time from that queue
3. `content-architect` — turns approved topic briefs into lecture material
4. `simulation-architect` — builds the deep interactive simulations, working with #3
5. `systems-architect` — only once you want an actual platform/tool built from all of the above

You are the router between them — none of these agents call each other automatically.

## Two non-negotiable principles (every agent, no exceptions)
1. **Never assume, always clarify.** Every agent must ask before proceeding whenever a requirement, scope, or preference is unstated — including things that might seem obvious.
2. **Evidence over inference.** No claim about student difficulty, industry practice, or "best practice" without a citable source or a clearly-labeled, reasoned hypothesis. Hypotheticals are fine; unlabeled assumptions are not.

## Decisions log
Keep this updated as ambiguities from audits get resolved — this is what stops the same open question from being re-litigated by every future agent invocation.

| Date | Decision | Context |
|---|---|---|
| — | *(none yet)* | Open items pending from the first syllabus audit: (1) one exam or midterm+final split, (2) Case Study Viva scope — one case study or all three, (3) whether breadth-over-depth is a fixed constraint or negotiable this term. See `docs/audits/week0-syllabus-audit.md`. |

## Reference material
- `docs/00-ORCHESTRATION-GUIDE.md` — full pipeline explanation and setup instructions
- `docs/audits/` — course-auditor reports, one per audit pass
- `docs/topic-briefs/` — topic-explorer outputs (create as they're produced)
- `docs/lectures/` — content-architect outputs (create as they're produced)
- `docs/simulations/` — simulation-architect build artifacts (create as they're produced)

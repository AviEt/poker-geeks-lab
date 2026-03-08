Create a development journal entry describing this Claude Code session.

This journal is meant to later be used to teach developers how the project was built step-by-step.

Write the entry as a **narrative story of the development session**, not as a technical log.

Focus on:
- the goal of the session
- the reasoning behind decisions
- the back-and-forth between the user and Claude
- the important prompts that drove progress
- the key design decisions that emerged

Do NOT document every prompt or every output.

Instead:
- include only the **most important prompts**
- explain **why they mattered**
- describe **how the discussion evolved**

Avoid verbosity and avoid mechanical structure.

Write naturally, like a developer explaining what happened during the session.

The tone should feel like a thoughtful engineering journal entry.

Structure the output roughly like this:

# Session Title

## What I tried to accomplish

## How the session unfolded
Narrative explanation of the conversation and development process.

## Key prompts that moved things forward

Include only the most important prompts - Quoted fully.

## Important decisions made

Architecture decisions, workflow changes, or Claude Code setup changes
(agents, rules, hooks, commands, etc).

## Takeaways

Insights about working with Claude Code or designing the system.

## Next direction

What should happen in the next session.

Save the file to:

docs/dev-journal/

File name format:

YYYY-MM-DD-session-title.md

If a journal file already exists for that date, add a numeric index:

YYYY-MM-DD-2-session-title.md
YYYY-MM-DD-3-session-title.md

Never append to an existing journal file. Each session gets its own file.
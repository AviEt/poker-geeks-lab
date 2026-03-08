Create a development journal entry for this Claude Code session.

Instructions:

1. Analyze the conversation history of this session.
2. Extract the most important prompts used by the user.
3. Summarize Claude's key outputs and architectural decisions.
4. Identify feedback or edits given to plans.
5. Identify Claude Code configuration changes such as:
   - CLAUDE.md changes
   - agents created
   - hooks created
   - settings modifications
   - new project files related to Claude Code

Then generate a journal entry in markdown format.

Save it to:

docs/dev-journal/

File name format:

YYYY-MM-DD-session-summary.md

The journal entry must include:

# Session Summary

## Context
Short explanation of the session goal.

## Key Prompts
Important prompts used during the session.

## Main Outputs
Important responses and decisions from Claude.

## Plan Feedback
Edits or corrections the user made.

## Claude Code Configuration Changes
Rules, agents, hooks, or settings added or modified.

## Code / Architecture Changes
New modules or design decisions.

## Lessons Learned

## Next Steps

Write it clearly so the entry can later be used to teach developers how to build the project step-by-step.
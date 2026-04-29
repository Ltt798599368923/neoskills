# Day 6: Vibe Coding Observation Journal

## Demo Task
Instructor demonstrated a full vibe-coding loop: converting a 10-page PDF into a 1-page memo.

## Four Moves Observed

### 1. Intent
The instructor started by clearly stating what they wanted: "Create a 1-page executive summary memo from this 10-page PDF, targeting a busy manager who needs the key takeaways."

**Observation**: The intent was specific about output length (1 page), format (memo), and audience (busy manager). This gave the agent a clear direction from the start.

### 2. Ask
The instructor didn't just paste the PDF and say "summarize." They structured the prompt with:
- Role: "You are a business analyst"
- Input: The PDF content
- Output shape: "Use headings, 3-5 bullet points per section, include action items"
- Acceptance: "A manager should be able to understand the core message in 2 minutes"

**Observation**: The pre-flight checklist (Role + Input + Output + Acceptance) was visible in how the prompt was constructed.

### 3. Iterate
When the first output was too long (1.5 pages), the instructor didn't re-prompt from scratch. They steered:
- "Good, but cut the background section to 2 sentences max"
- "Move the action items to the top"
- "Use shorter bullet points"

**Observation**: Each iteration was a small adjustment, not a complete rewrite. The instructor kept what worked and fixed what didn't.

### 4. Verify
The instructor checked the final output against the original acceptance criterion:
- "Can a manager understand this in 2 minutes? Yes."
- "Are the key takeaways clear? Yes."
- "Is it 1 page? Yes."

**Observation**: Verification was explicit, not assumed. The instructor read through the output and compared it to the original intent.

## Key Steering Moves

| Move | What Happened | Why It Matters |
|------|---------------|----------------|
| Setting constraints early | "1 page max" stated upfront | Prevents the agent from generating too much content |
| Iterative refinement | Small adjustments, not full re-prompts | Saves tokens and builds on what works |
| Explicit verification | Checked against acceptance criteria | Ensures the output actually meets the goal |
| Audience awareness | "Busy manager" mentioned in prompt | Shapes the tone and detail level |

## What Surprised Me
The instructor didn't treat the agent as an oracle that gets it right on the first try. Instead, they treated it like a junior colleague — give clear instructions, review the work, give feedback, and iterate. The "vibe" comes from knowing when to steer and when to let the agent run.

## One Thing I Noticed Most
**The instructor always had a written acceptance criterion before starting Action.** This prevented scope creep and made verification objective rather than subjective.

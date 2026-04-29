# Day 7: K-S-T-A-R Worksheet

## Exercise: Running skill-dedup to scan for duplicate skills

---

### K — Knowledge (Your Library)
**What I (and the agent) already know:**
- The neoskills project has a `skills/` directory with skill definitions
- Each skill has a `SKILL.md` file with metadata and instructions
- Duplicate skills can exist across multiple locations (bank, Claude, OpenCode, plugins)
- The `skill-dedup` skill has a Python script `scripts/dedup_scan.py` that can scan for duplicates
- The script supports three duplicate categories: exact, diverged, and name-similar

---

### S — Situation (Where You're Standing)
**Current context:**
- I'm working in the `d:\班级-elite\neoskills` repository (my fork)
- The project has 2 skills: `bank-status` and `skill-dedup`
- This is a fresh project, so likely no duplicates yet
- I need to understand how the skill works before using it in larger projects
- I have Python available to run the scan script

---

### T — Task (The Job Order)
**Specific thing to do now:**
Run the `skill-dedup` scan on the current workspace to check for duplicate skills.

**Acceptance Criterion:**
- The script runs without errors
- Output shows scan results (whether duplicates exist or not)
- I can explain what each duplicate category means
- I understand how the skill's SKILL.md guides the agent

---

### A — Action (The Move)
**What actually got executed:**

1. Read the `SKILL.md` file to understand the skill's purpose and usage
2. Navigated to the skill directory: `cd skills/skill-dedup`
3. Ran the scan command: `python scripts/dedup_scan.py --dry-run`
4. Reviewed the output to understand the results
5. Documented the findings in `skills-artifacts/D5-skill-dedup.md`

**Commands used:**
```bash
cd skills/skill-dedup
python scripts/dedup_scan.py --dry-run
```

**Output:**
```
Scanned 0 skills across bank + claude, opencode
No exact duplicates found.
No diverged copies found.
No name-similar groups found.
```

---

### R — Result (The Replay)
**What happened:**
- The scan completed successfully with no duplicates found (expected for a fresh project)
- I learned how the skill classifies duplicates into three categories
- I understood the resolution strategies: auto-resolve for exact duplicates, manual for name-similar

**What I learned:**
- Skills are "recipe cards" — the SKILL.md tells the agent what to do when a task matches
- The `--dry-run` flag is useful for previewing actions without making changes
- As the project grows, this skill will become more valuable for maintaining a clean skill inventory

**How this feeds back into K (the loop):**
- Now I know how to invoke a Skill and interpret its output
- I understand the duplicate categories, which will help when importing skills from other sources
- Next time I run this on a larger project, I'll know what to expect and how to resolve duplicates

---

## K-S-T-A-R Reflection

| Letter | Analogy | How It Applied Here |
|--------|---------|---------------------|
| K | Library | I started with knowledge of the project structure and the skill's purpose |
| S | Where you're standing | Fresh project, 2 skills, no duplicates expected |
| T | Job order | Run the scan and understand the output |
| A | The move | Executed `dedup_scan.py --dry-run` and documented results |
| R | The replay | Learned how Skills work; this knowledge feeds into future K |

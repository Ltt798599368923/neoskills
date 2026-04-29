# Day 5: Skill-Produced Artifact

## Skill Used: skill-dedup

### Invocation Command
```bash
cd skills/skill-dedup
python scripts/dedup_scan.py --dry-run
```

### Output
```
Scanned 0 skills across bank + claude, opencode

No exact duplicates found.
No diverged copies found.
No name-similar groups found.
```

### What This Skill Does
The `skill-dedup` skill scans for duplicate and near-duplicate skills across:
- **Bank**: `~/.neoskills/LTM/bank/skills/` (canonical copies)
- **Claude Code**: `~/.claude/skills/` (user-installed)
- **OpenCode**: `~/.config/opencode/skills/` (user-installed)
- **Plugins**: `~/.claude/plugins/*/skills/`

It classifies duplicates into three categories:
1. **Exact Duplicates** — identical content (same SHA256)
2. **Diverged Copies** — same skill ID but content differs
3. **Name-Similar Groups** — different skill IDs with similar names

### One-Paragraph Explanation
I invoked the `skill-dedup` skill to scan my neoskills workspace for duplicate skills. The skill uses a Python script (`dedup_scan.py`) that computes SHA256 hashes for exact matching and similarity scoring for name-based grouping. Since this is a fresh project with only 2 skills in the bank, no duplicates were found. This skill is useful for maintaining a clean skill inventory as the project grows — it can auto-resolve exact duplicates by replacing target copies with symlinks to the canonical bank version. Reading the SKILL.md taught me how Skills work: they are essentially "recipe cards" that tell the agent what to do when a task matches the skill's name and description. The skill body contains instructions, commands, and output formats that the agent follows.

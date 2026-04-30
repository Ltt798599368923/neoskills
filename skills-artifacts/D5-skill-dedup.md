# Day 5：Skill 使用作品

## 使用的 Skill：skill-dedup

### 运行命令
```bash
cd skills/skill-dedup
python scripts/dedup_scan.py --dry-run
```

### 输出结果
```
Scanned 0 skills across bank + claude, opencode

No exact duplicates found.
No diverged copies found.
No name-similar groups found.
```

### 这个 Skill 是干什么的
`skill-dedup` 用来扫描不同位置是否有重复的技能：
- **技能库**：`~/.neoskills/LTM/bank/skills/`（标准版本）
- **Claude Code**：`~/.claude/skills/`（用户安装的）
- **OpenCode**：`~/.config/opencode/skills/`（用户安装的）
- **插件**：`~/.claude/plugins/*/skills/`

它把重复分成三类：
1. **完全重复** — 内容一模一样（SHA256 相同）
2. **有分歧的副本** — 技能 ID 相同但内容有差异
3. **名字相似的组** — 不同技能 ID 但名字和描述相近

### 一段话总结
我调用了 `skill-dedup` 来扫描项目里有没有重复的技能。这个技能用一个 Python 脚本（`dedup_scan.py`）来计算 SHA256 做精确匹配，再用相似度评分做名字分组。因为这是个新项目，技能库里只有 2 个技能，所以没找到重复的。这个技能在项目变大后会很有用——它能自动把完全重复的副本替换成指向标准版本的符号链接。读完 SKILL.md 后我明白了 Skill 是怎么回事：本质上就是一张"菜谱卡"，告诉 agent 遇到匹配的任务时该做什么。SKILL.md 里面包含了使用说明、命令和输出格式。

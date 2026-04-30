# Day 7：K-S-T-A-R 工作表

## 练习：用 skill-dedup 扫描重复技能

---

### K — Knowledge（知识：你的图书馆）
**我（和 agent）已经知道的：**
- neoskills 项目有个 `skills/` 目录，里面是技能定义
- 每个技能都有一个 `SKILL.md` 文件，包含元数据和使用说明
- 重复的技能可能出现在多个位置（技能库、Claude、OpenCode、插件）
- `skill-dedup` 技能有一个 Python 脚本 `scripts/dedup_scan.py` 可以扫描重复
- 脚本支持三种重复分类：完全重复、有分歧的副本、名字相似的组

---

### S — Situation（情境：你站在哪）
**当前情况：**
- 我在 `d:\班级-elite\neoskills` 仓库里工作（我 fork 的）
- 项目里有 2 个技能：`bank-status` 和 `skill-dedup`
- 这是个新项目，大概率没有重复
- 我需要先理解这个技能怎么用，以后项目大了才能派上用场
- 我有 Python 环境可以运行扫描脚本

---

### T — Task（任务：工作指令）
**现在要做的具体事情：**
运行 `skill-dedup` 扫描，检查当前工作区有没有重复技能。

**验收标准：**
- 脚本运行不报错
- 输出显示扫描结果（有没有重复）
- 我能解释每种重复分类是什么意思
- 我理解 SKILL.md 是怎么引导 agent 的

---

### A — Action（行动：实际操作）
**具体执行了什么：**

1. 读了 `SKILL.md` 文件，理解技能的用途和用法
2. 进入技能目录：`cd skills/skill-dedup`
3. 运行扫描命令：`python scripts/dedup_scan.py --dry-run`
4. 看了输出结果，理解扫描结果
5. 把发现记录到了 `skills-artifacts/D5-skill-dedup.md`

**用的命令：**
```bash
cd skills/skill-dedup
python scripts/dedup_scan.py --dry-run
```

**输出：**
```
Scanned 0 skills across bank + claude, opencode
No exact duplicates found.
No diverged copies found.
No name-similar groups found.
```

---

### R — Result（结果：回放）
**发生了什么：**
- 扫描顺利完成，没有发现重复（新项目，符合预期）
- 我学会了这个技能是怎么把重复分成三类的
- 我了解了解决策略：完全重复可以自动解决，名字相似的需要手动判断

**我学到了什么：**
- Skill 就是"菜谱卡"——SKILL.md 告诉 agent 遇到匹配任务时该做什么
- `--dry-run` 参数很有用，可以预览操作但不实际执行
- 等项目变大了，这个技能对保持技能库整洁会很有帮助

**怎么反馈到 K（循环）：**
- 现在我知道怎么调用 Skill 并解读输出了
- 我理解了重复分类，以后从其他来源导入技能时就知道怎么处理了
- 下次在更大的项目上跑这个，我就知道会发生什么、怎么解决重复了

---

## K-S-T-A-R 总结

| 字母 | 类比 | 在这次练习中的体现 |
|------|------|-------------------|
| K | 图书馆 | 我从项目结构和技能用途的已有知识出发 |
| S | 你站的位置 | 新项目，2 个技能，预计没有重复 |
| T | 工作指令 | 运行扫描并理解输出 |
| A | 实际操作 | 执行 `dedup_scan.py --dry-run` 并记录结果 |
| R | 回放 | 学会了 Skill 的工作原理；这些知识变成下次的 K |

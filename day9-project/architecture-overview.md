# Neoskills 架构概览

## 项目简介
**neoskills** 是一个 Python CLI 工具，用于在多个平台（Claude Code、OpenCode 和插件）上管理 AI agent 技能。它提供技能发现、导入、去重、嵌入和本体管理功能。

---

## 高层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI 入口                                 │
│                     (cli/main.py)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ 命令模块  │  │  核心    │  │ 本体系统  │  │   运行时      │  │
│  │  (cli/)  │──│ (core/)  │  │  (/)     │  │  (runtime/)   │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘  │
│       │              │              │              │           │
│       ▼              ▼              ▼              ▼           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    适配器层                               │  │
│  │                  (adapters/)                             │  │
│  │   ┌─────────┐  ┌──────────┐  ┌──────────┐              │  │
│  │   │ Claude  │  │ OpenClaw │  │ OpenCode │              │  │
│  │   └─────────┘  └──────────┘  └──────────┘              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────┐  ┌──────────┐                                    │
│  │ 插件系统  │  │ 转换器    │                                    │
│  │ (plugin/)│  │  (/)      │                                    │
│  └──────────┘  └──────────┘                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 模块依赖关系

### 核心模块（`src/neoskills/core/`）
| 模块 | 作用 | 依赖 |
|------|------|------|
| `config.py` | 配置管理 | 无（基础模块） |
| `auth.py` | 认证处理 | config |
| `workspace.py` | 工作区目录管理 | config |
| `manifest.py` | 技能清单定义 | models, frontmatter |
| `models.py` | 数据模型 | 无 |
| `frontmatter.py` | YAML frontmatter 解析器 | 无 |
| `index.py` | 技能索引 | manifest, models |
| `resolver.py` | 技能解析 | index, manifest |
| `namespace.py` | 命名空间管理 | config |
| `cellar.py` | 技能存储 | manifest |
| `checksum.py` | 文件完整性检查 | 无 |
| `linker.py` | 符号链接管理 | workspace |
| `tap.py` | 源管理 | config |
| `mode.py` | 运行模式 | config |

### CLI 命令（`src/neoskills/cli/`）
| 命令 | 作用 | 核心依赖 |
|------|------|---------|
| `main.py` | CLI 入口 | 所有命令模块 |
| `list_cmd.py` | 列出技能 | core/index |
| `create_cmd.py` | 创建新技能 | core/manifest |
| `import_cmd.py` | 导入技能 | core/resolver |
| `dedup_cmd.py` | 去重技能 | core/checksum |
| `embed_cmd.py` | 嵌入技能 | core/linker |
| `doctor_cmd.py` | 健康检查 | core/workspace |
| `config_cmd.py` | 配置管理 | core/config |
| `init_cmd.py` | 初始化工作区 | core/workspace |
| `update_cmd.py` | 更新技能 | core/resolver |
| `push_cmd.py` | 推送到远程 | core/auth |
| `migrate_cmd.py` | 迁移工具 | core/manifest |
| `enhance_cmd.py` | 元增强 | meta/enhancer |
| `ontology_cmd.py` | 本体操作 | ontology/export |
| `schedule_cmd.py` | 定时任务 | core/config |
| `brew_install_cmd.py` | Brew 安装 | 无 |
| `agent_cmd.py` | Agent 管理 | adapters |
| `plugin_cmd.py` | 插件管理 | plugin |
| `link_cmd.py` | 链接操作 | core/linker |

### 本体系统（`src/neoskills/ontology/`）
| 模块 | 作用 |
|------|------|
| `models.py` | 本体数据模型 |
| `loader.py` | 从 YAML 加载本体 |
| `engine.py` | 本体处理引擎 |
| `graph.py` | 依赖图 |
| `taxonomy.py` | 技能分类 |
| `versioning.py` | 版本管理 |
| `lifecycle.py` | 技能生命周期状态 |
| `composition.py` | 技能组合规则 |
| `scaffold.py` | 本体脚手架 |
| `export.py` | 导出格式 |
| `writer.py` | YAML 写入器 |

### 适配器（`src/neoskills/adapters/`）
| 适配器 | 目标平台 |
|--------|---------|
| `claude/adapter.py` | Claude Code / Claude Desktop |
| `openclaw/adapter.py` | OpenClaw |
| `opencode/adapter.py` | OpenCode |
| `factory.py` | 适配器工厂模式 |
| `base.py` | 抽象适配器接口 |

---

## 架构模式

### 1. 工厂模式（适配器）
```
adapter_factory.get(target) → ClaudeAdapter | OpenClawAdapter | OpenCodeAdapter
```
工厂模式让添加新的 AI 平台集成时不需要修改已有代码。

### 2. 命令模式（CLI）
每个 CLI 命令都是一个独立的模块，接口一致，方便添加新命令。

### 3. 插件架构
插件系统允许在不修改核心代码的情况下扩展功能。

---

## 数据流

```
用户命令 → CLI 解析器 → 命令处理器 → 核心逻辑 → 适配器 → 目标平台
                      ↓
                  本体引擎（如果适用）
                      ↓
                  插件系统（如果适用）
```

---

## 入口点

1. **CLI**：`src/neoskills/cli/main.py` - 所有用户交互的主入口
2. **核心**：`src/neoskills/core/workspace.py` - 工作区初始化
3. **本体**：`src/neoskills/ontology/engine.py` - 本体处理

---

## 给新贡献者的关键提示

1. **从 `cli/main.py` 开始** 理解命令结构
2. **读 `core/config.py`** 理解配置层级
3. **研究 `adapters/base.py`** 理解适配器接口
4. **本体系统是最复杂的** - 先从 `ontology/models.py` 开始，再深入引擎

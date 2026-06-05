# Bilibili Subtitle → Obsidian Note

B 站视频 AI 字幕 → Obsidian Markdown 知识笔记，一键转换。

## 功能

- 提取 B 站视频 AI 字幕（需登录）
- 合并、分段、格式化字幕为结构化 Markdown
- 通过 LLM 生成知识卡片式 Obsidian 笔记
- 支持多分P批量处理
- 三种认证方式：QR 码扫码 / Cookie / 浏览器 Console

## 安装

### 前置条件

- [Obsidian](https://obsidian.md) + [Claude Code](https://claude.ai) + [Claudian - Obsidian插件]([YishenTu/claudian: An Obsidian plugin that embeds Claude Code/Codex as an AI collaborator in your vault](https://github.com/yishentu/claudian))
- Python 3 + `pip install requests qrcode[pil]`

### 安装步骤

```bash
# 1. 复制 skill 文件到 Claude Code skills 目录
cp -r skills/* .claude/skills/

# 2. 复制脚本和提示词到 scratch 目录
mkdir -p Claudian/scratch/bilibili-subtitleToNote/
cp scripts/* Claudian/scratch/bilibili-subtitleToNote/
cp prompts/* Claudian/scratch/bilibili-subtitleToNote/
```

### 初始化配置

在 Claude Code 中运行：

```
/set-bilibili-subtitle-to-note
```

按提示选择认证方式、配置路径。推荐 QR 码扫码登录。

## 使用

```
/bilibili-subtitle-to-note <视频URL> <输出目录> [分P] [额外要求]
```

| 参数 | 必选 | 说明 |
|------|------|------|
| 视频 URL | ✅ | B 站视频页地址或 BV 号 |
| 输出目录 | ✅ | 笔记输出目录（相对 vault） |
| 分P | ❌ | `all` / `1,2,3` / `3-5` / `no`（默认仅当前页） |
| 额外要求 | ❌ | 追加到 LLM prompt（如 "重点突出考试考点"） |

### 示例

```bash
# 单个视频，全部生成笔记
/bilibili-subtitle-to-note https://www.bilibili.com/video/BV1mQ 30.areas/learning/数据库/

# 仅 P1 和 P3，加额外要求
/bilibili-subtitle-to-note BV1mQ 30.areas/learning/数据库/ 1,3 重点突出考试考点

# 含 ?p=N 的 URL 自动识别分P
/bilibili-subtitle-to-note https://www.bilibili.com/video/BV1mQ/?p=3 30.areas/learning/数据库/
```

## 认证方式

| 方式 | 说明 | 推荐场景 |
|------|------|----------|
| QR 码 | App 扫码，两阶段流程 | 日常使用，免手动导出 |
| Cookie | 从浏览器导出 EditThisCookie JSON | 无手机 |
| Console | 浏览器 F12 运行 JS，Cookie 不出浏览器 | 隐私优先 |

## 文件结构

```
bilibili-subtitle-to-note/
├── skills/                    # Claude Code skill 定义
│   ├── bilibili-subtitle-to-note/
│   │   └── skill.md           # 主技能：字幕提取 + 笔记生成
│   └── set-bilibili-subtitle-to-note/
│       └── skill.md           # 配置技能：初始化设置
├── scripts/                   # Python / JS 脚本
│   ├── bili_fetch.py          # 认证 + API 字幕拉取
│   ├── bili_process.py        # 字幕格式转换
│   └── bili_console.js        # 浏览器 Console 认证脚本
├── prompts/
│   └── note_prompt.md         # LLM 笔记生成提示词
└── bili_config.example.json   # 配置模板
```

## 工作流

```
视频 URL → 获取字幕 (API/Console) → 格式转换 (compact.md) → LLM 生成笔记 (note.md)
```

管道输出：
- `bilibili_SubtitlesOutput/{BV号}/raw/` — 原始字幕 JSON
- `bilibili_SubtitlesOutput/{BV号}/` — compact.md + meta.json
- `{输出目录}/{page}_{part}_note.md` — 最终笔记

## License

MIT

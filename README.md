[中文](README-CN.md) | **English**

# Bilibili Subtitle → Obsidian Note

Bilibili video AI subtitles → Obsidian Markdown knowledge notes, one-click conversion.

## Features

- Extract Bilibili video AI subtitles (login required)
- Merge, segment, and format subtitles into structured Markdown
- Generate knowledge-card-style Obsidian notes via LLM
- Batch processing for multi-part videos
- Three authentication methods: QR code scan / Cookie / Browser Console

## Installation

### Prerequisites

- [Obsidian](https://obsidian.md) + [Claude Code](https://claude.ai) + [Claudian - Obsidian Plugin](https://github.com/yishentu/claudian)
- Python 3 + `pip install requests qrcode[pil]`

### Setup Steps

```bash
# 1. Copy skill files to Claude Code skills directory
cp -r skills/* .claude/skills/

# 2. Copy scripts and prompts to scratch directory
mkdir -p Claudian/scratch/bilibili-subtitleToNote/
cp scripts/* Claudian/scratch/bilibili-subtitleToNote/
cp prompts/* Claudian/scratch/bilibili-subtitleToNote/
```

### Initial Configuration

Run in Claude Code:

```
/set-bilibili-subtitle-to-note
```

Follow the prompts to select auth method and configure paths. QR code login is recommended.

## Usage

```
/bilibili-subtitle-to-note <videoURL> <outputDir> [pages] [extraRequirements]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| Video URL | ✅ | Bilibili video page URL or BV ID |
| Output Dir | ✅ | Note output directory (relative to vault) |
| Pages | ❌ | `all` / `1,2,3` / `3-5` / `no` (default: current page only) |
| Extra Reqs | ❌ | Appended to LLM prompt (e.g. "highlight exam key points") |

### Examples

```bash
# Single video, process current page
/bilibili-subtitle-to-note https://www.bilibili.com/video/BV1mQ 30.areas/learning/database/

# Only P1 and P3, with extra requirements
/bilibili-subtitle-to-note BV1mQ 30.areas/learning/database/ 1,3 highlight exam key points

# URL with ?p=N auto-detects page
/bilibili-subtitle-to-note https://www.bilibili.com/video/BV1mQ/?p=3 30.areas/learning/database/
```

## Authentication Methods

| Method | Description | Best For |
|--------|-------------|----------|
| QR Code | Scan with app, two-phase flow | Daily use, no manual export |
| Cookie | Export EditThisCookie JSON from browser | No phone available |
| Console | Run JS in browser F12, cookie never leaves browser | Privacy-first |

## File Structure

```
bilibili-subtitle-to-note/
├── skills/                    # Claude Code skill definitions
│   ├── bilibili-subtitle-to-note/
│   │   └── skill.md           # Main skill: subtitle extraction + note generation
│   └── set-bilibili-subtitle-to-note/
│       └── skill.md           # Config skill: initial setup
├── scripts/                   # Python / JS scripts
│   ├── bili_fetch.py          # Auth + API subtitle fetching
│   ├── bili_process.py        # Subtitle format conversion
│   └── bili_console.js        # Browser Console auth script
├── prompts/
│   └── note_prompt.md         # LLM note generation prompt
└── bili_config.example.json   # Configuration template
```

## Workflow

```
Video URL → Fetch Subtitles (API/Console) → Format Conversion (compact.md) → LLM Note Generation (note.md)
```

Pipeline output:
- `bilibili_SubtitlesOutput/{BVid}/raw/` — Raw subtitle JSON
- `bilibili_SubtitlesOutput/{BVid}/` — compact.md + meta.json
- `{outputDir}/{page}_{part}_note.md` — Final notes

## License

MIT

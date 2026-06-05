---
name: bilibili-subtitle-to-note
description: Extract BiliBili video AI subtitles and convert to structured Obsidian Markdown notes. Use when user wants to convert B站/Bilibili video subtitles to notes, mentions 字幕转笔记, B站笔记, video to note, or provides a bilibili.com/video/ URL.
---

# /bilibili-subtitle-to-note

B 站视频 AI 字幕 → Obsidian Markdown 知识笔记。

## 依赖

- 必须先运行 `/set-bilibili-subtitle-to-note` 完成配置
- 若未配置：提示用户先运行设置 skill
- **`{scratch}` 路径变量**：由 `/setup-matt-pocock-skills` 定义，默认为 `Claudian/scratch`。未运行该 skill 时使用默认值。

## 流程

### Step 0: 解析 `{scratch}` 路径

检测 `{scratch}` 是否已定义：
1. 已定义 → 直接使用
2. 未定义（未运行 `/setup-matt-pocock-skills`）→ 默认 `Claudian/scratch`

### Step 1: 读取配置

读 `{scratch}/bilibili-subtitleToNote/bili_config.json`。不存在 → 提示先运行 `/set-bilibili-subtitle-to-note`。

提取：`auth_method`, `python_cmd`, `cookie_path`, `console_js_path`, `note_prompt_path`, `compact_base_dir`, `scratch_dir`。
- `auth_method` 可选: `qrcode` | `cookie` | `console`

### Step 2: 解析用户参数

用户输入格式：
```
/bilibili-subtitle-to-note <视频URL> [输出目录] [分P] [额外要求]
```

| 参数 | 必选 | 默认 | 说明 |
|------|------|------|------|
| 视频 URL | ✅ | — | B 站视频页地址或 BV 号 |
| 输出目录 | ✅ | — | 笔记输出目录（相对 vault） |
| 分P | ❌ | `no`（仅当前页） | `all`、`1,2,3`、`3-5` 或 `no` |
| 额外要求 | ❌ | 空 | 追加到 LLM prompt 末尾 |

**`?p=N` URL 处理：** 检测到 `?p=3` → 默认 pages 设为 `3`，确认清单中标注。

### Step 3: 展示确认清单

```
┌─────────────────────────────────────────┐
│ 视频: 《数据库系统概论》 (BV1mQ)         │
│ 分P: P1, P2, P3 (共8个，已选3个)         │
│ 输出: 30.areas/learning/数据库/          │
│ Auth: QR 码 / Cookie / Console          │
│ 额外: 重点突出考试考点                   │
│                                         │
│ 确认执行? Y / 修改?                      │
└─────────────────────────────────────────┘
```

- 若用户未指定分P且视频有多P → 询问"检测到 N 个分P，提取全部还是一部分？"
- 列出分P信息：P1: 绪论 (25:58, 621条字幕)
- 等待用户确认或修改

获取分P列表方式：
- Cookie / QR 路径：`{python_cmd} {scratch_dir}/bili_fetch.py <bvid> --list-only --cookie {cookie_path}`
- Console 路径：无预检，用户在浏览器中自行确认

### Step 4: 获取字幕

**QR 路径（推荐）：两步式**
```bash
# 第一步：生成二维码（立即退出）
{python_cmd} {scratch_dir}/bili_fetch.py --generate-qr --cookie {cookie_path}
```
- 展示二维码：`![[{scratch_dir}/bili_qr.png]]`
- 告知用户：点击图片 → Bilibili App 扫码 → 回复「已确认扫码」
- **阻塞等待用户确认**

```bash
# 第二步：用户确认后，轮询登录
{python_cmd} {scratch_dir}/bili_fetch.py --complete-login --cookie {cookie_path}
```
- 成功后自动清理 `bili_qr.png` 和 `bili_qr_state.json`

```bash
# 正常获取字幕
{python_cmd} {scratch_dir}/bili_fetch.py <bvid> \
  --cookie {cookie_path} \
  --output {compact_base_dir} \
  --pages {pages}
```

**向后兼容：一步式 `--login-qr`**
```bash
{python_cmd} {scratch_dir}/bili_fetch.py --login-qr --cookie {cookie_path}
```
- 阻塞等待扫码（最多 3 分钟），不推荐

- 输出：`{compact_base_dir}/{bvid}/raw/` 下的 raw JSON
- 失败 → "Cookie 过期或无效。尝试重新扫码" → 回到两步式 QR 流程
- Cookie 不存在 → 自动先跑 `--generate-qr`，展示二维码，等待用户确认 → `--complete-login`

**Console 路径：**
1. 提示用户打开视频页面 `![[{console_js_path}]]`
2. 告知：F12 → Console → 粘贴 → Enter → 下载 JSON
3. 告知：将下载的 JSON 文件放入 `{compact_base_dir}/{bvid}/raw/`
4. **等待用户回复确认"已下载"再继续**

### Step 5: 重跑检测

检查 `{compact_base_dir}/{bvid}/raw/` 目录：
- 已有 JSON → 询问："检测到已下载的字幕文件，重新下载覆盖？Y/N"
- 无 → 继续

### Step 6: 格式转换

```bash
{python_cmd} {scratch_dir}/bili_process.py \
  --raw-dir {compact_base_dir}/{bvid}/raw \
  --output-dir {compact_base_dir}/{bvid}
```

输出：`{compact_base_dir}/{bvid}/{page}_{part}_compact.md` + `meta.json`

### Step 7: 生成笔记

读 `{note_prompt_path}` → 获得基础 LLM prompt。追加额外要求（如有）。

对每个选中的分P，独立调用 Agent：

```
分P {page_num}: {part_name}

1. 读 {compact_base_dir}/{bvid}/{page_num}_{part_name}_compact.md
2. 用 prompt 生成笔记
3. 写入 {output_dir}/{safe_name}_note.md
```

笔记文件命名规则：`{page_num}_{safe_part_name}_note.md`

### Step 8: 完成报告

```
┌─────────────────────────────────────────┐
│ ✅ 字幕笔记生成完成                       │
│                                          │
│ 视频: 《数据库系统概论》(BV1mQ)           │
│ 生成笔记:                                │
│   [[output/P1_绪论_note.md]]             │
│   [[output/P2_关系数据库_note.md]]        │
│   ...                                    │
│                                          │
│ 中间文件: bilibili_SubtitlesOutput/BV1mQ/ │
└─────────────────────────────────────────┘
```

## 错误处理

| 错误 | 处理 |
|------|------|
| 配置不存在 | 提示运行 `/set-bilibili-subtitle-to-note` |
| Cookie 过期/无效 | QR 方式：运行 `--generate-qr` → 展示二维码 → 用户确认 → `--complete-login`。Cookie 方式：提示运行 `/set-bilibili-subtitle-to-note` 更新 |
| 字幕为空 | 报告该分P无字幕，跳过 |
| Python 无 `requests` | 提示 `pip install requests`，询问是否自动安装 |
| Python 无 `qrcode` | 提示 `pip install qrcode[pil]`，询问是否自动安装 |
| raw 目录有冲突 | 询问覆盖确认 |

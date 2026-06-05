---
name: set-bilibili-subtitle-to-note
description: Configure BiliBili subtitle extraction settings. Use when user wants to set up or change BiliBili subtitle-to-note pipeline settings, mentions B站字幕设置, or needs to update auth method/cookie.
---

# /set-bilibili-subtitle-to-note

设置 B 站字幕 → Obsidian 笔记流水线。

## 前置条件

- Python 3 安装，`pip install requests`
- (Cookie 路径) EditThisCookie Chrome 扩展
- (Console 路径) 浏览器能打开 B 站

## 流程

### Step 1: 解析 scratch 目录

检查 scratch 路径配置优先级：

1. 已有 scratch 路径配置 → 直接用 `{scratch}/bilibili-subtitleToNote/`
2. 未配置 → 询问用户："请输入 scratch 目录路径（默认 `Claudian/scratch/bilibili-subtitleToNote/`）"
3. 用户指定 → 用用户给的

### Step 2: 确保目录存在

```bash
mkdir -p {scratch}/bilibili-subtitleToNote
```

确保以下文件存在（不存在则创建）：
- `bili_console.js` — 浏览器 Console 运行的 JS
- `note_prompt.md` — LLM 笔记生成提示词
- `bili_config.json` — 配置模板

### Step 3: 选择认证方式

```
┌──────────────────────────────────────────────────┐
│ 选择认证方式：                                    │
│ 1. QR 码 → App 扫码登录 (推荐，免手动导出 Cookie) │
│ 2. Cookie → 从浏览器导出 EditThisCookie JSON      │
│ 3. Console → 浏览器 Console 运行 JS              │
│    (Cookie 不离开浏览器，隐私最好)                │
└──────────────────────────────────────────────────┘
```

**QR 码路径（推荐）：两阶段流程**
1. 第一步：`python {scratch}/bilibili-subtitleToNote/bili_fetch.py --generate-qr`
   - 生成二维码 PNG，保存 qrcode_key 到 `bili_qr_state.json`，**立即退出**
2. 展示二维码：`![[{scratch}/bilibili-subtitleToNote/bili_qr.png]]`
   - 用户点击路径打开图片 → Bilibili App 扫码
3. **等待用户回复「已确认扫码」**
4. 第二步：`python {scratch}/bilibili-subtitleToNote/bili_fetch.py --complete-login`
   - 读取 qrcode_key → 轮询 API → 保存 Cookie
   - 成功后自动清理 `bili_qr.png` 和 `bili_qr_state.json`
- 需要 `pip install qrcode[pil]`
- 向后兼容：`--login-qr` 仍可用（一步式阻塞，不推荐）

**Cookie 路径：**
- 引导用户：Chrome → F12 → Application → Cookies → EditThisCookie 导出
- 保存为 `{scratch}/bilibili-subtitleToNote/bili_cookies.json`
- 提醒：SESSDATA 约 30 天过期

**Console 路径：**
- 提供文件路径：`![[{scratch}/bilibili-subtitleToNote/bili_console.js]]`
- 说明用法：打开 B 站视频页 → F12 → Console → 粘贴 → Enter → 下载 JSON
- 勿输出代码全文，只给路径

### Step 4: 配置路径与工具

询问：
- Python 命令 (`python` / `python3` / `py`)，默认 `python`
- 认证方式确认（默认 `qrcode`）
- 笔记提示词路径 → 将笔记生成提示词保存到 `{scratch}/bilibili-subtitleToNote/note_prompt.md`（可从仓库 `prompts/note_prompt.md` 获取默认版本）
- Compact 中间文件存储路径（默认 `bilibili_SubtitlesOutput`）

如果选 QR 码方式且需要 `qrcode[pil]`，询问是否安装依赖。

### Step 5: 写入配置

```json
{
  "_comment_auth": "auth_method 可选: qrcode | cookie | console",
  "auth_method": "qrcode",
  "cookie_path": "{scratch}/bilibili-subtitleToNote/bili_cookies.json",
  "console_js_path": "{scratch}/bilibili-subtitleToNote/bili_console.js",
  "python_cmd": "python",
  "note_prompt_path": "{scratch}/bilibili-subtitleToNote/note_prompt.md",
  "compact_base_dir": "bilibili_SubtitlesOutput",
  "scratch_dir": "{scratch}/bilibili-subtitleToNote"
}
```

保存到 `{scratch}/bilibili-subtitleToNote/bili_config.json`。

### Step 6: 验证

- 检查所有配置路径存在
- QR 路径：运行 `python bili_fetch.py --generate-qr --cookie <path>` → 展示二维码 → 用户扫码确认 → 运行 `python bili_fetch.py --complete-login --cookie <path>`
- Cookie 路径：运行 `python bili_fetch.py --check-login --cookie <path>` 验证
- Console 路径：确认 `bili_console.js` 可读

输出完成摘要，告知 `/bilibili-subtitle-to-note` 已可用。

## 错误处理

| 错误 | 处理 |
|------|------|
| Python 未安装 | 提示安装 Python 3，终止 |
| `pip install requests` 失败 | 询问是否自动安装 |
| `pip install qrcode[pil]` 失败 | 询问是否自动安装（仅 QR 路径需要）|
| QR 码过期 | 提示重新运行 `--generate-qr` |
| 扫码超时 | 提示重试，最多等待 3 分钟 |
| Cookie 无效 | 提示重新登录 |
| 配置路径不存在 | 逐项检查并提示修复 |

## 文件清单

所有可复用代码存储于 scratch 目录：

| 文件 | 用途 |
|------|------|
| `bili_config.json` | 用户配置 |
| `bili_fetch.py` | Cookie 路径：认证 + API 拉取 |
| `bili_process.py` | 格式转换（两条路径共用）|
| `bili_console.js` | 浏览器 Console 脚本 |
| `note_prompt.md` | LLM 笔记生成提示词（固化版本）|
| `bili_cookies.json` | 登录 Cookie（自动生成）|
| `bili_qr.png` | 二维码图片（临时，登录后自动清理）|
| `bili_qr_state.json` | QR 登录状态（临时，登录后自动清理）|

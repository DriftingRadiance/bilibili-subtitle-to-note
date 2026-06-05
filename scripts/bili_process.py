#!/usr/bin/env python3
"""
BiliBili Subtitle Processor — 读 raw JSON → compact.md + meta.json
用法: python bili_process.py --raw-dir <path> --output-dir <path>
"""
import argparse
import json
import sys
from pathlib import Path


def format_subtitle_merged(body: list) -> str:
    """
    合并字幕为段落格式，带时间戳。
    分段策略: 句末标点 + >1s 间隔，或 >3s 间隔。
    """
    if not body:
        return ""
    paragraphs = []
    current_lines = []
    current_start = None

    for i, item in enumerate(body):
        if item.get("music", 0) == 1:
            continue
        from_time = item.get("from", 0)
        content = item.get("content", "")

        if not current_lines:
            current_start = from_time

        current_lines.append(content)

        has_end_punct = content.rstrip()[-1:] in "。？！.?!"
        next_gap = 999
        if i + 1 < len(body):
            next_gap = body[i + 1]["from"] - item.get("to", from_time)

        if has_end_punct and next_gap > 1.0:
            text = "".join(current_lines)
            mins = int(current_start // 60)
            secs = int(current_start % 60)
            paragraphs.append(f"[{mins:02d}:{secs:02d}] {text}")
            current_lines = []
            current_start = None
        elif next_gap > 3.0:
            text = "".join(current_lines)
            mins = int(current_start // 60)
            secs = int(current_start % 60)
            paragraphs.append(f"[{mins:02d}:{secs:02d}] {text}")
            current_lines = []
            current_start = None

    if current_lines:
        mins = int(current_start // 60)
        secs = int(current_start % 60)
        paragraphs.append(f"[{mins:02d}:{secs:02d}] {''.join(current_lines)}")

    return "\n".join(paragraphs)


def seconds_to_timestamp(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def process(raw_dir: Path, output_dir: Path) -> list:
    """
    读 raw_dir 下所有 *_*.json 文件 → 生成 compact.md 到 output_dir。
    返回: [(page_num, part_name, duration_sec, subtitle_count, compact_path), ...]
    """
    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 读取 meta.json (如果存在) 获取 duration 信息
    meta_path = output_dir.parent / "meta.json"
    meta = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

    page_meta = {}
    for p in meta.get("pages", []):
        page_meta[p["page"]] = {"part": p["part"], "duration": p["duration"]}

    results = []
    json_files = sorted(raw_dir.glob("*.json"), key=lambda p: p.name)

    for jf in json_files:
        # 解析文件名: {page}_{part}.json
        stem = jf.stem
        parts = stem.split("_", 1)
        try:
            page_num = int(parts[0])
            part_name = parts[1] if len(parts) > 1 else ""
        except ValueError:
            print(f"  [SKIP] 无法解析页码: {jf.name}")
            continue

        with open(jf, "r", encoding="utf-8") as f:
            body = json.load(f)

        if not body:
            print(f"  [SKIP] P{page_num} "{part_name}" 无字幕")
            continue

        text = format_subtitle_merged(body)
        duration = page_meta.get(page_num, {}).get("duration", 0)

        safe_name = part_name.replace("/", "_").replace(":", "_").replace("*", "_") \
                             .replace("?", "_").replace('"', "_").replace("<", "_") \
                             .replace(">", "_").replace("|", "_")
        compact_filename = f"{page_num}_{safe_name}_compact.md"
        compact_path = output_dir / compact_filename

        with open(compact_path, "w", encoding="utf-8") as f:
            f.write(f"# P{page_num} {part_name}\n\n")
            f.write(text)

        line_count = len(text.split("\n"))
        print(f"  [OK] P{page_num} "{part_name}" → {compact_filename} ({line_count} 段)")
        results.append((page_num, part_name, duration, len(body), compact_path))

    # 生成/更新 meta.json
    new_meta = {
        "bvid": meta.get("bvid", ""),
        "title": meta.get("title", ""),
        "fetch_time": meta.get("fetch_time", ""),
        "pages": [
            {
                "page": pn,
                "part": pn_name,
                "duration": dur,
                "subtitles": count,
            }
            for pn, pn_name, dur, count, _ in results
        ],
    }
    with open(output_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(new_meta, f, ensure_ascii=False, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(description="BiliBili 字幕格式转换")
    parser.add_argument("--raw-dir", required=True, help="raw JSON 目录")
    parser.add_argument("--output-dir", required=True, help="compact.md 输出目录")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    if not raw_dir.exists():
        print(f"[!] raw 目录不存在: {raw_dir}")
        sys.exit(1)

    json_files = list(raw_dir.glob("*.json"))
    if not json_files:
        print(f"[!] raw 目录下无 JSON 文件: {raw_dir}")
        sys.exit(1)

    results = process(raw_dir, Path(args.output_dir))
    if not results:
        print("[!] 未生成任何 compact 文件")
        sys.exit(1)

    total_lines = sum(count for _, _, _, count, _ in results)
    print(f"\nDone! {len(results)} 个 compact 文件, {total_lines} 条字幕 → {args.output_dir}")


if __name__ == "__main__":
    main()

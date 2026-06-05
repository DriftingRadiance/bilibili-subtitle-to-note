#!/usr/bin/env python3
"""
BiliBili Subtitle Fetcher (Cookie / QR 码认证)
用法:
  python bili_fetch.py --generate-qr [--cookie <path>]      生成二维码 → 用户扫码
  python bili_fetch.py --complete-login [--cookie <path>]   轮询扫码结果 → 保存 Cookie
  python bili_fetch.py --login-qr [--cookie <path>]         一步式扫码登录 (阻塞，不推荐)
  python bili_fetch.py <bvid> [--cookie <path>] [--output <dir>] [--pages <list>] [--list-only] [--check-login]
"""
import argparse
import hashlib
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.bilibili.com",
})

WBI_IMG_KEY = ""
WBI_SUB_KEY = ""
COOKIE_FILE = Path(__file__).parent / "bili_cookies.json"


# ============================================================
# WBI 签名
# ============================================================
def fetch_wbi_keys():
    global WBI_IMG_KEY, WBI_SUB_KEY
    resp = SESSION.get("https://api.bilibili.com/x/web-interface/nav")
    data = resp.json()
    wbi = data["data"]["wbi_img"]
    WBI_IMG_KEY = wbi["img_url"].split("/")[-1].split(".")[0]
    WBI_SUB_KEY = wbi["sub_url"].split("/")[-1].split(".")[0]


def wbi_sign(params: dict) -> dict:
    mix_key = (WBI_IMG_KEY + WBI_SUB_KEY)[:32]
    params["wts"] = str(int(time.time()))
    sorted_params = sorted(params.items())
    query = urllib.parse.urlencode(sorted_params)
    params["w_rid"] = hashlib.md5((query + mix_key).encode()).hexdigest()
    return params


# ============================================================
# Cookie 管理
# ============================================================
def load_cookies(filepath: Path) -> bool:
    """从文件加载 Cookie (支持 EditThisCookie 数组和简单 dict)"""
    if not filepath or not filepath.exists():
        return False
    with open(filepath, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    if isinstance(cookies, list):
        for c in cookies:
            SESSION.cookies.set(c["name"], c["value"],
                                domain=c.get("domain", ".bilibili.com"),
                                path=c.get("path", "/"))
    else:
        for name, value in cookies.items():
            SESSION.cookies.set(name, value, domain=".bilibili.com")
    print(f"[OK] 已加载 {len(cookies)} 个 Cookie: {filepath}")
    return True


def check_login() -> bool:
    resp = SESSION.get("https://api.bilibili.com/x/web-interface/nav")
    data = resp.json()
    is_login = data["data"]["isLogin"]
    if is_login:
        uname = data["data"].get("uname", "unknown")
        print(f"[OK] 已登录: {uname}")
    return is_login


def save_cookies(filepath: Path = None):
    """保存当前会话 Cookie 到文件"""
    fp = filepath or COOKIE_FILE
    cookies = {}
    for cookie in SESSION.cookies:
        cookies[cookie.name] = cookie.value
    fp.parent.mkdir(parents=True, exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f"[OK] Cookie 已保存到 {fp}")


def qr_login(cookie_path: Path = None) -> bool:
    """扫码登录，返回是否成功，成功时 Cookie 已保存"""
    try:
        import qrcode
    except ImportError:
        print("[!] 需要 qrcode 库: pip install qrcode[pil]")
        return False

    fp = cookie_path or COOKIE_FILE

    # 1. 生成二维码
    resp = SESSION.get("https://passport.bilibili.com/x/passport-login/web/qrcode/generate")
    data = resp.json()
    if data["code"] != 0:
        print(f"[!] 获取二维码失败: {data}")
        return False

    url = data["data"]["url"]
    qrcode_key = data["data"]["qrcode_key"]

    # 2. 生成二维码图片
    img = qrcode.make(url)
    qr_path = fp.parent / "bili_qr.png"
    img.save(qr_path)
    print(f"\n{'='*50}")
    print(f"请用 Bilibili App 扫描二维码：")
    print(f"  {qr_path}")
    print(f"{'='*50}\n")

    # 3. 轮询扫码状态
    for i in range(90):  # 最多 3 分钟
        resp = SESSION.get(
            "https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
            params={"qrcode_key": qrcode_key},
        )
        data = resp.json()
        code = data.get("data", {}).get("code")

        if code == 0:
            print("[OK] 扫码登录成功!")
            fetch_wbi_keys()
            save_cookies(fp)
            return True
        elif code == 86038:
            print("[!] 二维码已过期，请重试")
            return False
        elif code == 86090:
            if i % 5 == 0:
                print("[.] 已扫码，请在手机上确认...")
        elif code == 86101:
            if i == 0:
                print("[.] 等待扫码...")

        time.sleep(2)

    print("[!] 扫码超时")
    return False


def generate_qr(cookie_path: Path = None) -> str:
    """
    生成二维码图片 + 保存 qrcode_key。
    返回: qrcode_key (供后续 complete_login 使用)
    不等待扫码，立即返回。
    """
    try:
        import qrcode
    except ImportError:
        print("[!] 需要 qrcode 库: pip install qrcode[pil]")
        return ""

    fp = cookie_path or COOKIE_FILE

    resp = SESSION.get("https://passport.bilibili.com/x/passport-login/web/qrcode/generate")
    data = resp.json()
    if data["code"] != 0:
        print(f"[!] 获取二维码失败: {data}")
        return ""

    url = data["data"]["url"]
    qrcode_key = data["data"]["qrcode_key"]

    # 生成二维码图片
    img = qrcode.make(url)
    qr_path = fp.parent / "bili_qr.png"
    img.save(qr_path)

    # 保存 qrcode_key 到状态文件
    state = {"qrcode_key": qrcode_key, "cookie_path": str(fp)}
    state_path = fp.parent / "bili_qr_state.json"
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"二维码已生成:")
    print(f"  {qr_path}")
    print(f"请用 Bilibili App 扫描二维码，然后告诉我「已确认扫码」。")
    print(f"状态文件: {state_path}")
    print(f"{'='*50}\n")
    return qrcode_key


def complete_qr_login(cookie_path: Path = None) -> bool:
    """
    读取 qrcode_key → 轮询扫码结果 → 保存 Cookie。
    返回: 是否登录成功。
    """
    fp = cookie_path or COOKIE_FILE
    state_path = fp.parent / "bili_qr_state.json"

    if not state_path.exists():
        print("[!] 未找到 QR 状态文件，请先运行 --generate-qr")
        return False

    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    qrcode_key = state.get("qrcode_key", "")
    if not qrcode_key:
        print("[!] 状态文件中无 qrcode_key")
        return False

    print(f"[.] 正在轮询扫码结果 (qrcode_key={qrcode_key[:8]}...)")

    for i in range(90):  # 最多 3 分钟
        resp = SESSION.get(
            "https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
            params={"qrcode_key": qrcode_key},
        )
        data = resp.json()
        code = data.get("data", {}).get("code")

        if code == 0:
            print("[OK] 扫码登录成功!")
            # 清理状态文件
            state_path.unlink(missing_ok=True)
            # 清理二维码图片
            qr_img = fp.parent / "bili_qr.png"
            qr_img.unlink(missing_ok=True)
            fetch_wbi_keys()
            save_cookies(fp)
            return True
        elif code == 86038:
            print("[!] 二维码已过期，请重新运行 --generate-qr")
            state_path.unlink(missing_ok=True)
            return False
        elif code == 86090:
            if i % 5 == 0:
                print("[.] 已扫码，请在手机上确认...")
        elif code == 86101:
            if i == 0:
                print("[.] 等待扫码...")

        time.sleep(2)

    print("[!] 扫码超时")
    state_path.unlink(missing_ok=True)
    return False


# ============================================================
# 字幕获取
# ============================================================
def get_video_info(bvid: str) -> dict:
    params = wbi_sign({"bvid": bvid})
    url = "https://api.bilibili.com/x/web-interface/wbi/view?" + urllib.parse.urlencode(params)
    resp = SESSION.get(url)
    data = resp.json()
    if data["code"] != 0:
        raise Exception(f"获取视频信息失败: {data}")
    return data["data"]


def get_subtitle_urls(bvid: str, cid: int) -> list:
    params = wbi_sign({
        "bvid": bvid, "cid": str(cid),
        "fnval": "12288", "fnver": "0", "fourk": "1",
    })
    url = "https://api.bilibili.com/x/player/wbi/v2?" + urllib.parse.urlencode(params)
    resp = SESSION.get(url)
    data = resp.json()
    return data.get("data", {}).get("subtitle", {}).get("subtitles", [])


def download_subtitle(subtitle_url: str) -> dict:
    if subtitle_url.startswith("//"):
        subtitle_url = "https:" + subtitle_url
    resp = SESSION.get(subtitle_url)
    if resp.status_code != 200:
        raise Exception(f"下载字幕失败: {resp.status_code} {resp.text[:200]}")
    return resp.json()


def fetch_all_subtitles(bvid: str, pages_filter: list = None) -> tuple:
    info = get_video_info(bvid)
    pages = info["pages"]
    title = info["title"]
    results = []
    for page in pages:
        page_num = page["page"]
        part_name = page["part"]
        cid = page["cid"]
        duration = page["duration"]
        if pages_filter and page_num not in pages_filter:
            print(f"  [SKIP] P{page_num}: {part_name}")
            continue
        print(f"\n[SUB] P{page_num}: {part_name} (cid={cid}, {duration}s)")
        sub_infos = get_subtitle_urls(bvid, cid)
        if not sub_infos:
            print(f"  [!] 无字幕")
            results.append((page_num, part_name, duration, []))
            continue
        selected = None
        for s in sub_infos:
            if s.get("lan") in ("zh-CN", "ai-zh", "zh"):
                selected = s; break
        if not selected:
            selected = sub_infos[0]
        sub_url = selected["subtitle_url"]
        try:
            subtitle_data = download_subtitle(sub_url)
            body = subtitle_data.get("body", [])
            print(f"  [OK] {len(body)} 条字幕")
            results.append((page_num, part_name, duration, body))
        except Exception as e:
            print(f"  [!] 下载失败: {e}")
            results.append((page_num, part_name, duration, []))
    return results, title


def save_raw_subtitles(results: list, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    for page_num, part_name, duration, body in results:
        if not body:
            continue
        safe_name = part_name.replace("/", "_").replace(":", "_").replace("*", "_") \
                             .replace("?", "_").replace('"', "_").replace("<", "_") \
                             .replace(">", "_").replace("|", "_")
        filename = f"{page_num}_{safe_name}.json"
        filepath = output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False, indent=2)
        print(f"  [SAVE] {filepath}")


def seconds_to_timestamp(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


# ============================================================
# CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="BiliBili 字幕下载 (Cookie / QR 码认证)")
    parser.add_argument("url", nargs="?", help="B 站视频 URL 或 BV 号")
    parser.add_argument("--cookie", "-c", help="Cookie JSON 文件路径")
    parser.add_argument("--output", "-o", default="bilibili_SubtitlesOutput", help="输出根目录")
    parser.add_argument("--pages", "-p", help="分P编号，逗号分隔 (默认全部)")
    parser.add_argument("--list-only", action="store_true", help="仅列出分P信息，不下载")
    parser.add_argument("--check-login", action="store_true", help="仅检查 Cookie 是否有效")
    parser.add_argument("--login-qr", action="store_true", help="扫码登录并保存 Cookie，然后退出 (一步式阻塞)")
    parser.add_argument("--generate-qr", action="store_true", help="生成二维码图片，不等待扫码 (两步式第一步)")
    parser.add_argument("--complete-login", action="store_true", help="读取 qrcode_key 并轮询扫码结果 (两步式第二步)")
    args = parser.parse_args()

    # 确定 cookie 路径
    cookie_path = Path(args.cookie) if args.cookie else COOKIE_FILE

    # --generate-qr: 生成二维码 + 保存 key，立即退出
    if args.generate_qr:
        key = generate_qr(cookie_path)
        if not key:
            sys.exit(1)
        print("二维码已生成。用户扫码确认后，运行:")
        print(f"  python bili_fetch.py --complete-login --cookie {cookie_path}")
        sys.exit(0)

    # --complete-login: 读 key → 轮询 → 保存 Cookie
    if args.complete_login:
        if not complete_qr_login(cookie_path):
            sys.exit(1)
        print("登录完成。现在可以运行 bili_fetch.py <bvid> 获取字幕。")
        sys.exit(0)

    # --login-qr: 扫码登录 (一步式，向后兼容)
    if args.login_qr:
        if not qr_login(cookie_path):
            sys.exit(1)
        print("登录完成。现在可以运行 bili_fetch.py <bvid> 获取字幕。")
        sys.exit(0)

    # --check-login
    if args.check_login:
        if args.cookie:
            load_cookies(Path(args.cookie))
        elif cookie_path.exists():
            load_cookies(cookie_path)
        fetch_wbi_keys()
        if check_login():
            print("Cookie 有效。")
            sys.exit(0)
        else:
            print("Cookie 无效或已过期。")
            sys.exit(1)

    if not args.url:
        parser.print_help()
        sys.exit(1)

    bvid_match = re.search(r"BV[\w]+", args.url)
    if not bvid_match:
        print("[!] 无效 URL，需要包含 BV 号")
        sys.exit(1)
    bvid = bvid_match.group(0)

    # 登录
    if args.cookie:
        load_cookies(Path(args.cookie))
    elif cookie_path.exists():
        load_cookies(cookie_path)
    fetch_wbi_keys()
    if not check_login():
        print("[!] 未登录。请先运行 --login-qr 扫码，或提供 Cookie 文件。")
        sys.exit(1)

    # 分P过滤
    pages_filter = None
    if args.pages:
        pages_filter = [int(p.strip()) for p in args.pages.split(",")]

    # --list-only
    if args.list_only:
        info = get_video_info(bvid)
        print(f"视频: {info['title']} ({bvid})")
        for p in info["pages"]:
            print(f"  P{p['page']}: {p['part']} ({seconds_to_timestamp(p['duration'])})")
        sys.exit(0)

    # 下载
    raw_dir = Path(args.output) / bvid / "raw"
    print(f"输出目录: {raw_dir}")
    results, video_title = fetch_all_subtitles(bvid, pages_filter)
    if not results:
        print("[!] 未获取到任何字幕")
        sys.exit(1)
    save_raw_subtitles(results, raw_dir)

    # 保存 meta 摘要
    meta = {
        "bvid": bvid,
        "title": video_title,
        "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pages": [
            {"page": pn, "part": pn_name, "duration": dur, "subtitles": len(body)}
            for pn, pn_name, dur, body in results
        ],
    }
    meta_path = Path(args.output) / bvid / "meta.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    total_lines = sum(len(body) for _, _, _, body in results)
    print(f"\nDone! {len(results)} 个分P, {total_lines} 条字幕 → {meta_path.parent}")


if __name__ == "__main__":
    main()

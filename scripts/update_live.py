#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
影视仓 / TVBox 电视直播源自动更新脚本
=====================================
功能：
1. 读取 config/live_sources.json 中的上游直播源（支持 txt #genre# 格式 与 m3u #EXTINF 格式）
2. 逐个抓取，解析为 {(分组, 频道名): [url, ...]}，兼容两种格式
3. 合并去重（同频道多线路保留，频道名/分组归一化），过滤无效 URL
4. 生成自有直播文件：
   - output/live.txt       影视仓直播地址（#genre# 分组格式，可直接填进"直播地址"）
   - output/live.m3u       标准 m3u（带 tvg-name/group-title，兼容 VLC/其他播放器）
   - output/live_status.json 更新状态
5. 容错：某源失败不影响其他源；全部失败时沿用上次缓存的 live.txt

用法：
    python scripts/update_live.py
"""

import datetime
import json
import os
import re
import sys
import time
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(ROOT, "config", "live_sources.json")
OUTPUT_DIR = os.path.join(ROOT, "output")

USER_AGENT = "Mozilla/5.0"
TIMEOUT = 20
MAX_RETRIES = 2

# 每个频道最多保留的线路数（避免单文件过大、也保证有冗余可切换）
MAX_LINES_PER_CHANNEL = 6
# 过滤掉明显无效的 URL
INVALID_URL_PAT = re.compile(r"(127\.0\.0\.1|localhost|0\.0\.0\.0|示例|example\.com)", re.I)


def now_cst():
    tz = datetime.timezone(datetime.timedelta(hours=8))
    return datetime.datetime.now(tz)


def normalize_channel(name: str) -> str:
    """归一化频道名：去空白、统一常见别名，便于跨源合并。"""
    name = re.sub(r"\s+", "", (name or "").strip())
    # 去掉常见的清晰度/线路后缀括号，如 (720p)/(1080p)/(4K)/(高清)/(HD)/(线路2)
    name = re.sub(r"[（(](?:1080p?|720p?|4k|2160p|高清|HD|超清|蓝光|线路\d*)[）)]", "", name, flags=re.I)
    # 去掉结尾的清晰度标记，如 CCTV5HD / 湖南卫视1080P
    name = re.sub(r"(?:HD|1080P?|720P?|4K)$", "", name, flags=re.I)
    aliases = {
        "CCTV1综合": "CCTV1", "CCTV-1": "CCTV1", "央视一套": "CCTV1",
        "CCTV2财经": "CCTV2", "CCTV-2": "CCTV2",
        "CCTV3综艺": "CCTV3", "CCTV-3": "CCTV3",
        "CCTV4中文国际": "CCTV4", "CCTV-4": "CCTV4",
        "CCTV5体育": "CCTV5", "CCTV-5": "CCTV5",
        "CCTV5+体育赛事": "CCTV5+", "CCTV-5+": "CCTV5+",
        "CCTV6电影": "CCTV6", "CCTV-6": "CCTV6",
        "CCTV7国防军事": "CCTV7", "CCTV-7": "CCTV7",
        "CCTV8电视剧": "CCTV8", "CCTV-8": "CCTV8",
        "CCTV9纪录": "CCTV9", "CCTV-9": "CCTV9",
        "CCTV10科教": "CCTV10", "CCTV-10": "CCTV10",
        "CCTV11戏曲": "CCTV11", "CCTV-11": "CCTV11",
        "CCTV12社会与法": "CCTV12", "CCTV-12": "CCTV12",
        "CCTV13新闻": "CCTV13", "CCTV-13": "CCTV13",
        "CCTV14少儿": "CCTV14", "CCTV-14": "CCTV14",
        "CCTV15音乐": "CCTV15", "CCTV-15": "CCTV15",
        "CCTV16奥林匹克": "CCTV16", "CCTV-16": "CCTV16",
        "CCTV17农业农村": "CCTV17", "CCTV-17": "CCTV17",
    }
    name = aliases.get(name, name)
    # 统一 CCTV-数字 与 CCTV数字 两种写法（含 CCTV-5+ / CCTV5+）
    m = re.fullmatch(r"CCTV-?(\d+\+?)", name, re.I)
    if m:
        name = "CCTV" + m.group(1)
    return name


def normalize_group(name: str) -> str:
    """归一化分组名。"""
    name = (name or "").strip()
    name = re.sub(r"^[^\w\u4e00-\u9fff]+", "", name)  # 去开头的 emoji/装饰符
    if re.search(r"央视|CCTV", name, re.I):
        return "央视频道"
    if re.search(r"卫视", name):
        return "卫视频道"
    if re.search(r"港|澳|台", name):
        return "港澳台"
    if re.search(r"其他|轮播|电影|剧场", name):
        return "其他频道"
    return name or "其他频道"


def valid_url(url: str) -> bool:
    url = (url or "").strip()
    if not re.match(r"^(http|https|rtmp|rtsp)://", url, re.I):
        return False
    if INVALID_URL_PAT.search(url):
        return False
    return True


def parse_txt(text: str):
    """解析 #genre# 分组格式。
    returns: {(group, channel): [url, ...]}
    """
    result = {}
    group = "其他频道"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if "#genre#" in line:
            g = line.split("#genre#")[0].strip().rstrip(",，")
            group = normalize_group(g)
            continue
        if "," not in line:
            continue
        parts = line.split(",", 1)
        ch = normalize_channel(parts[0])
        url = parts[1].strip()
        if not ch or not valid_url(url):
            continue
        result.setdefault((group, ch), [])
        if url not in result[(group, ch)]:
            result[(group, ch)].append(url)
    return result


def parse_m3u(text: str):
    """解析 m3u #EXTINF 格式。
    returns: {(group, channel): [url, ...]}
    """
    result = {}
    cur_name = None
    cur_group = "其他频道"
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#EXTINF"):
            # 提取 group-title="..."
            gm = re.search(r'group-title="([^"]*)"', line)
            cur_group = normalize_group(gm.group(1)) if gm else "其他频道"
            # 频道名在最后一个逗号之后
            if "," in line:
                cur_name = normalize_channel(line.rsplit(",", 1)[1].strip())
            else:
                nm = re.search(r'tvg-name="([^"]*)"', line)
                cur_name = normalize_channel(nm.group(1)) if nm else None
        elif line and not line.startswith("#") and cur_name:
            if valid_url(line):
                result.setdefault((cur_group, cur_name), [])
                if line not in result[(cur_group, cur_name)]:
                    result[(cur_group, cur_name)].append(line)
            cur_name = None
    return result


def fetch_source(url: str) -> str:
    """抓取单个源，返回文本。"""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            text = r.text.lstrip("\ufeff")
            if len(text) < 100:
                raise ValueError("响应过短，疑似无效")
            return text
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)
    raise last_err


def detect_format(text: str) -> str:
    if "#EXTM3U" in text or "#EXTINF" in text:
        return "m3u"
    if "#genre#" in text:
        return "txt"
    # 兜底：看有效行里有没有逗号分隔的 url
    for line in text.splitlines()[:50]:
        if "," in line and re.search(r"http", line):
            return "txt"
    return "unknown"


def write_live_txt(channels, out_path):
    """生成影视仓直播 txt（#genre# 分组格式）。"""
    # 按分组归类
    groups = {}
    for (group, ch), urls in channels.items():
        groups.setdefault(group, []).append((ch, urls))
    # 组内按频道名排序；央视/卫视优先排在前面
    priority = {"央视频道": 0, "卫视频道": 1, "港澳台": 2, "其他频道": 9}
    lines = []
    lines.append("🕘️更新时间,#genre#")
    lines.append(f"{now_cst().strftime('%Y-%m-%d %H:%M:%S')},https://github.com")
    ordered_groups = sorted(groups.keys(), key=lambda g: (priority.get(g, 5), g))
    for group in ordered_groups:
        lines.append(f"📺{group},#genre#")
        for ch, urls in sorted(groups[group], key=lambda x: x[0]):
            for u in urls[:MAX_LINES_PER_CHANNEL]:
                lines.append(f"{ch},{u}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_live_m3u(channels, out_path):
    """生成标准 m3u。"""
    lines = ["#EXTM3U"]
    for (group, ch), urls in sorted(channels.items()):
        for u in urls[:MAX_LINES_PER_CHANNEL]:
            lines.append(f'#EXTINF:-1 tvg-name="{ch}" group-title="{group}",{ch}')
            lines.append(u)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    channels = {}   # {(group, ch): [urls]}
    status_sources = []
    ok_count = 0
    sources = cfg.get("sources", [])

    for src in sources:
        name = src.get("name", "未知")
        url = src.get("url", "")
        entry = {"name": name, "url": url, "ok": False, "channels": 0, "error": None}
        try:
            text = fetch_source(url)
            fmt = detect_format(text)
            if fmt == "m3u":
                parsed = parse_m3u(text)
            elif fmt == "txt":
                parsed = parse_txt(text)
            else:
                raise ValueError("无法识别的直播源格式")
            if not parsed:
                raise ValueError("解析到 0 个频道")
            # 合并到总表
            for key, urls in parsed.items():
                channels.setdefault(key, [])
                for u in urls:
                    if u not in channels[key]:
                        channels[key].append(u)
            entry["ok"] = True
            entry["channels"] = len(parsed)
            entry["format"] = fmt
            ok_count += 1
            print(f"[OK] {name} ({fmt}) -> {len(parsed)} 个频道")
        except Exception as e:  # noqa: BLE001
            entry["error"] = str(e)
            print(f"[FAIL] {name} -> {e}")
        status_sources.append(entry)
        time.sleep(1)

    live_txt = os.path.join(OUTPUT_DIR, "live.txt")
    live_m3u = os.path.join(OUTPUT_DIR, "live.m3u")

    if channels:
        write_live_txt(channels, live_txt)
        write_live_m3u(channels, live_m3u)
        print(f"\n生成 {live_txt}：{len(channels)} 个频道")
    else:
        # 全部失败：沿用缓存
        print("\n[WARN] 本次未抓到任何频道，检查已有缓存文件")
        if not os.path.exists(live_txt):
            print("[ERROR] 无可用缓存，直播文件生成失败")
            return 1

    total_urls = sum(len(v) for v in channels.values())
    status = {
        "updated_at": now_cst().strftime("%Y-%m-%d %H:%M:%S"),
        "ok_sources": ok_count,
        "total_sources": len(sources),
        "channels": len(channels),
        "lines": total_urls,
        "sources": status_sources,
    }
    with open(os.path.join(OUTPUT_DIR, "live_status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    print("=" * 50)
    print(f"直播更新完成：{ok_count}/{len(sources)} 源成功，{len(channels)} 频道，{total_urls} 条线路")
    return 0 if channels else 1


if __name__ == "__main__":
    sys.exit(main())

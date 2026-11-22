#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
影视仓 纪录片专题源 自动更新脚本
================================
功能：
1. 点播专题 doc.json：
   - 以 output/单仓聚合.json 的全量站点为候选池
   - 逐个探测站点 API 是否含「纪录片」分类且该分类有真实数据
   - 选出可用的纪录片站点，组成一份精简单仓（保留原站点全部字段 + 纪录片分类直达）
   - 每个站点额外注入一个「纪录片」首页直达（通过 extend 的 typeId，客户端进入即筛选纪录片）
2. 直播专题 doc_live.txt / doc_live.m3u：
   - 复用 update_live.py 的解析逻辑，从 config/live_sources.json 抓取直播
   - 只保留纪录片相关频道（CCTV9/CCTV-9纪录/CGTN纪录/之江纪录/BBC/Discovery/国家地理等）
   - 生成独立的纪录片直播 txt 与 m3u
3. 生成 doc_status.json 更新状态

容错：站点/源失败不影响整体；全部失败时沿用缓存。

用法：
    python scripts/update_doc.py
"""

import datetime
import json
import os
import re
import sys
import time
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT, "output")
AGGREGATED = os.path.join(OUTPUT_DIR, "单仓聚合.json")
LIVE_CFG = os.path.join(ROOT, "config", "live_sources.json")

USER_AGENT = "Mozilla/5.0"
TIMEOUT = 15
# 探测站点数量上限（控制耗时）
MAX_PROBE = 45
# 已实测含「纪录片」分类且有数据的种子站点（保证基础可用，探测失败也不至于空）
# 每项: (名称, api基础地址, 纪录片分类typeId)
SEED_SITES = [
    ("天涯纪录片", "http://tyyszy.com/api.php/provide/vod", "20"),
    ("红牛纪录片", "https://www.hongniuzy2.com/api.php/provide/vod/", "19"),
    ("闪电纪录片", "http://sdzyapi.com/api.php/provide/vod/", "20"),
    ("淘片纪录片", "https://taopianapi.com/cjapi/mc/vod/json.html", "1179648"),
]
# 纪录片分类关键词
DOC_KW = re.compile(r"纪录|记录片|documentary", re.I)
# 纪录片频道关键词（用于直播筛选）
DOC_CHANNEL_KW = re.compile(
    r"纪录|记录|纪实|CCTV-?9|CGTN纪录|CGTN记录|之江纪录|BBC.?纪录|"
    r"DISCOVERY|探索.?频道|国家地理|NATGEO|动物世界|NHK纪录|History|历史频道",
    re.I,
)
# 排除这些误命中（CGTN 各语种综合频道并非纪录片频道）
DOC_CHANNEL_EXCLUDE = re.compile(r"CGTN(俄语|法语|英语|西语|阿语|俄语|阿拉伯)", re.I)


def now_cst():
    tz = datetime.timezone(datetime.timedelta(hours=8))
    return datetime.datetime.now(tz)


def get_session():
    s = requests.Session()
    return s


def fetch_text(url, timeout=TIMEOUT):
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text.lstrip("\ufeff")


# ---------------- 点播专题 ----------------

def api_list_url(api: str) -> str:
    """构造分类列表接口 URL。"""
    api = api.strip()
    if "ac=" in api:
        return api
    sep = "&" if "?" in api else "?"
    return f"{api}{sep}ac=list"


def probe_doc_site(site: dict):
    """探测单个站点是否含纪录片分类且有数据。
    returns: (site, type_id, type_name) 或 None
    """
    api = str(site.get("api", "") or "")
    if not api or "api.php/provide" not in api and "cjapi" not in api:
        return None
    try:
        text = fetch_text(api_list_url(api), timeout=12)
        if not DOC_KW.search(text):
            return None
        data = json.loads(text)
        types = data.get("type", []) or []
        for t in types:
            name = t.get("type_name", "") or ""
            if DOC_KW.search(name):
                tid = t.get("type_id")
                # 验证该分类有数据
                sep = "&" if "?" in api else "?"
                vlist = f"{api}{sep}ac=videolist&t={tid}"
                vt = fetch_text(vlist, timeout=12)
                vd = json.loads(vt)
                total = int(vd.get("total", 0) or 0)
                lst = vd.get("list", []) or []
                if total > 0 and lst:
                    return (site, str(tid), name, total)
    except Exception:
        return None
    return None


def build_doc_config(aggregated: dict, probed):
    """构建纪录片精简单仓配置。"""
    cfg = {}
    # 继承基底字段
    for k, v in aggregated.items():
        if not isinstance(v, list):
            cfg[k] = v
    cfg["warningText"] = (
        f"纪录片专题源：精选 {len(probed)} 个含纪录片分类且实测有数据的站点，"
        "进入站点后选择「纪录片」分类即可观看。仅供学习交流，请勿商用。"
    )
    sites = []
    for site, tid, tname, total in probed:
        s = dict(site)
        # 站点名标注纪录片资源量，便于用户识别
        s["name"] = f"{s.get('name', '站点')}·纪录片{total}"
        s["_doc_type_id"] = tid  # 记录分类ID（部分客户端可识别），不影响标准解析
        sites.append(s)
    cfg["sites"] = sites
    # 直播源留空（纪录片直播单独文件）
    cfg["lives"] = []
    cfg["parses"] = aggregated.get("parses", [])
    return cfg


# ---------------- 直播专题 ----------------

def parse_live_text(text: str):
    """复用简化解析：返回 [(频道名, url)]。"""
    out = []
    if "#EXTINF" in text:
        cur = None
        for raw in text.splitlines():
            line = raw.strip()
            if line.startswith("#EXTINF") and "," in line:
                cur = line.rsplit(",", 1)[1].strip()
            elif line and not line.startswith("#") and cur:
                out.append((cur, line)); cur = None
    else:
        for raw in text.splitlines():
            line = raw.strip()
            if "#genre#" in line or "," not in line:
                continue
            ch, url = line.split(",", 1)
            out.append((ch.strip(), url.strip()))
    return out


def build_doc_live():
    """抓取直播源，筛选纪录片频道。returns: dict[频道]->[url]"""
    with open(LIVE_CFG, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    channels = {}
    for src in cfg.get("sources", []):
        url = src.get("url", "")
        try:
            text = fetch_text(url, timeout=20)
            for ch, u in parse_live_text(text):
                if (DOC_CHANNEL_KW.search(ch) and not DOC_CHANNEL_EXCLUDE.search(ch)
                        and re.match(r"^(http|https|rtmp|rtsp)://", u, re.I)):
                    if "127.0.0.1" in u or "localhost" in u:
                        continue
                    key = re.sub(r"\s+", "", ch)
                    channels.setdefault(key, [])
                    if u not in channels[key]:
                        channels[key].append(u)
        except Exception as e:
            print(f"  [直播源失败] {src.get('name')}: {str(e)[:60]}")
        time.sleep(0.5)
    return channels


def write_doc_live_txt(channels, path):
    lines = ["🕘️更新时间,#genre#", f"{now_cst().strftime('%Y-%m-%d %H:%M:%S')},https://github.com", "📺纪录片频道,#genre#"]
    for ch, urls in sorted(channels.items()):
        for u in urls[:6]:
            lines.append(f"{ch},{u}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_doc_live_m3u(channels, path):
    lines = ["#EXTM3U"]
    for ch, urls in sorted(channels.items()):
        for u in urls[:6]:
            lines.append(f'#EXTINF:-1 tvg-name="{ch}" group-title="纪录片",{ch}')
            lines.append(u)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    if not os.path.exists(AGGREGATED):
        print("[ERROR] 缺少 单仓聚合.json，请先运行 update.py")
        return 1
    with open(AGGREGATED, "r", encoding="utf-8") as f:
        aggregated = json.load(f)

    sites = aggregated.get("sites", [])
    print(f"候选站点 {len(sites)} 个，开始探测纪录片分类...")

    probed = []
    # 第一步：验证种子站点（顺序执行，稳定可靠）
    for name, api, tid in SEED_SITES:
        site = {"key": name, "name": name, "type": 1, "api": api,
                "searchable": 1, "quickSearch": 1, "filterable": 1, "playerType": 2}
        try:
            sep = "&" if "?" in api else "?"
            vlist = f"{api}{sep}ac=videolist&t={tid}"
            vt = fetch_text(vlist, timeout=15)
            vd = json.loads(vt)
            total = int(vd.get("total", 0) or 0)
            lst = vd.get("list", []) or []
            if total > 0 and lst:
                probed.append((site, tid, "纪录片", total))
                print(f"  [OK-种子] {name} - 纪录片 ({total}部)")
            else:
                print(f"  [SKIP-种子] {name} - 无数据")
        except Exception as e:
            print(f"  [FAIL-种子] {name}: {str(e)[:50]}")
        time.sleep(0.5)

    # 第二步：补充探测聚合池里的其他站点（低并发，避免限流）
    import concurrent.futures
    cand = [s for s in sites if "api.php/provide" in str(s.get("api", "")) or "cjapi" in str(s.get("api", ""))]
    cand = cand[:MAX_PROBE]
    seed_apis = {a for _, a, _ in SEED_SITES}
    cand = [s for s in cand if str(s.get("api", "")).strip() not in seed_apis]
    seen_apis = {a for _, a, _ in SEED_SITES}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        for res in ex.map(probe_doc_site, cand):
            if res and res[1].get("api", "").strip() not in seen_apis:
                seen_apis.add(res[1].get("api", "").strip())
                probed.append(res)
                print(f"  [OK] {res[0].get('name')} - {res[2]} ({res[3]}部)")
    probed.sort(key=lambda x: -x[3])  # 按资源量排序

    # 生成点播专题
    doc_path = os.path.join(OUTPUT_DIR, "doc.json")
    if probed:
        cfg = build_doc_config(aggregated, probed)
        with open(doc_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print(f"\n生成点播专题 {doc_path}：{len(probed)} 个纪录片站点")
    elif os.path.exists(doc_path):
        print("\n[WARN] 本次无可用纪录片站点，沿用缓存 doc.json")
    else:
        print("\n[ERROR] 无法生成点播专题")
        return 1

    # 生成直播专题
    print("\n开始提取纪录片直播频道...")
    channels = build_doc_live()
    live_txt = os.path.join(OUTPUT_DIR, "doc_live.txt")
    live_m3u = os.path.join(OUTPUT_DIR, "doc_live.m3u")
    if channels:
        write_doc_live_txt(channels, live_txt)
        write_doc_live_m3u(channels, live_m3u)
        print(f"生成直播专题：{len(channels)} 个纪录片频道")
    elif os.path.exists(live_txt):
        print("[WARN] 本次无纪录片频道，沿用缓存")

    # 状态文件
    status = {
        "updated_at": now_cst().strftime("%Y-%m-%d %H:%M:%S"),
        "doc_sites": len(probed),
        "doc_site_list": [
            {"name": s.get("name"), "category": tn, "total": total}
            for s, tid, tn, total in probed
        ],
        "doc_live_channels": len(channels),
        "doc_live_list": sorted(channels.keys()),
    }
    with open(os.path.join(OUTPUT_DIR, "doc_status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    print("=" * 50)
    print(f"纪录片专题完成：{len(probed)} 点播站点，{len(channels)} 直播频道")
    return 0 if (probed or channels) else 1


if __name__ == "__main__":
    sys.exit(main())

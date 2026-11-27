# 我的影视仓 / TVBox 专属源

聚合肥猫、饭太硬、王二小、老刘备、小马、讴歌、4K小盒子等公开影视仓配置，通过 **GitHub Actions 每天自动更新**，结果提交回本仓库，供影视仓 / TVBox / OK影视随时拉取。

> 所有配置均来自互联网公开分享，版权归原作者所有；本仓库仅做聚合与镜像，仅供学习交流，请勿商用。

![TVBox 配置状态](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/junhong044/tvbox-ysc-config/main/output/shield.json)

## 一、源可用性状态

<!-- STATUS_START -->
> 🔄 最近更新：2026-11-27 10:49:24（北京时间） · 成功 **8/10** 个源

| 配置源 | 状态 | 使用地址 |
| --- | --- | --- |
| 肥猫 | ✅ 成功 | `https://6296.kstore.vip/facat.json` |
| 饭太硬 | ❌ 失败 | HTTPConnectionPool(host='www.xn--sss604efuw.xyz', port=80... |
| 王二小 | ✅ 成功 | `https://d.kstore.dev/download/9280/wex.json` |
| 老刘备 | ✅ 成功 | `https://raw.liucn.cc/box/m.json` |
| 小马 | ✅ 成功 | `https://szyyds.cn/tv/x.json` |
| 讴歌 | ❌ 失败 | HTTPSConnectionPool(host='xn--dkw0c.v.nxog.top', port=443... |
| 4K小盒子 | ✅ 成功 | `http://xhztv.top/4k.json` |
| 小盒子单仓 | ✅ 成功 | `http://xhztv.top/xhz` |
| 拾光多仓 | ✅ 成功 | `http://xmbjm.fh4u.org/dc.txt` |
| 挺好分享多仓 | ✅ 成功 | `http://ztha.top/TVBox/GYCK.json` |
<!-- STATUS_END -->

## 二、订阅地址

| 类型 | 地址 | 说明 |
| --- | --- | --- |
| 点播-多仓订阅（推荐） | `https://gh-proxy.org/https://raw.githubusercontent.com/junhong044/tvbox-ysc-config/main/output/多仓订阅.json` | App 内可在各源之间切换 |
| 点播-单仓聚合 | `https://gh-proxy.org/https://raw.githubusercontent.com/junhong044/tvbox-ysc-config/main/output/单仓聚合.json` | 所有源站点合并成一个，开箱即用 |
| **电视直播 txt（推荐）** | `https://cdn.jsdelivr.net/gh/junhong044/tvbox-ysc-config@main/output/live.txt` | 165 频道、央视/卫视/港澳台/地方台，每天聚合更新 |
| 电视直播 m3u | `https://cdn.jsdelivr.net/gh/junhong044/tvbox-ysc-config@main/output/live.m3u` | 带台标/分组，兼容 VLC 等播放器 |
| **纪录片点播（专题）** | `https://cdn.jsdelivr.net/gh/junhong044/tvbox-ysc-config@main/output/doc.json` | 精选含「纪录片」分类且实测有数据的站点，进入站点选「纪录片」分类 |
| **纪录片直播（专题）** | `https://cdn.jsdelivr.net/gh/junhong044/tvbox-ysc-config@main/output/doc_live.txt` | CCTV9纪录/CGTN纪录/之江纪录等，填「直播地址」栏 |
| 纪录片直播 m3u | `https://cdn.jsdelivr.net/gh/junhong044/tvbox-ysc-config@main/output/doc_live.m3u` | 纪录片频道 m3u 版 |
| 纪录片状态 | `https://raw.githubusercontent.com/junhong044/tvbox-ysc-config/main/output/doc_status.json` | 纪录片站点/频道更新状态（机器可读） |
| 直播状态 | `https://raw.githubusercontent.com/junhong044/tvbox-ysc-config/main/output/live_status.json` | 直播源更新时间与频道数（机器可读） |
| 点播状态文件 | `https://raw.githubusercontent.com/junhong044/tvbox-ysc-config/main/output/status.json` | 各源更新时间与结果（机器可读） |

国内若 `gh-proxy.org` 失效，可改用以下任一加速前缀，或直接裸连 raw：
- `https://gh-proxy.com/https://raw.githubusercontent.com/...`
- `https://fastly.jsdelivr.net/gh/junhong044/tvbox-ysc-config@main/output/多仓订阅.json`

## 三、使用方法

- **看点播**：影视仓 / TVBox → 设置 → **配置地址** → 粘贴上面「点播-多仓订阅」地址 → 确定 → 返回首页。
- **看电视直播**：影视仓 / TVBox → 设置 → **直播地址** → 粘贴上面「电视直播 txt」地址 → 确定 → 返回首页 → 进入直播栏目。
- **看纪录片**：把「纪录片点播（专题）」填进**配置地址**（进入站点后选「纪录片」分类），把「纪录片直播（专题）」填进**直播地址**，即可点播+直播双管齐下。

## 四、自动更新机制

- 每天北京时间 **10:00** 和 **22:00** 自动更新点播与直播（UTC 02:00 / 14:00）。
- 也可在 Actions → Auto Update TVBox Configs → Run workflow 手动触发。
- 结果自动提交回 `main` 分支，README 状态表与徽章同步刷新，使用内置 GITHUB_TOKEN，无需任何密钥。
- 脚本自动从 `git remote origin` 识别仓库名，无需手动修改；失败源自动回退上次缓存。
- 直播脚本（`scripts/update_live.py`）会抓取多个上游、归一化合并去重、过滤无效线路，生成 `live.txt` / `live.m3u`。
- 纪录片脚本（`scripts/update_doc.py`）会实测各站点的「纪录片」分类是否有数据，生成专题点播 `doc.json`；并从直播源提取纪录片频道生成 `doc_live.txt` / `doc_live.m3u`。

## 五、自定义配置源

编辑 `config/sources.json`，按如下格式增删改：

```json
{
  "id": "mysource",
  "name": "我的源",
  "urls": [
    "https://example.com/tv",
    "https://backup.example.com/tv"
  ]
}
```

- `id`：输出文件名（建议英文小写）。
- `name`：在多仓订阅与状态表中展示的名字。
- `urls`：依次尝试的地址，第一个成功的被采用（主地址在前、备用在后）。

推送后会自动触发一次更新。

### 自定义直播源

编辑 `config/live_sources.json`，按如下格式增删改（支持 `#genre#` 的 txt 与 `#EXTINF` 的 m3u，脚本自动识别）：

```json
{
  "name": "我的直播源",
  "url": "https://example.com/live.txt"
}
```

## 六、本地手动运行

```bash
pip install -r requirements.txt
python scripts/update.py          # 更新点播配置
python scripts/update_live.py     # 更新电视直播
python scripts/update_doc.py      # 更新纪录片专题
```

## 七、免责声明

本项目仅用于学习、测试与个人使用；聚合的接口资源来自互联网公开分享，版权归原作者所有。若涉及侵权，请联系删除相应内容。

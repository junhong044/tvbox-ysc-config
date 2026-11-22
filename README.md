# 我的影视仓 / TVBox 专属源

聚合肥猫、饭太硬、王二小、老刘备、小马、讴歌、4K小盒子等公开影视仓配置，通过 **GitHub Actions 每天自动更新**，结果提交回本仓库，供影视仓 / TVBox / OK影视随时拉取。

> 所有配置均来自互联网公开分享，版权归原作者所有；本仓库仅做聚合与镜像，仅供学习交流，请勿商用。

![TVBox 配置状态](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/YOUR_USERNAME/tvbox-ysc-config/main/output/shield.json)

## 一、源可用性状态

<!-- STATUS_START -->
> 🔄 最近更新：2026-11-23 01:18:45（北京时间） · 成功 **8/10** 个源

| 配置源 | 状态 | 使用地址 |
| --- | --- | --- |
| 肥猫 | ✅ 成功 | `https://6296.kstore.vip/facat.json` |
| 饭太硬 | ❌ 失败 | 502 Server Error: Bad Gateway for url: http://www.xn--sss... |
| 王二小 | ✅ 成功 | `https://9280.kstore.vip/newwex.json` |
| 老刘备 | ✅ 成功 | `https://raw.liucn.cc/box/m.json` |
| 小马 | ✅ 成功 | `https://szyyds.cn/tv/x.json` |
| 讴歌 | ❌ 失败 | HTTPSConnectionPool(host='xn--dkw0c.v.nxog.top', port=443... |
| 4K小盒子 | ✅ 成功 | `http://xhztv.top/4k.json` |
| 小盒子单仓 | ✅ 成功 | `http://xhztv.top/xhz` |
| 拾光多仓 | ✅ 成功 | `http://xmbjm.fh4u.org/dc.txt` |
| 挺好分享多仓 | ✅ 成功 | `http://ztha.top/TVBox/GYCK.json` |
<!-- STATUS_END -->

## 二、订阅地址（部署后替换 YOUR_USERNAME 为你的 GitHub 用户名）

| 类型 | 地址 | 说明 |
| --- | --- | --- |
| 多仓订阅（推荐） | `https://gh-proxy.org/https://raw.githubusercontent.com/YOUR_USERNAME/tvbox-ysc-config/main/output/多仓订阅.json` | App 内可在各源之间切换 |
| 单仓聚合 | `https://gh-proxy.org/https://raw.githubusercontent.com/YOUR_USERNAME/tvbox-ysc-config/main/output/单仓聚合.json` | 所有源站点合并成一个，开箱即用 |
| 状态文件 | `https://raw.githubusercontent.com/YOUR_USERNAME/tvbox-ysc-config/main/output/status.json` | 各源更新时间与结果（机器可读） |

国内若 `gh-proxy.org` 失效，可改用以下任一加速前缀，或直接裸连 raw：
- `https://gh-proxy.com/https://raw.githubusercontent.com/...`
- `https://fastly.jsdelivr.net/gh/YOUR_USERNAME/tvbox-ysc-config@main/output/多仓订阅.json`

## 三、使用方法

影视仓 / TVBox → 设置 → 配置地址 → 粘贴上面「多仓订阅」地址 → 确定 → 返回首页。

## 四、自动更新机制

- 每天北京时间 **10:00** 和 **22:00** 自动更新（UTC 02:00 / 14:00）。
- 也可在 Actions → Auto Update TVBox Configs → Run workflow 手动触发。
- 结果自动提交回 `main` 分支，README 状态表与徽章同步刷新，使用内置 GITHUB_TOKEN，无需任何密钥。
- 脚本自动从 `git remote origin` 识别仓库名，无需手动修改；失败源自动回退上次缓存。

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

## 六、本地手动运行

```bash
pip install -r requirements.txt
python scripts/update.py
```

## 七、免责声明

本项目仅用于学习、测试与个人使用；聚合的接口资源来自互联网公开分享，版权归原作者所有。若涉及侵权，请联系删除相应内容。

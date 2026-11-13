# 素材来源（云端环境实测，2026-11）

## 能用的（无水印）

| 站点 | 怎么拿 | 画质 | 备注 |
|---|---|---|---|
| Mixkit | `scripts/scrape_mixkit.py` 按关键词抓分类页 `mixkit.co/free-stock-video/<kw>/?page=N`。下载 `https://assets.mixkit.co/videos/<id>/<id>-{2160,1080,720}.mp4`，按顺序尝试 | 老素材免费只有 720p，新素材有 1080p/4K | 请求太快会被 Cloudflare 挡（返回 "Just a moment"），每页间隔 6 秒，被挡就等 1 分钟 |
| Coverr | `scripts/scrape_coverr.py` 抓 `coverr.co/s?q=<词>`，下载 `https://cdn.coverr.co/videos/<slug>/1080p.mp4` | 1080p | 搜索不太准；slug 里带 `premium` 或 `user-ai` 的跳过 |

Mixkit 好用的分类词：flowers, flower, blossom, cherry-blossom, garden, lotus, field, meadow, grass, spring, sunrise, lantern, temple, china, mountain, fog, waterfall, aerial, drone。
Mixkit 缩略图：`https://assets.mixkit.co/videos/<id>/<id>-thumb-720-0.jpg`。
Coverr 缩略图：`https://cdn.coverr.co/videos/<slug>/thumbnail?width=385`。

## 不能用

| 站点 | 原因 |
|---|---|
| Vecteezy、iStock、Shutterstock | 免费预览**带水印**（画面中间的半透明 logo），分辨率也只有 576p。用户明确说过水印「一定要去掉，非常影响画面观感」。不要用这些预览，也不要去抹水印：抹水印是绕开版权保护，不做 |
| YouTube | 服务器 IP 被要求登录验证（"Sign in to confirm you're not a bot"） |
| B 站 | 搜索接口返回 412 |
| Pexels、Pixabay、Videezy、Vimeo | Cloudflare 403 |
| Wikimedia Commons | 接口限流，中国风景视频很少 |

## 找不到合适素材时

免费站的中国风素材很少（例如牡丹园、紫藤、元阳梯田）。这时候别用不对题的素材凑数，直接告诉用户缺哪几类画面，请用户提供素材文件，或者让用户去 Vecteezy 用免费账号下载无水印原片再发过来。

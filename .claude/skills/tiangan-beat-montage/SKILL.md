---
name: tiangan-beat-montage
description: 制作「你以为的X / 实际上的X」天干系列卡点短视频（抖音、视频号、小红书的国学账号）：前 2 秒是这个天干最小的日常样子，黑屏翻转成「实际上的X」，BGM 一爆就是每拍一刀、色彩鲜艳的盛大画面蒙太奇。用户提到十天干（甲乙丙丁戊己庚辛壬癸）任意一个做「你以为的 / 实际上的」视频、对标「你以为的庚金」、要做天干卡点视频、或给了 BGM 让照着某个天干视频做时，都用这个 skill，哪怕用户没说「卡点」两个字。
---

# 天干卡点短视频：你以为的 X / 实际上的 X

对标爆款《你以为的庚金》：24 秒，41 个镜头，开头一个小画面骗你，黑屏一翻，音乐一爆，每拍一个盛大画面。涨粉快靠的是三件事：**题对**（每个画面都一眼看出是这个天干）、**卡准**（每一刀都在鼓点上）、**好看**（高饱和、高反差、没有水印）。三件里错一件，用户就会打回来重做。

## 先读这两份

- `references/tiangan_imagery.md`：十天干意象对照表，每个天干「可以用 / 不能用」。**选素材前必读。**
- `references/style_spec.md`：配色、光线、质感、字幕、节奏、构图的具体数值。

需要找素材时再读 `references/sources.md`（哪些站能用、哪些被挡、哪些带水印）。

## 用户纠正过的错误（不要再犯）

1. **意象选错。** 做乙木时用了参天大树、仰拍森林、竹海、榕树气根、苔藓树干，用户指出：「乙木不是树，乙木是花草，要找比较盛大的花草，呈现欣欣繁荣之象。」树是甲木。阴阳同五行的两个天干（甲/乙、丙/丁、戊/己、庚/辛、壬/癸）最容易混。每个镜头都要能回答「主体为什么属于这个天干」，答不上来就换掉。没把握的天干，先把意象列表给用户确认再开工。
2. **相邻镜头重复。** 两条不同素材都是「绿色树林仰拍」，放在一起看起来就是同一个画面放了两次。换素材文件不等于换画面：相邻两个镜头的主体、景别或主色至少要有一样明显不同。`check_shots.py` 会自动查，但最后还是要自己看一遍镜头预览图。
3. **带水印的素材。** 用了 Vecteezy 的免费预览，画面中间有半透明 logo，用户说「一定要去掉，非常影响画面观感」。只用无水印素材（Mixkit、Coverr、用户自己给的），也不要去抹水印。
4. **没卡上点。** 照搬对标视频的切点，结果有一刀落在两拍中间（10.46s，前一拍 10.18、后一拍 10.62）。切点必须从 BGM 本身分析出来，渲染完再用成片验证。
5. **标题多出 2 帧。** 用帧号 `n` 控制叠加的显示时段，标题在黑屏上多留了 2 帧。用时间 `t` 控制（`render.py` 已修好）。

## 流程

工作目录用 scratchpad，最终成片和镜头表放进 `作品/<日期>_<天干>/`。

### 1. 确认输入

需要：天干、BGM 文件、账号水印名。英文副标题可以自己写一句贴合这个天干的（例如乙木 `SOFT AS A VINE, IT BINDS THE MOUNTAINS AND RIVERS.`），写完给用户看。
对标原片是 16:9 横屏，默认出横屏，竖屏要用户确认后再做（安全区见 style_spec）。

### 2. 分析 BGM，定切点

```bash
python3 scripts/beats.py BGM.mp3 WORK/plan.json
```

它会打印每一拍的强弱，并自动生成切点：
- 钩子在 1.5–2.2 秒内最强的鼓点结束
- 自动找 Drop，标题在 Drop 前 0.25 秒消失
- Drop 之后只在强拍切，弱拍跳过让镜头多停；超过 2.5 拍的空档，如果中间有够强的鼓点（反拍重音）就补一刀；音乐停顿处的弱鼓点不补，保留长镜头

看一遍打印的表：音乐停顿或过门处应该自然形成一个 2–3 拍的长镜头。对标 BGM 实测 129.2 BPM，拍子会轻微漂移，所以不要用固定网格。

### 3. 列镜头表，再找素材

先按 `tiangan_imagery.md` 列出色彩段落和每段要什么画面，再去找素材。不要先搜一堆素材再往里凑。

```bash
python3 scripts/footage.py search WORK mixkit flowers,cherry-blossom,lotus,field,meadow --pages 2
python3 scripts/footage.py search WORK coverr "flower field,peony,lavender"
python3 scripts/footage.py sheets WORK --include "flower,blossom,tulip,lavender,meadow,field" --exclude "tree,forest,bamboo,jungle,roots"
```

`--include` 只留名字里带这些词的素材（素材库上千条时必用，不然要翻几十页），`--exclude` 去掉不对题的。逐张看 `WORK/sheets/` 里的预览图，按画面挑，不要按素材名挑。挑好后：

```bash
python3 scripts/footage.py get WORK CLIPS k12440 k48889 c17 ...
```

某一类画面找不到合适的，就别用不对题的素材凑数，告诉用户缺哪几类，请用户提供素材。

### 4. 写 plan.json 的 shots

`beats.py` 生成的 plan.json 里，`shots` 要补全，个数等于切点段数。格式见 `render.py` 开头的注释。第 0 个是钩子，第 1 个是 `black`。每个镜头都要写：
- `subject`：画面主体，例如「牡丹特写」「油菜花海航拍」
- `why`：为什么属于这个天干，例如「草本花，乙木」

镜头排布：
- 每段 3–7 个镜头，同段色调一致，段与段之间换主色
- 景别交替：航拍大场面和特写穿插，特写不要连着用
- 同一条素材整片只用一次
- 最后一段是整片最盛大的画面

### 5. 检查 → 渲染 → 再检查

```bash
bash scripts/setup_fonts.sh WORK/fonts
node scripts/titles.js WORK/titles WORK/fonts "乙木" "ENGLISH SUBTITLE" "账号水印"
python3 scripts/check_shots.py WORK/plan.json                      # 渲染前：重复素材、相邻同主体
python3 scripts/render.py WORK/plan.json WORK/titles WORK OUT.mp4
python3 scripts/check_shots.py WORK/plan.json WORK/seg WORK/shots.jpg  # 渲染后：相邻画面相似度 + 镜头预览图
python3 scripts/verify_sync.py OUT.mp4 WORK/plan.json               # 每个切点对鼓点
```

`titles.js` 需要 Playwright（环境里已装好，用 node 跑时如果找不到模块，在装有 playwright 的目录下运行）。

两个检查都要 PASS 才能交付：
- `check_shots.py`：没有重复素材，没有相邻相似画面
- `verify_sync.py`：所有切点都找到、没有多余切点、每一刀和鼓点的误差 ≤ 17ms

然后**亲眼看 `shots.jpg`**，逐个镜头对照意象表问一遍「这是不是这个天干」，并确认画面上没有任何水印或 logo。脚本只能查重复和卡点，查不了意象对不对。

### 6. 交付

用 SendUserFile 发成片和镜头表（每个镜头的时间、主体、为什么属于这个天干、素材来源链接）。在回复里说明：
- 每个切点和鼓点的最大误差
- 哪些画面类别是用替代素材顶上的
- 还需要用户确认的地方（水印名、竖屏版等）

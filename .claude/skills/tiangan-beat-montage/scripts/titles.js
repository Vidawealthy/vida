// Render the title overlays as transparent 1920x1080 PNGs with headless Chromium.
// Usage: node titles.js OUT_DIR FONTS_DIR "乙木" "ENGLISH SUBTITLE" "WATERMARK"
// FONTS_DIR must contain the npm packages lxgw-wenkai-webfont and @fontsource/playfair-display
// (setup_fonts.sh puts them there).
// Outputs: hook.png, overlay.png (disclaimer + watermark), real_000..real_015.png (blur-in frames).
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path');
const [outDir, fontsDir, stem, english, watermark] = process.argv.slice(2);
if (!watermark) { console.error('usage: node titles.js OUT_DIR FONTS_DIR STEM ENGLISH WATERMARK'); process.exit(1); }
fs.mkdirSync(outDir, {recursive: true});
const find = (re) => { const d = fs.readdirSync(fontsDir).find(n => re.test(n)); if (!d) throw new Error('missing font package ' + re); return path.resolve(fontsDir, d); };
const wk = find(/^lxgw-wenkai-webfont/), pf = find(/playfair-display/);
const html = `<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="file://${wk}/lxgwwenkai-bold.css">
<style>
@font-face{font-family:PF;src:url('file://${pf}/files/playfair-display-latin-500-normal.woff2')}
html,body{margin:0;width:1920px;height:1080px;background:transparent;overflow:hidden}
.zh{position:absolute;left:0;width:1920px;text-align:center;font-family:'LXGW WenKai';font-weight:bold;font-size:110px;line-height:1;color:#fff}
.en{position:absolute;left:0;width:1920px;text-align:center;font-family:PF;font-size:23px;letter-spacing:.62em;color:rgba(255,255,255,.88);text-transform:uppercase}
.sh{text-shadow:0 2px 6px rgba(0,0,0,.6),0 0 18px rgba(0,0,0,.35)}
.disc{position:absolute;left:38px;top:34px;font-family:'LXGW WenKai';font-weight:bold;font-size:25px;color:rgba(255,255,255,.86);text-shadow:0 1px 3px rgba(0,0,0,.5)}
.wm{position:absolute;left:0;width:1920px;top:1034px;text-align:center;font-family:PF;font-size:16px;letter-spacing:.18em;color:rgba(255,255,255,.7)}
.c{display:inline-block}
</style></head><body><div id="root"></div></body></html>`;
const page = path.join(outDir, '_titles.html'); fs.writeFileSync(page, html);
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({viewport: {width: 1920, height: 1080}});
  await p.goto('file://' + path.resolve(page));
  const shot = async (inner, name) => {
    await p.evaluate(h => { document.getElementById('root').innerHTML = h; }, inner);
    await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(250);
    await p.screenshot({path: path.join(outDir, name), omitBackground: true});
  };
  const L1 = 440, L2 = 560, EN = 704, line2 = `-${stem}-`;
  await shot(`<div class="zh sh" style="top:${L1}px">你以为的</div><div class="zh sh" style="top:${L2}px">${line2}</div><div class="en sh" style="top:${EN}px">${english}</div>`, 'hook.png');
  await shot(`<div class="disc">内容仅供娱乐参考｜无不良引导｜理性观看</div><div class="wm">${watermark}</div>`, 'overlay.png');
  const l1 = [...'实际上的'], l2 = [...line2], ST = 2, DUR = 8, N = ST * (Math.max(l1.length, l2.length) - 1) + DUR + 1;
  const span = (c, k, f) => {
    const t = Math.min(1, Math.max(0, (f - k * ST) / DUR)), e = 1 - Math.pow(1 - t, 3), bl = (1 - e) * 28, id = `hb${k}_${f}`;
    return `<span class="c" style="opacity:${e.toFixed(3)};filter:url(#${id})">${c}</span><svg width="0" height="0" style="position:absolute"><filter id="${id}" x="-50%" width="200%"><feGaussianBlur stdDeviation="${bl.toFixed(2)} ${(bl * 0.12).toFixed(2)}"/></filter></svg>`;
  };
  for (let f = 0; f <= N; f++)
    await shot(`<div class="zh" style="top:${L1}px;color:#E8E8E8">${l1.map((c, k) => span(c, k, f)).join('')}</div><div class="zh" style="top:${L2}px;color:#E8E8E8">${l2.map((c, k) => span(c, k, f)).join('')}</div>`, `real_${String(f).padStart(3, '0')}.png`);
  fs.writeFileSync(path.join(outDir, 'reveal_frames.txt'), String(N + 1));
  console.log('titles written, reveal frames', N + 1); await b.close();
})();

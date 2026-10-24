// かしこさ Lv ごとに、同じ罠配置で「罠が何回発動したか」「被弾数」「撃退数」を比べる
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const p = await (await browser.newContext({ locale: 'ja-JP' })).newPage();
  const errors = [];
  p.on('pageerror', e => errors.push(String(e)));
  await p.route('**/game.html', async route => {
    const res = await route.fetch(); let body = await res.text();
    body = body.replace("if (location.hostname === '127.0.0.1') window.__wanakan", "window.__sim = { update, startWave, beginDefense, setP: v => paused = v, get G(){return G}, set G(v){G=v}, makeRun }; window.__wanakan");
    route.fulfill({ response: res, body, headers: { ...res.headers(), 'content-type': 'text/html; charset=utf-8' } });
  });
  await p.goto((process.env.GAME_URL || 'http://127.0.0.1:8766/src/game.html'));
  await p.click('#btnStart');
  const R = await p.evaluate(() => {
    const S = window.__sim; S.setP(true);
    const layout = [['bear', 3, 4, 1], ['rock', 4, 3, 1], ['spring', 11, 5, 1], ['fire', 10, 3, 1], ['bear', 7, 2, 1]];
    const out = {};
    for (const L of [0, 2, 5]) {
      let triggers = 0, hurt = 0, kills = 0, wipes = 0, n = 12;
      for (let k = 0; k < n; k++) {
        const G = S.makeRun('play'); S.G = G; G.up.smart = L; G.hp = 99;
        S.startWave(3);
        for (const [type, x, y, dir] of layout) G.traps.set(x + ',' + y, { type, x, y, dir, cd: 0, cdMax: 1, snap: 0, anim: 0, at: 0, bonus: false });
        G.mana = 0; // 新しく置かせない
        for (let i = 0; i < 60 * 4; i++) S.update(1 / 60); // 準備中に待ち場所へ
        S.setP(false); S.beginDefense(); S.setP(true);
        let t = 0; const prev = new Map();
        while (G.clearT < 0 && t < 80) {
          G.mana = 0;
          S.update(1 / 60); t += 1 / 60;
          for (const [key, tr] of G.traps) { if (tr.cd > (prev.get(key) || 0) + .5) triggers++; prev.set(key, tr.cd); }
        }
        hurt += 99 - G.hp; kills += G.kills; if (G.bannerTitle === '全滅させた！') wipes++;
      }
      out['Lv' + (L + 1)] = { 罠発動: (triggers / n).toFixed(1), 被弾: (hurt / n).toFixed(1), 撃退: (kills / n).toFixed(1), 全滅クリア: wipes + '/' + n };
    }
    return out;
  });
  console.log(JSON.stringify(R, null, 1));
  console.log('pageerror:', errors.length ? errors : 'なし');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });

// 逃げる子4人 × 罠の組み合わせを、罠を自動で置くボットに遊ばせて、到達した夜・クリア率・得点を比べる
// 使い方: python -m http.server 8766 --bind 127.0.0.1（リポジトリ直下）→ node tools/sim/sim_balance.js [1組あたりの回数]
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const RUNS = +(process.argv[2] || 3);
const LOADOUTS = {
  定番: ['bear', 'spring', 'rock', 'fire'],
  足止め: ['bear', 'ice', 'blade', 'bell'],
  毒と氷: ['ice', 'poison', 'fire', 'spring'],
  一撃: ['bear', 'rock', 'blade', 'poison'],
  誘い込み: ['bell', 'poison', 'fire', 'ice'],
};
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const p = await (await browser.newContext()).newPage();
  const errors = [];
  p.on('pageerror', e => errors.push(String(e)));
  await p.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/src/game.html');
  const results = [];
  for (const char of ['lily', 'mina', 'noel', 'cecil']) {
    for (const [lname, lo] of Object.entries(LOADOUTS)) {
      const r = await p.evaluate(({ char, lo, RUNS }) => {
        const A = window.__wanakan.api, W = window.__wanakan;
        const COLS = 15, DT = 1 / 30;
        const out = [];
        for (let run = 0; run < RUNS; run++) {
          A.startRun(char, lo); A.setPaused(true);
          let G = W.G, nextPlace = 0, guard = 0;
          const tileFoe = (x, y) => G.foes.some(f => !f.dead && Math.round(f.x) === x && Math.round(f.y) === y);
          // 侵入者がたどる道（目的地の BFS を逆にたどる）
          const pathFrom = (sx, sy, field, n) => {
            const path = []; let x = sx, y = sy, d = field[x + y * COLS];
            while (d > 0 && path.length < n) {
              const st = A.DIRS.find(([dx, dy]) => field[x + dx + (y + dy) * COLS] === d - 1);
              if (!st) break; x += st[0]; y += st[1]; d--; path.push([x, y, st]);
            }
            return path;
          };
          const botPlace = () => {
            if (G.traps.size >= A.stat.limit()) return;
            const h = G.hero, hx = Math.round(h.x), hy = Math.round(h.y);
            const field = A.bfs(hx, hy, A.foeWalk);
            let cands = [];
            const live = G.foes.filter(f => !f.dead && !f.fly);
            if (live.length) {
              live.sort((a, b) => field[a.tx + a.ty * COLS] - field[b.tx + b.ty * COLS]);
              for (const f of live.slice(0, 2)) cands.push(...pathFrom(f.tx, f.ty, field, 5).slice(1, 5));
            } else {
              const doors = [[0, 4], [14, 5], [7, 0]].slice(0, Math.min(3, G.wave));
              for (const [dx, dy] of doors) cands.push(...pathFrom(dx, dy, field, 12).slice(2, 9));
            }
            cands = cands.filter(([x, y]) => A.canPlace(x, y) && !G.traps.has(x + ',' + y) && !tileFoe(x, y) && Math.abs(x - hx) + Math.abs(y - hy) > 1);
            if (!cands.length) return;
            const [x, y, st] = cands[0];
            const order = G.loadout.slice().sort(() => Math.random() - .5);
            const type = order.find(t => A.trapCost(t) <= G.mana);
            if (!type) return;
            if (type === 'spring') { const dx = Math.sign(x - hx), dy = Math.sign(y - hy); G.springDir = Math.abs(x - hx) >= Math.abs(y - hy) ? (dx > 0 ? 1 : 3) : (dy > 0 ? 2 : 0); }
            if (type === 'blade' && st) { const back = A.DIRS.findIndex(([a, b]) => a === -st[0] && b === -st[1]); G.springDir = back >= 0 ? back : 1; }
            G.selected = type; A.placeTrap(x, y, type);
          };
          const botSkill = () => {
            if (G.skillCd > 0 || G.phase === 0) return;
            A.setPaused(false); try { botSkillInner(); } finally { A.setPaused(true); } // useSkill は一時停止中だと動かない
          };
          const botSkillInner = () => {
            const h = G.hero, live = G.foes.filter(f => !f.dead && !f.fly);
            if (!live.length) return;
            const near = live.filter(f => Math.max(Math.abs(f.x - h.x), Math.abs(f.y - h.y)) <= 2.2);
            if (char === 'lily' && [...G.traps.values()].filter(t => t.cd > 1).length >= 3) A.useSkill();
            else if (char === 'mina' && (G.mana < 40 || [...G.traps.values()].filter(t => t.cd > 1).length >= 3)) A.useSkill();
            else if (char === 'noel' && near.length) A.useSkill();
            else if (char === 'cecil') {
              const tgt = live.map(f => [f, live.filter(g => Math.max(Math.abs(g.x - f.x), Math.abs(g.y - f.y)) <= 1.2).length]).sort((a, b) => b[1] - a[1])[0];
              const close = Math.abs(tgt[0].x - h.x) + Math.abs(tgt[0].y - h.y) <= 5;
              if (tgt[1] >= 2 || close) { A.useSkill(); A.doSkill(Math.round(tgt[0].x), Math.round(tgt[0].y)); }
            }
          };
          const PRI = ['limit', 'smart', 'power', 'regen', 'cd', 'hp', 'maxMana', 'speed'];
          while (G.state !== 'over' && guard++ < 30 * 60 * 25) {
            if (G.state === 'shop') {
              let bought = true;
              while (bought) {
                bought = false;
                for (const id of PRI) {
                  const u = A.UPS.find(u => u.id === id), lv = G.up[id];
                  if (lv >= u.max) continue;
                  const cost = A.upCost(u, lv);
                  if (G.soul >= cost) { G.soul -= cost; G.up[id]++; if (id === 'hp') G.hp++; if (id === 'maxMana') G.mana = A.stat.maxMana(); bought = true; break; }
                }
              }
              A.startWave(G.wave + 1); continue;
            }
            if (G.phase === 0 && G.time > 0 && G.prepT < 17) { A.setPaused(false); A.beginDefense(); A.setPaused(true); }
            if (G.time >= nextPlace) { botPlace(); nextPlace = G.time + .4; }
            botSkill();
            for (const dv of G.devices) { // 館の仕掛けも使う
              if (dv.cd > 0) continue;
              const n = G.foes.filter(f => !f.dead && !f.fly && A.deviceReach(dv, Math.round(f.x), Math.round(f.y))).length;
              if (n >= 1) A.activateDevice(dv);
            }
            A.update(DT);
            G = W.G;
          }
          out.push({ skills: G.skillUses || 0, kills: G.kills, traps: G.traps.size, trig: [...G.traps.values()].map(t => t.type).join('+'), wave: G.wave, won: G.bannerTitle === '全滅させた！' || G.bannerTitle === '夜明け' ? G.wave >= 10 && G.hp > 0 : false, score: G.score, hp: G.hp, time: Math.round(G.time) });
        }
        return out;
      }, { char, lo, RUNS });
      results.push({ char, loadout: lname, runs: r });
      const avgW = r.reduce((a, b) => a + b.wave, 0) / r.length, wins = r.filter(x => x.wave >= 10 && x.hp > 0).length, avgS = Math.round(r.reduce((a, b) => a + b.score, 0) / r.length);
      if (process.env.DETAIL) console.log(JSON.stringify(r));
      console.log(`${char.padEnd(6)} ${lname.padEnd(5)} 到達夜 ${avgW.toFixed(1)}  クリア ${wins}/${r.length}  平均得点 ${avgS}`);
    }
  }
  const by = key => {
    const m = {};
    for (const x of results) for (const r of x.runs) { const k = x[key]; (m[k] ||= []).push(r); }
    for (const [k, rs] of Object.entries(m)) console.log(`  ${key}=${k}: 到達夜 ${(rs.reduce((a, b) => a + b.wave, 0) / rs.length).toFixed(1)}  クリア ${rs.filter(r => r.wave >= 10 && r.hp > 0).length}/${rs.length}  平均得点 ${Math.round(rs.reduce((a, b) => a + b.score, 0) / rs.length)}`);
  };
  console.log('--- 逃げる子ごと'); by('char');
  console.log('--- 罠の組み合わせごと'); by('loadout');
  console.log('pageerror:', errors.length ? errors.slice(0, 3) : 'なし');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });

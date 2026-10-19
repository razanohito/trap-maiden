// 夜明けをまたいだ罠の保持と、通常枠・フェイズ枠の回帰テスト。
// python -m http.server 8766 --bind 127.0.0.1
// node tools/sim/test_trap_slots.js
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.route('**/*.html', async route => {
      const response = await route.fetch();
      const body = (await response.text()).replace(
        "if (location.hostname === '127.0.0.1') window.__wanakan",
        "window.__slots = { openShop, advancePhase }; if (location.hostname === '127.0.0.1') window.__wanakan"
      );
      await route.fulfill({ response, body });
    });
    await page.goto(process.env.GAME_URL || 'http://127.0.0.1:8766/src/game.html');
    const results = await page.evaluate(() => {
      const { api } = window.__wanakan;
      const { openShop, advancePhase } = window.__slots;
      const check = (ok, message) => { if (!ok) throw new Error(message); };
      const results = [];
      for (const night of [3, 6]) {
        api.startRun('lily', ['bear', 'rock', 'spring', 'fire']);
        api.setPaused(true);
        api.startWave(night);
        const G = window.__wanakan.G;
        const cells = [];
        for (let y = 0; y < 10; y++) for (let x = 0; x < 15; x++) {
          if (api.canPlace(x, y)) cells.push([x, y]);
        }
        const key = i => cells[i].join(',');
        const place = (i, type = 'bear') => {
          G.time++;
          G.mana = api.stat.maxMana();
          api.placeTrap(...cells[i], type);
        };
        for (let i = 0; i < 5; i++) place(i);
        const original = [...G.traps.values()];
        advancePhase();
        check(G.traps.size === 5 && api.stat.limit() === 5, 'phase 1 must retain traps');
        advancePhase();
        check(original.every(t => G.traps.get(t.x + ',' + t.y) === t), 'phase 2 removed a trap');
        place(5);
        advancePhase();
        check(G.traps.size === 6 && api.stat.limit() === 7, 'phase 3 must retain traps');
        place(6);
        // 通常枠を2個撤去すると、追加枠の罠も基本上限内で翌夜に残る。
        place(0); place(1);
        const retained = [...G.traps.entries()];
        G.soul = 1000;
        openShop();
        check(G.traps.size === 5, 'traps within the base limit disappeared at dawn');
        check([...G.traps.values()].every(t => t.cd === 0), 'retained cooldowns must reset');
        // 実際のショップボタンで通常枠を1個増やす。
        G.soul = 1000;
        document.getElementById('up-limit').click();
        check(G.up.limit === 1 && api.stat.limit() === 6, 'slot upgrade did not apply');
        api.startWave(night + 1);
        place(0);
        check(G.traps.size === 6 && !G.traps.get(key(0)).bonus, 'new permanent slot was treated as temporary');
        advancePhase(); advancePhase();
        place(1);
        check(G.traps.size === 7, 'phase slot must be usable');
        // 別種への置き換えでも枠と印は引き継ぐ。
        place(1, 'rock');
        check(G.traps.size === 7, 'replacement must retain its slot');
        place(7);
        check(!G.traps.has(key(7)), 'placement exceeded the phase limit');
        openShop();
        check(retained.every(([k, t]) => G.traps.get(k) === t), 'a previously retained trap disappeared instead');
        check(G.traps.size === 6 && !G.traps.has(key(1)), 'dawn must remove the new temporary trap');
        check([...G.traps.values()].every(t => !t.bonus), 'retained traps must become permanent');
        check(G.traps.has(key(0)), 'upgraded permanent slot disappeared');
        // フェイズ3の追加2枠も夜明けに戻る。
        api.startWave(night + 2);
        advancePhase(); advancePhase(); advancePhase();
        place(1); place(7);
        check(G.traps.size === 8, 'both temporary slots must be usable');
        openShop();
        check(G.traps.size === 6 && !G.traps.has(key(1)) && !G.traps.has(key(7)), 'dawn must remove only the two temporary traps');
        if (night === 3) {
          api.startWave(6);
          check(G.traps.size === 0 && G.up.limit === 1, 'room change must clear traps and retain upgrades');
        }
        results.push(`night ${night} -> ${night + 1}: OK`);
      }
      return results;
    });
    assert.deepEqual(errors, [], 'browser runtime errors');
    console.log(results.join('\n'));
    console.log('phase limits, dawn retention, shop upgrades, replacement, room change: OK');
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exitCode = 1; });

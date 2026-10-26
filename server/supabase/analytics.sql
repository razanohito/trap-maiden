-- Trap of Lily: queries for balancing. Run them in Supabase > SQL Editor (they read every row, so only you can run them).

-- How often each trap is brought along, and how often it fires per run
select t.trap,
       count(*)                                         as runs_with_trap,
       round(100.0 * count(*) / (select count(*) from scores where not hidden), 1) as pick_rate_pct,
       round(avg(coalesce((s.fired ->> t.trap)::int, 0)), 1) as avg_fires_per_run
from scores s cross join lateral unnest(s.loadout) as t(trap)
where not s.hidden
group by t.trap order by runs_with_trap desc;

-- Scores and combos by girl (lily, mina, noel, cecil)
select girl, count(*) as runs, round(avg(score)) as avg_score, max(score) as best_score,
       round(avg(combo), 1) as avg_combo, max(combo) as best_combo
from scores where not hidden group by girl order by avg_score desc;

-- Most common 4-trap loadouts and how well they do
select array_to_string(array(select unnest(loadout) order by 1), ' + ') as loadout,
       count(*) as runs, round(avg(score)) as avg_score, round(avg(combo), 1) as avg_combo
from scores where not hidden group by 1 order by runs desc limit 20;

-- Daily submissions and players, by platform
select date_trunc('day', created_at)::date as day, platform, count(*) as runs, count(distinct player) as players
from scores group by 1, 2 order by 1 desc, 2;

-- Suspicious scores to review (set hidden = true in the Table Editor to remove one)
select id, created_at, name, score, combo, duration, platform from scores
where not hidden and (score > 200000 or combo > 300) order by score desc limit 50;

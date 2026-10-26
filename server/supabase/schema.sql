-- Trap of Lily: score ranking for 無限の夜 (Endless Night)
-- Paste this whole file into Supabase > SQL Editor > New query, then press Run.
-- Running it again is safe (it only creates what is missing and replaces the functions).

-- 1) Scores table. The game inserts one row per submission.
create table if not exists public.scores (
  id         bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  player     uuid not null,                       -- random per-device id (not linked to a person)
  name       text not null check (char_length(btrim(name)) between 1 and 12),
  score      integer not null check (score between 0 and 10000000),
  combo      integer not null check (combo between 0 and 5000),
  girl       text not null check (girl in ('lily', 'mina', 'noel', 'cecil')),
  loadout    text[] not null default '{}' check (coalesce(array_length(loadout, 1), 0) <= 4),
  fired      jsonb not null default '{}' check (jsonb_typeof(fired) = 'object' and pg_column_size(fired) < 2000),
  kills      integer not null default 0 check (kills between 0 and 100000),
  pits       integer not null default 0 check (pits between 0 and 100000),
  crashes    integer not null default 0 check (crashes between 0 and 100000),
  chains     integer not null default 0 check (chains between 0 and 100000),
  multi      integer not null default 0 check (multi between 0 and 100000),
  duration   real not null check (duration between 110 and 900),  -- seconds; a run is 120s of night plus setup
  version    text not null default '' check (char_length(version) <= 20),
  platform   text not null default '' check (char_length(platform) <= 20),
  lang       text not null default '' check (char_length(lang) <= 8),
  hidden     boolean not null default false        -- set to true in the Table Editor to remove a cheat or a bad name
);
create index if not exists scores_rank_idx on public.scores (score desc, created_at) where not hidden;
create index if not exists scores_player_idx on public.scores (player, created_at desc);

-- 2) Security: the public key may only INSERT. Nobody can read the raw rows with it
--    (the ranking is read through top_scores below, which shows only name/score/combo/girl).
alter table public.scores enable row level security;
drop policy if exists "game can insert" on public.scores;
create policy "game can insert" on public.scores for insert to anon, authenticated with check (not hidden);
revoke all on public.scores from anon, authenticated;
grant insert (player, name, score, combo, girl, loadout, fired, kills, pits, crashes, chains, multi, duration, version, platform, lang)
  on public.scores to anon, authenticated;

-- 3) Guard: one submission per device per 30 seconds, server sets the time.
create or replace function public.scores_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if exists (select 1 from public.scores where player = new.player and created_at > now() - interval '30 seconds') then
    raise exception 'too many submissions' using errcode = 'P0001';
  end if;
  new.created_at := now();
  new.hidden := false;
  new.name := btrim(new.name);
  return new;
end $$;
drop trigger if exists scores_guard on public.scores;
create trigger scores_guard before insert on public.scores for each row execute function public.scores_guard();

-- 4) Ranking: each device's best score, top 100 at most.
create or replace function public.top_scores(lim integer default 50)
returns table (rank bigint, name text, score integer, combo integer, girl text, player_tag text, created_at timestamptz)
language sql stable security definer set search_path = public as $$
  select row_number() over (order by b.score desc, b.created_at), b.name, b.score, b.combo, b.girl, left(b.player::text, 8), b.created_at
  from (select distinct on (player) * from public.scores where not hidden order by player, score desc, created_at) b
  order by b.score desc, b.created_at
  limit least(greatest(coalesce(lim, 50), 1), 100);
$$;
revoke all on function public.top_scores(integer) from public;
grant execute on function public.top_scores(integer) to anon, authenticated;

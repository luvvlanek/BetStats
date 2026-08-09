-- BetStats 3.0 prediction history (optional cloud sync)
-- Run this in Supabase SQL Editor.
create table if not exists public.prediction_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  prediction_key text not null,
  model_version text not null,
  match_id text,
  home text,
  away text,
  league text,
  league_id text,
  match_datetime text,
  market text not null,
  market_name text,
  probability numeric not null,
  odds numeric,
  fair_odds numeric,
  edge_pct numeric,
  ev_pct numeric,
  confidence integer,
  data_quality integer,
  agreement integer,
  score integer,
  status text,
  result smallint,
  result_source text,
  final_score text,
  created_at timestamptz not null default now(),
  settled_at timestamptz,
  unique(user_id, prediction_key)
);

alter table public.prediction_logs enable row level security;

drop policy if exists "prediction_logs_select_own" on public.prediction_logs;
create policy "prediction_logs_select_own"
on public.prediction_logs for select
using (auth.uid() = user_id);

drop policy if exists "prediction_logs_insert_own" on public.prediction_logs;
create policy "prediction_logs_insert_own"
on public.prediction_logs for insert
with check (auth.uid() = user_id);

drop policy if exists "prediction_logs_update_own" on public.prediction_logs;
create policy "prediction_logs_update_own"
on public.prediction_logs for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create index if not exists prediction_logs_user_created_idx
on public.prediction_logs(user_id, created_at desc);

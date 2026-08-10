-- BetStats BETA — PRYWATNOŚĆ KUPONÓW
-- Uruchom w Supabase SQL Editor.
-- Ten skrypt usuwa WSZYSTKIE istniejące polityki RLS tabeli bets, aby stara polityka
-- nie pozwalała przypadkiem na publiczny odczyt. Następnie tworzy wyłącznie polityki właściciela.

alter table if exists public.bets enable row level security;
alter table if exists public.bets force row level security;

do $$
declare
  p record;
begin
  for p in
    select policyname
    from pg_policies
    where schemaname = 'public' and tablename = 'bets'
  loop
    execute format('drop policy if exists %I on public.bets', p.policyname);
  end loop;
end $$;

create policy "bets_select_own"
on public.bets for select
to authenticated
using (auth.uid() = user_id);

create policy "bets_insert_own"
on public.bets for insert
to authenticated
with check (auth.uid() = user_id);

create policy "bets_update_own"
on public.bets for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "bets_delete_own"
on public.bets for delete
to authenticated
using (auth.uid() = user_id);

-- Weryfikacja: po wykonaniu powinny istnieć dokładnie 4 polityki bets_*_own.

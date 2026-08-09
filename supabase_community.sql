-- BetStats Polska: fundament bezpiecznej społeczności.
-- Uruchom w Supabase SQL Editor po sprawdzeniu, że tabela public.profiles używa id zgodnego z auth.users.id.

create table if not exists public.community_posts (
  id uuid primary key default gen_random_uuid(),
  author_id uuid not null references auth.users(id) on delete cascade,
  category text not null check (category in ('Analiza', 'Typ społeczności', 'Dyskusja')),
  title text not null check (char_length(title) between 4 and 90),
  body text not null check (char_length(body) between 20 and 700),
  moderation_status text not null default 'pending' check (moderation_status in ('pending', 'approved', 'rejected')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists community_posts_public_feed_idx
  on public.community_posts (moderation_status, created_at desc);

alter table public.community_posts enable row level security;

create policy "Publiczne wpisy są widoczne"
  on public.community_posts for select
  using (moderation_status = 'approved' or auth.uid() = author_id);

create policy "Zalogowany użytkownik dodaje własny wpis"
  on public.community_posts for insert to authenticated
  with check (auth.uid() = author_id and moderation_status = 'pending');

create policy "Autor może edytować oczekujący wpis"
  on public.community_posts for update to authenticated
  using (auth.uid() = author_id and moderation_status = 'pending')
  with check (auth.uid() = author_id and moderation_status = 'pending');

create policy "Autor może usunąć własny oczekujący wpis"
  on public.community_posts for delete to authenticated
  using (auth.uid() = author_id and moderation_status = 'pending');

-- Moderacja powinna odbywać się wyłącznie z zaufanego panelu backendowego
-- z użyciem klucza service_role, nigdy bezpośrednio w przeglądarce.

-- BetStats Polska: fundament bezpiecznej społeczności.
-- Uruchom w Supabase SQL Editor po sprawdzeniu, że tabela public.profiles używa id zgodnego z auth.users.id.

create table if not exists public.community_posts (
  id uuid primary key default gen_random_uuid(),
  author_id uuid not null references auth.users(id) on delete cascade,
  category text not null check (category in ('Analiza', 'Typ społeczności', 'Dyskusja')),
  title text not null check (char_length(title) between 4 and 90),
  body text not null check (char_length(body) between 20 and 700),
  moderation_status text not null default 'approved' check (moderation_status in ('pending', 'approved', 'rejected')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists community_posts_public_feed_idx
  on public.community_posts (moderation_status, created_at desc);

alter table public.community_posts enable row level security;

drop policy if exists "Publiczne wpisy są widoczne" on public.community_posts;
create policy "Publiczne wpisy są widoczne"
  on public.community_posts for select
  using (moderation_status = 'approved' or auth.uid() = author_id);

drop policy if exists "Zalogowany użytkownik dodaje własny wpis" on public.community_posts;
create policy "Zalogowany użytkownik dodaje własny wpis"
  on public.community_posts for insert to authenticated
  with check (auth.uid() = author_id and moderation_status = 'approved');

drop policy if exists "Autor może edytować oczekujący wpis" on public.community_posts;
create policy "Autor może edytować własny wpis"
  on public.community_posts for update to authenticated
  using (auth.uid() = author_id)
  with check (auth.uid() = author_id);

drop policy if exists "Autor może usunąć własny oczekujący wpis" on public.community_posts;
create policy "Autor może usunąć własny wpis"
  on public.community_posts for delete to authenticated
  using (auth.uid() = author_id and moderation_status = 'approved');

-- Moderacja powinna odbywać się wyłącznie z zaufanego panelu backendowego
-- z użyciem klucza service_role, nigdy bezpośrednio w przeglądarce.


-- BetStats 1.0 Beta: reakcje i komentarze społeczności.
create table if not exists public.community_reactions (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references public.community_posts(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  value smallint not null check (value in (-1, 1)),
  created_at timestamptz not null default now(),
  unique(post_id, user_id)
);

create index if not exists community_reactions_post_idx
  on public.community_reactions(post_id);

alter table public.community_reactions enable row level security;

drop policy if exists "Reakcje są widoczne" on public.community_reactions;
create policy "Reakcje są widoczne"
  on public.community_reactions for select
  using (true);

drop policy if exists "Zalogowany zmienia własną reakcję" on public.community_reactions;
create policy "Zalogowany zmienia własną reakcję"
  on public.community_reactions for insert to authenticated
  with check (auth.uid() = user_id);

drop policy if exists "Zalogowany usuwa własną reakcję" on public.community_reactions;
create policy "Zalogowany usuwa własną reakcję"
  on public.community_reactions for delete to authenticated
  using (auth.uid() = user_id);

drop policy if exists "Zalogowany aktualizuje własną reakcję" on public.community_reactions;
create policy "Zalogowany aktualizuje własną reakcję"
  on public.community_reactions for update to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create table if not exists public.community_comments (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references public.community_posts(id) on delete cascade,
  author_id uuid not null references auth.users(id) on delete cascade,
  body text not null check (char_length(body) between 1 and 500),
  created_at timestamptz not null default now()
);

create index if not exists community_comments_post_idx
  on public.community_comments(post_id, created_at asc);

alter table public.community_comments enable row level security;

drop policy if exists "Komentarze są widoczne" on public.community_comments;
create policy "Komentarze są widoczne"
  on public.community_comments for select
  using (true);

drop policy if exists "Zalogowany dodaje własny komentarz" on public.community_comments;
create policy "Zalogowany dodaje własny komentarz"
  on public.community_comments for insert to authenticated
  with check (auth.uid() = author_id);

drop policy if exists "Autor usuwa własny komentarz" on public.community_comments;
create policy "Autor usuwa własny komentarz"
  on public.community_comments for delete to authenticated
  using (auth.uid() = author_id);

-- Beta: nowy feed jest publikowany od razu po zapisie.
alter table public.community_posts alter column moderation_status set default 'approved';

-- Bets must remain private to their owner.
alter table if exists public.bets enable row level security;
drop policy if exists "Users can read own bets" on public.bets;
create policy "Users can read own bets" on public.bets for select to authenticated using (auth.uid() = user_id);
drop policy if exists "Users can insert own bets" on public.bets;
create policy "Users can insert own bets" on public.bets for insert to authenticated with check (auth.uid() = user_id);
drop policy if exists "Users can update own bets" on public.bets;
create policy "Users can update own bets" on public.bets for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "Users can delete own bets" on public.bets;
create policy "Users can delete own bets" on public.bets for delete to authenticated using (auth.uid() = user_id);

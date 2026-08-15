-- BetStats BETA — subskrypcje + Stripe + program partnerski
-- Uruchom CAŁY plik w Supabase SQL Editor.
-- Potem ustaw profiles.is_admin = true dla swojego konta.

alter table if exists public.profiles
  add column if not exists is_admin boolean not null default false;

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users(id) on delete cascade,
  stripe_customer_id text,
  stripe_subscription_id text unique,
  status text not null default 'inactive',
  plan_name text not null default 'BetStats Weekly',
  amount_pln numeric(10,2) not null default 29.99,
  current_period_end timestamptz,
  cancel_at_period_end boolean not null default false,
  partner_code text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists subscriptions_user_idx on public.subscriptions(user_id);
create index if not exists subscriptions_stripe_idx on public.subscriptions(stripe_subscription_id);

alter table public.subscriptions enable row level security;
alter table public.subscriptions force row level security;

drop policy if exists "subscriptions_select_own" on public.subscriptions;
create policy "subscriptions_select_own"
on public.subscriptions for select to authenticated
using (auth.uid() = user_id);

drop policy if exists "subscriptions_admin_select" on public.subscriptions;
create policy "subscriptions_admin_select"
on public.subscriptions for select to authenticated
using (exists (select 1 from public.profiles p where p.id = auth.uid() and p.is_admin = true));

create table if not exists public.partner_codes (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  partner_name text not null,
  commission_percent numeric(5,2) not null default 20 check (commission_percent >= 0 and commission_percent <= 100),
  active boolean not null default true,
  max_uses integer,
  uses_count integer not null default 0,
  created_at timestamptz not null default now()
);

create index if not exists partner_codes_code_idx on public.partner_codes(code);
alter table public.partner_codes enable row level security;
alter table public.partner_codes force row level security;

drop policy if exists "partner_codes_admin_select" on public.partner_codes;
create policy "partner_codes_admin_select"
on public.partner_codes for select to authenticated
using (exists (select 1 from public.profiles p where p.id = auth.uid() and p.is_admin = true));

drop policy if exists "partner_codes_admin_insert" on public.partner_codes;
create policy "partner_codes_admin_insert"
on public.partner_codes for insert to authenticated
with check (exists (select 1 from public.profiles p where p.id = auth.uid() and p.is_admin = true));

drop policy if exists "partner_codes_admin_update" on public.partner_codes;
create policy "partner_codes_admin_update"
on public.partner_codes for update to authenticated
using (exists (select 1 from public.profiles p where p.id = auth.uid() and p.is_admin = true))
with check (exists (select 1 from public.profiles p where p.id = auth.uid() and p.is_admin = true));

create table if not exists public.partner_referrals (
  id uuid primary key default gen_random_uuid(),
  partner_code_id uuid references public.partner_codes(id) on delete set null,
  partner_code text,
  partner_name text,
  user_id uuid not null references auth.users(id) on delete cascade,
  subscription_id uuid references public.subscriptions(id) on delete set null,
  stripe_checkout_session_id text unique,
  stripe_subscription_id text,
  stripe_invoice_id text unique,
  gross_amount_pln numeric(10,2) not null default 29.99,
  commission_percent numeric(5,2) not null default 0,
  commission_amount_pln numeric(10,2) not null default 0,
  status text not null default 'pending',
  created_at timestamptz not null default now()
);

create index if not exists partner_referrals_partner_idx on public.partner_referrals(partner_code_id, created_at desc);
create index if not exists partner_referrals_user_idx on public.partner_referrals(user_id, created_at desc);

alter table public.partner_referrals enable row level security;
alter table public.partner_referrals force row level security;

drop policy if exists "partner_referrals_admin_select" on public.partner_referrals;
create policy "partner_referrals_admin_select"
on public.partner_referrals for select to authenticated
using (exists (select 1 from public.profiles p where p.id = auth.uid() and p.is_admin = true));

-- RPC used by the Edge Function to validate a partner code without exposing all codes.
create or replace function public.get_partner_code(p_code text)
returns table (
  id uuid,
  code text,
  partner_name text,
  commission_percent numeric,
  active boolean,
  max_uses integer,
  uses_count integer
)
language sql
security definer
set search_path = public
as $$
  select id, code, partner_name, commission_percent, active, max_uses, uses_count
  from public.partner_codes
  where code = upper(trim(p_code))
  limit 1;
$$;

revoke all on function public.get_partner_code(text) from public;
grant execute on function public.get_partner_code(text) to service_role;

-- Admin helper: mark a user as admin.
-- Replace EMAIL with your own email and run manually once.
-- update public.profiles set is_admin = true where email = 'EMAIL';

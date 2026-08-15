-- BetStats BETA — profil użytkownika
-- Naprawia 406 na GET /profiles/... gdy konto nie ma jeszcze rekordu.
-- Uruchom raz w Supabase SQL Editor.
--
-- Zakładamy, że public.profiles.id = auth.users.id.
-- Trigger tworzy profil po rejestracji. Jeśli masz już własny trigger,
-- usuń tylko duplikujący trigger lub zachowaj ten, jeśli nazwa jest wolna.

create or replace function public.handle_new_user_profile()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if to_regclass('public.profiles') is not null then
    begin
      execute 'insert into public.profiles (id, nickname) values ($1, $2) on conflict (id) do nothing'
        using new.id, left(coalesce(split_part(new.email, '@', 1), 'user'), 30);
    exception when undefined_column then
      execute 'insert into public.profiles (id) values ($1) on conflict (id) do nothing'
        using new.id;
    end;
  end if;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created_profile on auth.users;

create trigger on_auth_user_created_profile
after insert on auth.users
for each row execute function public.handle_new_user_profile();

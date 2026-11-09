-- 002: profiles + trigger จาก auth.users (CONFIG ข้อ 2)

create table profiles (
  user_id uuid primary key references auth.users (id) on delete cascade,
  username citext unique not null,
  created_at timestamptz not null default now()
);

-- สร้าง profile อัตโนมัติตอนสมัคร (username จาก metadata, citext กันซ้ำไม่สนตัวพิมพ์)
create or replace function public.handle_new_user()
returns trigger
language plpgsql security definer
set search_path = public
as $$
begin
  insert into public.profiles (user_id, username)
  values (new.id, coalesce(nullif(new.raw_user_meta_data->>'username', ''), split_part(new.email, '@', 1)))
  on conflict (user_id) do nothing;
  return new;
exception
  when unique_violation then
    -- username ซ้ำ: ไม่บล็อก signup, ให้ user มาตั้งทีหลัง
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

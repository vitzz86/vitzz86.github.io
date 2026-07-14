-- Vito's Dream Board: public posts with anonymous Supabase Auth sessions.
-- Run this file once in the Supabase SQL Editor.

create extension if not exists pgcrypto;

create table if not exists public.dream_board_posts (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references auth.users(id) on delete set null,
  message text not null check (char_length(btrim(message)) between 3 and 500),
  type text not null check (type in ('hope', 'dream', 'motivation', 'gratitude', 'feedback', 'advice', 'general')),
  display_name text check (display_name is null or char_length(btrim(display_name)) between 2 and 40),
  is_anonymous boolean not null default true,
  spotify_playlist_id text check (spotify_playlist_id is null or spotify_playlist_id ~ '^[A-Za-z0-9]{10,30}$'),
  spotify_canonical_url text,
  spotify_embed_url text,
  spotify_title text,
  spotify_creator_name text,
  spotify_thumbnail_url text,
  spotify_validation_status text not null default 'empty' check (spotify_validation_status in ('empty', 'valid', 'invalid', 'unavailable')),
  moderation_status text not null default 'published' check (moderation_status in ('pending', 'published', 'flagged', 'hidden', 'deleted')),
  reaction_count integer not null default 0 check (reaction_count >= 0),
  report_count integer not null default 0 check (report_count >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  published_at timestamptz
);

create table if not exists public.dream_board_reactions (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references public.dream_board_posts(id) on delete cascade,
  owner_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (post_id, owner_id)
);

create table if not exists public.dream_board_reports (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references public.dream_board_posts(id) on delete cascade,
  owner_id uuid not null references auth.users(id) on delete cascade,
  reason text not null,
  status text not null default 'pending' check (status in ('pending', 'resolved', 'dismissed')),
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  unique (post_id, owner_id)
);

create table if not exists public.dream_board_moderation_logs (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references public.dream_board_posts(id) on delete cascade,
  action text not null,
  previous_status text,
  new_status text,
  administrator_id uuid references auth.users(id) on delete set null,
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists dream_board_posts_published_idx
  on public.dream_board_posts (moderation_status, created_at desc);
create index if not exists dream_board_posts_owner_created_idx
  on public.dream_board_posts (owner_id, created_at desc);
create index if not exists dream_board_reactions_post_idx
  on public.dream_board_reactions (post_id);
create index if not exists dream_board_reports_status_idx
  on public.dream_board_reports (status, created_at desc);

alter table public.dream_board_posts enable row level security;
alter table public.dream_board_reactions enable row level security;
alter table public.dream_board_reports enable row level security;
alter table public.dream_board_moderation_logs enable row level security;

-- Visitors never access tables directly. Carefully scoped functions below are the API.
revoke all on table public.dream_board_posts from anon, authenticated;
revoke all on table public.dream_board_reactions from anon, authenticated;
revoke all on table public.dream_board_reports from anon, authenticated;
revoke all on table public.dream_board_moderation_logs from anon, authenticated;

create or replace function public.get_dream_board_posts(p_limit integer default 100)
returns table (
  id uuid,
  message text,
  type text,
  display_name text,
  is_anonymous boolean,
  spotify_playlist_id text,
  spotify_canonical_url text,
  spotify_embed_url text,
  spotify_title text,
  spotify_creator_name text,
  spotify_thumbnail_url text,
  reaction_count integer,
  created_at timestamptz,
  loved_by_me boolean
)
language sql
stable
security definer
set search_path = ''
as $$
  select
    p.id,
    p.message,
    p.type,
    p.display_name,
    p.is_anonymous,
    p.spotify_playlist_id,
    p.spotify_canonical_url,
    p.spotify_embed_url,
    p.spotify_title,
    p.spotify_creator_name,
    p.spotify_thumbnail_url,
    p.reaction_count,
    p.created_at,
    case
      when auth.uid() is null then false
      else exists (
        select 1
        from public.dream_board_reactions r
        where r.post_id = p.id and r.owner_id = auth.uid()
      )
    end as loved_by_me
  from public.dream_board_posts p
  where p.moderation_status = 'published'
  order by p.created_at desc
  limit least(greatest(coalesce(p_limit, 100), 1), 100);
$$;

create or replace function public.create_dream_board_post(
  p_message text,
  p_type text,
  p_is_anonymous boolean default true,
  p_display_name text default null,
  p_spotify_playlist_id text default null,
  p_spotify_title text default null,
  p_spotify_creator_name text default null,
  p_spotify_thumbnail_url text default null
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_owner uuid := auth.uid();
  v_message text := btrim(coalesce(p_message, ''));
  v_name text;
  v_id uuid;
begin
  if v_owner is null then
    raise exception 'A visitor session is required.';
  end if;

  if char_length(v_message) < 3 or char_length(v_message) > 500 then
    raise exception 'Message must contain between 3 and 500 characters.';
  end if;

  if p_type is null or p_type not in ('hope', 'dream', 'motivation', 'gratitude', 'feedback', 'advice', 'general') then
    raise exception 'Invalid message type.';
  end if;

  if v_message ~ '<[^>]+>' then
    raise exception 'HTML is not allowed in messages.';
  end if;

  if v_message ~ '(.)\1{19,}' then
    raise exception 'Please remove excessive repeated characters.';
  end if;

  if p_is_anonymous then
    v_name := null;
  else
    v_name := btrim(coalesce(p_display_name, ''));
    if char_length(v_name) < 2 or char_length(v_name) > 40 then
      raise exception 'Display name must contain between 2 and 40 characters.';
    end if;
  end if;

  if p_spotify_playlist_id is not null and p_spotify_playlist_id !~ '^[A-Za-z0-9]{10,30}$' then
    raise exception 'Invalid Spotify playlist identifier.';
  end if;

  if p_spotify_thumbnail_url is not null and p_spotify_thumbnail_url !~ '^https://' then
    raise exception 'Invalid Spotify thumbnail URL.';
  end if;

  if (
    select count(*)
    from public.dream_board_posts
    where owner_id = v_owner and created_at > now() - interval '10 minutes'
  ) >= 3 then
    raise exception 'Please wait before posting again.';
  end if;

  if (
    select count(*)
    from public.dream_board_posts
    where owner_id = v_owner and created_at > now() - interval '24 hours'
  ) >= 10 then
    raise exception 'Daily posting limit reached.';
  end if;

  if exists (
    select 1
    from public.dream_board_posts
    where owner_id = v_owner
      and lower(message) = lower(v_message)
      and created_at > now() - interval '24 hours'
  ) then
    raise exception 'This message was already submitted.';
  end if;

  insert into public.dream_board_posts (
    owner_id,
    message,
    type,
    display_name,
    is_anonymous,
    spotify_playlist_id,
    spotify_canonical_url,
    spotify_embed_url,
    spotify_title,
    spotify_creator_name,
    spotify_thumbnail_url,
    spotify_validation_status,
    moderation_status,
    published_at
  ) values (
    v_owner,
    v_message,
    p_type,
    v_name,
    p_is_anonymous,
    p_spotify_playlist_id,
    case when p_spotify_playlist_id is null then null else 'https://open.spotify.com/playlist/' || p_spotify_playlist_id end,
    case when p_spotify_playlist_id is null then null else 'https://open.spotify.com/embed/playlist/' || p_spotify_playlist_id end,
    left(nullif(btrim(p_spotify_title), ''), 120),
    left(nullif(btrim(p_spotify_creator_name), ''), 80),
    p_spotify_thumbnail_url,
    case when p_spotify_playlist_id is null then 'empty' else 'valid' end,
    'published',
    now()
  )
  returning id into v_id;

  return v_id;
end;
$$;

create or replace function public.toggle_dream_board_reaction(p_post_id uuid)
returns table (reaction_count integer, loved boolean)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_owner uuid := auth.uid();
  v_loved boolean;
begin
  if v_owner is null then
    raise exception 'A visitor session is required.';
  end if;

  if not exists (
    select 1 from public.dream_board_posts
    where id = p_post_id and moderation_status = 'published'
  ) then
    raise exception 'Post not found.';
  end if;

  if exists (
    select 1 from public.dream_board_reactions
    where post_id = p_post_id and owner_id = v_owner
  ) then
    delete from public.dream_board_reactions
    where post_id = p_post_id and owner_id = v_owner;
    update public.dream_board_posts as p
    set reaction_count = greatest(p.reaction_count - 1, 0), updated_at = now()
    where p.id = p_post_id;
    v_loved := false;
  else
    insert into public.dream_board_reactions (post_id, owner_id)
    values (p_post_id, v_owner);
    update public.dream_board_posts as p
    set reaction_count = p.reaction_count + 1, updated_at = now()
    where p.id = p_post_id;
    v_loved := true;
  end if;

  return query
  select p.reaction_count, v_loved
  from public.dream_board_posts p
  where p.id = p_post_id;
end;
$$;

create or replace function public.report_dream_board_post(p_post_id uuid, p_reason text)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_owner uuid := auth.uid();
  v_inserted integer := 0;
begin
  if v_owner is null then
    raise exception 'A visitor session is required.';
  end if;

  if p_reason is null or p_reason not in (
    'Spam',
    'Harassment or abusive content',
    'Hate speech',
    'Sexual or explicit content',
    'Personal information',
    'Dangerous content',
    'Other'
  ) then
    raise exception 'Invalid report reason.';
  end if;

  if (
    select count(*) from public.dream_board_reports
    where owner_id = v_owner and created_at > now() - interval '10 minutes'
  ) >= 5 then
    raise exception 'Please wait before submitting another report.';
  end if;

  insert into public.dream_board_reports (post_id, owner_id, reason)
  select p_post_id, v_owner, p_reason
  where exists (
    select 1 from public.dream_board_posts
    where id = p_post_id and moderation_status = 'published'
  )
  on conflict (post_id, owner_id) do nothing;

  get diagnostics v_inserted = row_count;

  if v_inserted = 1 then
    update public.dream_board_posts
    set
      report_count = report_count + 1,
      moderation_status = case when report_count + 1 >= 3 then 'flagged' else moderation_status end,
      updated_at = now()
    where id = p_post_id;
  end if;

  return v_inserted = 1;
end;
$$;

revoke execute on function public.get_dream_board_posts(integer) from public;
revoke execute on function public.create_dream_board_post(text, text, boolean, text, text, text, text, text) from public;
revoke execute on function public.toggle_dream_board_reaction(uuid) from public;
revoke execute on function public.report_dream_board_post(uuid, text) from public;

grant execute on function public.get_dream_board_posts(integer) to anon, authenticated;
grant execute on function public.create_dream_board_post(text, text, boolean, text, text, text, text, text) to authenticated;
grant execute on function public.toggle_dream_board_reaction(uuid) to authenticated;
grant execute on function public.report_dream_board_post(uuid, text) to authenticated;

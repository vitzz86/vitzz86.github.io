-- Dream Board comments upgrade.
-- Safe to run after schema.sql and youtube_upgrade.sql.

begin;

alter table public.dream_board_posts
  add column if not exists comment_count integer not null default 0
  check (comment_count >= 0);

create table if not exists public.dream_board_comments (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references public.dream_board_posts(id) on delete cascade,
  owner_id uuid references auth.users(id) on delete set null,
  message text not null check (char_length(btrim(message)) between 1 and 280),
  display_name text check (display_name is null or char_length(btrim(display_name)) between 2 and 40),
  is_anonymous boolean not null default true,
  moderation_status text not null default 'published'
    check (moderation_status in ('published', 'flagged', 'hidden', 'deleted')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists dream_board_comments_post_created_idx
  on public.dream_board_comments (post_id, moderation_status, created_at);
create index if not exists dream_board_comments_owner_created_idx
  on public.dream_board_comments (owner_id, created_at desc);

update public.dream_board_posts p
set comment_count = (
  select count(*)::integer
  from public.dream_board_comments c
  where c.post_id = p.id and c.moderation_status = 'published'
);

alter table public.dream_board_comments enable row level security;
revoke all on table public.dream_board_comments from anon, authenticated;

drop function if exists public.get_dream_board_posts(integer);

create function public.get_dream_board_posts(p_limit integer default 100)
returns table (
  id uuid,
  message text,
  type text,
  display_name text,
  is_anonymous boolean,
  spotify_item_id text,
  spotify_content_type text,
  spotify_canonical_url text,
  spotify_embed_url text,
  spotify_title text,
  spotify_creator_name text,
  spotify_thumbnail_url text,
  youtube_item_id text,
  youtube_content_type text,
  youtube_canonical_url text,
  youtube_embed_url text,
  youtube_title text,
  youtube_creator_name text,
  youtube_thumbnail_url text,
  reaction_count integer,
  comment_count integer,
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
    p.spotify_playlist_id as spotify_item_id,
    p.spotify_content_type,
    p.spotify_canonical_url,
    p.spotify_embed_url,
    p.spotify_title,
    p.spotify_creator_name,
    p.spotify_thumbnail_url,
    p.youtube_item_id,
    p.youtube_content_type,
    p.youtube_canonical_url,
    p.youtube_embed_url,
    p.youtube_title,
    p.youtube_creator_name,
    p.youtube_thumbnail_url,
    p.reaction_count,
    p.comment_count,
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

drop function if exists public.get_dream_board_comments(uuid, integer);

create function public.get_dream_board_comments(
  p_post_id uuid,
  p_limit integer default 50
)
returns table (
  id uuid,
  message text,
  display_name text,
  is_anonymous boolean,
  created_at timestamptz
)
language sql
stable
security definer
set search_path = ''
as $$
  select
    c.id,
    c.message,
    c.display_name,
    c.is_anonymous,
    c.created_at
  from public.dream_board_comments c
  where c.post_id = p_post_id
    and c.moderation_status = 'published'
    and exists (
      select 1
      from public.dream_board_posts p
      where p.id = p_post_id and p.moderation_status = 'published'
    )
  order by c.created_at asc
  limit least(greatest(coalesce(p_limit, 50), 1), 100);
$$;

drop function if exists public.create_dream_board_comment(uuid, text, boolean, text);

create function public.create_dream_board_comment(
  p_post_id uuid,
  p_message text,
  p_is_anonymous boolean default true,
  p_display_name text default null
)
returns table (comment_id uuid, comment_count integer)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_owner uuid := auth.uid();
  v_message text := btrim(coalesce(p_message, ''));
  v_name text;
  v_comment_id uuid;
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

  if char_length(v_message) < 1 or char_length(v_message) > 280 then
    raise exception 'Comment must contain between 1 and 280 characters.';
  end if;

  if v_message ~ '<[^>]+>' then
    raise exception 'HTML is not allowed in comments.';
  end if;

  if v_message ~ '(.)\1{19,}' then
    raise exception 'Please remove excessive repeated characters.';
  end if;

  if (select count(*) from regexp_matches(v_message, 'https?://', 'gi')) > 2 then
    raise exception 'Please limit your comment to two links.';
  end if;

  if coalesce(p_is_anonymous, true) then
    v_name := null;
  else
    v_name := btrim(coalesce(p_display_name, ''));
    if char_length(v_name) < 2 or char_length(v_name) > 40 then
      raise exception 'Display name must contain between 2 and 40 characters.';
    end if;
  end if;

  if (
    select count(*)
    from public.dream_board_comments
    where owner_id = v_owner and created_at > now() - interval '10 minutes'
  ) >= 8 then
    raise exception 'Please wait before commenting again.';
  end if;

  if (
    select count(*)
    from public.dream_board_comments
    where owner_id = v_owner and created_at > now() - interval '24 hours'
  ) >= 40 then
    raise exception 'Daily comment limit reached.';
  end if;

  if exists (
    select 1
    from public.dream_board_comments
    where owner_id = v_owner
      and post_id = p_post_id
      and lower(message) = lower(v_message)
      and created_at > now() - interval '24 hours'
  ) then
    raise exception 'You already added that comment.';
  end if;

  insert into public.dream_board_comments (
    post_id,
    owner_id,
    message,
    display_name,
    is_anonymous,
    moderation_status
  ) values (
    p_post_id,
    v_owner,
    v_message,
    v_name,
    coalesce(p_is_anonymous, true),
    'published'
  )
  returning id into v_comment_id;

  update public.dream_board_posts as p
  set comment_count = p.comment_count + 1, updated_at = now()
  where p.id = p_post_id;

  return query
  select v_comment_id, p.comment_count
  from public.dream_board_posts p
  where p.id = p_post_id;
end;
$$;

revoke execute on function public.get_dream_board_posts(integer) from public;
revoke execute on function public.get_dream_board_comments(uuid, integer) from public;
revoke execute on function public.create_dream_board_comment(uuid, text, boolean, text) from public;

grant execute on function public.get_dream_board_posts(integer) to anon, authenticated;
grant execute on function public.get_dream_board_comments(uuid, integer) to anon, authenticated;
grant execute on function public.create_dream_board_comment(uuid, text, boolean, text) to authenticated;

notify pgrst, 'reload schema';

commit;

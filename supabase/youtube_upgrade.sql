-- Dream Board YouTube media upgrade.
-- Safe to run on an existing installation after the original schema.

begin;

alter table public.dream_board_posts
  add column if not exists youtube_item_id text,
  add column if not exists youtube_content_type text,
  add column if not exists youtube_canonical_url text,
  add column if not exists youtube_embed_url text,
  add column if not exists youtube_title text,
  add column if not exists youtube_creator_name text,
  add column if not exists youtube_thumbnail_url text,
  add column if not exists youtube_validation_status text not null default 'empty';

alter table public.dream_board_posts
  drop constraint if exists dream_board_posts_youtube_item_id_check,
  drop constraint if exists dream_board_posts_youtube_content_type_check,
  drop constraint if exists dream_board_posts_youtube_validation_status_check,
  drop constraint if exists dream_board_posts_single_media_provider_check;

alter table public.dream_board_posts
  add constraint dream_board_posts_youtube_item_id_check
    check (youtube_item_id is null or youtube_item_id ~ '^[A-Za-z0-9_-]{10,80}$'),
  add constraint dream_board_posts_youtube_content_type_check
    check (youtube_content_type is null or youtube_content_type in ('video', 'playlist')),
  add constraint dream_board_posts_youtube_validation_status_check
    check (youtube_validation_status in ('empty', 'valid', 'invalid', 'unavailable')),
  add constraint dream_board_posts_single_media_provider_check
    check (not (spotify_playlist_id is not null and youtube_item_id is not null));

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

drop function if exists public.create_dream_board_post_v2(text, text, boolean, text, text, text, text, text, text, text);

create function public.create_dream_board_post_v2(
  p_message text,
  p_type text,
  p_is_anonymous boolean default true,
  p_display_name text default null,
  p_media_provider text default null,
  p_media_item_id text default null,
  p_media_content_type text default null,
  p_media_title text default null,
  p_media_creator_name text default null,
  p_media_thumbnail_url text default null
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

  if p_media_provider is null then
    if p_media_item_id is not null or p_media_content_type is not null then
      raise exception 'A media provider is required for attached media.';
    end if;
  elsif p_media_provider = 'spotify' then
    if p_media_item_id is null or p_media_item_id !~ '^[A-Za-z0-9]{10,30}$' then
      raise exception 'Invalid Spotify item identifier.';
    end if;
    if p_media_content_type is null or p_media_content_type not in ('playlist', 'album', 'track') then
      raise exception 'Spotify content must be a song, album, or playlist.';
    end if;
  elsif p_media_provider = 'youtube' then
    if p_media_content_type = 'video' and (p_media_item_id is null or p_media_item_id !~ '^[A-Za-z0-9_-]{11}$') then
      raise exception 'Invalid YouTube video identifier.';
    end if;
    if p_media_content_type = 'playlist' and (p_media_item_id is null or p_media_item_id !~ '^[A-Za-z0-9_-]{10,80}$') then
      raise exception 'Invalid YouTube playlist identifier.';
    end if;
    if p_media_content_type is null or p_media_content_type not in ('video', 'playlist') then
      raise exception 'YouTube content must be a video or playlist.';
    end if;
  else
    raise exception 'Unsupported media provider.';
  end if;

  if p_media_thumbnail_url is not null and p_media_thumbnail_url !~ '^https://' then
    raise exception 'Invalid media thumbnail URL.';
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
    spotify_content_type,
    spotify_canonical_url,
    spotify_embed_url,
    spotify_title,
    spotify_creator_name,
    spotify_thumbnail_url,
    spotify_validation_status,
    youtube_item_id,
    youtube_content_type,
    youtube_canonical_url,
    youtube_embed_url,
    youtube_title,
    youtube_creator_name,
    youtube_thumbnail_url,
    youtube_validation_status,
    moderation_status,
    published_at
  ) values (
    v_owner,
    v_message,
    p_type,
    v_name,
    p_is_anonymous,
    case when p_media_provider = 'spotify' then p_media_item_id end,
    case when p_media_provider = 'spotify' then p_media_content_type end,
    case when p_media_provider = 'spotify' then 'https://open.spotify.com/' || p_media_content_type || '/' || p_media_item_id end,
    case when p_media_provider = 'spotify' then 'https://open.spotify.com/embed/' || p_media_content_type || '/' || p_media_item_id end,
    case when p_media_provider = 'spotify' then left(nullif(btrim(p_media_title), ''), 120) end,
    case when p_media_provider = 'spotify' then left(nullif(btrim(p_media_creator_name), ''), 80) end,
    case when p_media_provider = 'spotify' then p_media_thumbnail_url end,
    case when p_media_provider = 'spotify' then 'valid' else 'empty' end,
    case when p_media_provider = 'youtube' then p_media_item_id end,
    case when p_media_provider = 'youtube' then p_media_content_type end,
    case
      when p_media_provider = 'youtube' and p_media_content_type = 'playlist' then 'https://www.youtube.com/playlist?list=' || p_media_item_id
      when p_media_provider = 'youtube' then 'https://www.youtube.com/watch?v=' || p_media_item_id
    end,
    case
      when p_media_provider = 'youtube' and p_media_content_type = 'playlist' then 'https://www.youtube.com/embed/videoseries?list=' || p_media_item_id
      when p_media_provider = 'youtube' then 'https://www.youtube.com/embed/' || p_media_item_id
    end,
    case when p_media_provider = 'youtube' then left(nullif(btrim(p_media_title), ''), 120) end,
    case when p_media_provider = 'youtube' then left(nullif(btrim(p_media_creator_name), ''), 80) end,
    case when p_media_provider = 'youtube' then p_media_thumbnail_url end,
    case when p_media_provider = 'youtube' then 'valid' else 'empty' end,
    'published',
    now()
  )
  returning id into v_id;

  return v_id;
end;
$$;

revoke execute on function public.get_dream_board_posts(integer) from public;
revoke execute on function public.create_dream_board_post_v2(text, text, boolean, text, text, text, text, text, text, text) from public;
grant execute on function public.get_dream_board_posts(integer) to anon, authenticated;
grant execute on function public.create_dream_board_post_v2(text, text, boolean, text, text, text, text, text, text, text) to authenticated;

notify pgrst, 'reload schema';

commit;

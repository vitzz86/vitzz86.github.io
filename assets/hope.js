(() => {
  "use strict";

  const STORAGE = {
    posts: "vitzz86-dream-board-posts-v1",
    loved: "vitzz86-dream-board-loved-v1",
    comments: "vitzz86-dream-board-comments-v1",
    commentSubmissions: "vitzz86-dream-board-comment-submissions-v1",
    reports: "vitzz86-dream-board-reports-v1",
    theme: "vitzz86-dream-board-theme",
    submissions: "vitzz86-dream-board-submissions-v1"
  };

  const TYPES = {
    hope: { label: "Hope", icon: "✨" },
    dream: { label: "Dream", icon: "☁️" },
    motivation: { label: "Motivation", icon: "⚡" },
    gratitude: { label: "Gratitude", icon: "💜" },
    feedback: { label: "Feedback", icon: "💬" },
    advice: { label: "Advice", icon: "💡" },
    general: { label: "General", icon: "🌈" }
  };

  const SPOTIFY_TYPES = {
    playlist: "playlist",
    album: "album",
    track: "song"
  };

  const YOUTUBE_TYPES = {
    video: "video",
    playlist: "playlist"
  };

  const YOUTUBE_ICON_URL = "https://www.gstatic.com/youtube/img/branding/favicon/favicon_144x144.png";

  const EMOJIS = [
    "✨", "💜", "🌈", "🚀", "🌱", "☀️", "🌟", "💪",
    "🙏", "😊", "🥰", "😂", "😭", "❤️", "🔥", "🎉",
    "🎵", "☁️", "💡", "👏", "🤞", "🫶", "🌍", "☕"
  ];

  const BACKEND_CONFIG = window.DREAM_BOARD_CONFIG || {};
  const backendConfigured = Boolean(
    /^https:\/\/[a-z0-9-]+\.supabase\.co$/i.test(BACKEND_CONFIG.supabaseUrl || "") &&
    /^sb_publishable_|^eyJ/i.test(BACKEND_CONFIG.supabasePublishableKey || "")
  );
  let database = null;
  const postCardCache = new Map();
  const commentThreads = new Map();
  const spotifyControllers = new Map();
  const playingSpotifyPosts = new Set();
  const youtubePlayers = new Map();
  const playingYouTubePosts = new Set();
  let spotifyIframeApi = null;
  let youtubeIframeApiReady = false;

  const el = {
    html: document.documentElement,
    form: document.querySelector("#postForm"),
    composerShell: document.querySelector(".composer-shell"),
    composerFields: document.querySelector("#composerFields"),
    composerToggle: document.querySelector("#composerToggle"),
    composerToggleLabel: document.querySelector("#composerToggleLabel"),
    composerToggleIcon: document.querySelector("#composerToggleIcon"),
    message: document.querySelector("#message"),
    characterCount: document.querySelector("#characterCount"),
    emojiButton: document.querySelector("#emojiButton"),
    emojiPicker: document.querySelector("#emojiPicker"),
    composerTypes: document.querySelector("#composerTypes"),
    displayName: document.querySelector("#displayName"),
    nameField: document.querySelector("#nameField"),
    mediaUrl: document.querySelector("#mediaUrl"),
    mediaStatus: document.querySelector("#mediaStatus"),
    mediaPreview: document.querySelector("#mediaPreview"),
    mediaProviderIcon: document.querySelector("#mediaProviderIcon"),
    mediaProviderLink: document.querySelector("#mediaProviderLink"),
    mediaPreviewIcon: document.querySelector("#mediaPreviewIcon"),
    clearMedia: document.querySelector("#clearMedia"),
    removeMedia: document.querySelector("#removeMedia"),
    publishButton: document.querySelector("#publishButton"),
    publishLabel: document.querySelector("#publishLabel"),
    formError: document.querySelector("#formError"),
    categoryFilters: document.querySelector("#categoryFilters"),
    searchInput: document.querySelector("#searchInput"),
    sortControl: document.querySelector("#sortControl"),
    timeFilter: document.querySelector("#timeFilter"),
    boardSummary: document.querySelector("#boardSummary"),
    board: document.querySelector("#board"),
    boardLoading: document.querySelector("#boardLoading"),
    emptyState: document.querySelector("#emptyState"),
    clearFilters: document.querySelector("#clearFilters"),
    messageCount: document.querySelector("#messageCount"),
    playlistCount: document.querySelector("#playlistCount"),
    youtubeCount: document.querySelector("#youtubeCount"),
    reportDialog: document.querySelector("#reportDialog"),
    reportForm: document.querySelector("#reportForm"),
    reportReason: document.querySelector("#reportReason"),
    toast: document.querySelector("#toast")
  };

  const params = new URLSearchParams(window.location.search);
  const initialFilter = params.get("type") || (params.get("music") === "true" ? "music" : "all");
  const state = {
    posts: backendConfigured ? [] : loadPosts(),
    loved: new Set(readJson(STORAGE.loved, [])),
    backendConfigured,
    backendReady: false,
    backendLoading: backendConfigured,
    backendError: "",
    filter: initialFilter === "music" || TYPES[initialFilter] ? initialFilter : "all",
    sort: ["latest", "loved", "random", "oldest"].includes(params.get("sort")) ? params.get("sort") : "latest",
    period: ["all", "today", "week", "month", "year"].includes(params.get("period")) ? params.get("period") : "all",
    search: (params.get("search") || "").trim(),
    mediaProvider: "spotify",
    media: null,
    reportPostId: null,
    randomOrder: new Map(),
    mediaRequest: 0
  };

  function readJson(key, fallback) {
    try {
      const parsed = JSON.parse(localStorage.getItem(key));
      return parsed ?? fallback;
    } catch {
      return fallback;
    }
  }

  function writeJson(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* Storage can be unavailable in private modes. */ }
  }

  function loadPosts() {
    const stored = readJson(STORAGE.posts, null);
    return Array.isArray(stored) ? stored : [];
  }

  function mapDatabasePost(row) {
    const spotifyItemId = row.spotify_item_id || row.spotify_playlist_id;
    const spotifyType = SPOTIFY_TYPES[row.spotify_content_type] ? row.spotify_content_type : "playlist";
    const spotify = spotifyItemId ? {
      id: spotifyItemId,
      type: spotifyType,
      canonicalUrl: row.spotify_canonical_url,
      embedUrl: row.spotify_embed_url,
      title: row.spotify_title || `Spotify ${SPOTIFY_TYPES[spotifyType]}`,
      creator: row.spotify_creator_name || "Spotify",
      thumbnailUrl: row.spotify_thumbnail_url || null
    } : null;
    const youtubeItemId = row.youtube_item_id;
    const youtubeType = YOUTUBE_TYPES[row.youtube_content_type] ? row.youtube_content_type : "video";
    const youtube = youtubeItemId ? {
      id: youtubeItemId,
      type: youtubeType,
      canonicalUrl: row.youtube_canonical_url,
      embedUrl: row.youtube_embed_url,
      title: row.youtube_title || `YouTube ${YOUTUBE_TYPES[youtubeType]}`,
      creator: row.youtube_creator_name || "YouTube",
      thumbnailUrl: row.youtube_thumbnail_url || null
    } : null;
    return {
      id: row.id,
      message: row.message,
      type: row.type,
      displayName: row.is_anonymous ? "Anonymous" : (row.display_name || "Anonymous"),
      isAnonymous: row.is_anonymous,
      reactionCount: Number(row.reaction_count || 0),
      commentCount: Number(row.comment_count || 0),
      createdAt: row.created_at,
      spotify,
      youtube,
      lovedByMe: Boolean(row.loved_by_me)
    };
  }

  function getPostMedia(post) {
    if (post.spotify) return { provider: "spotify", ...post.spotify };
    if (post.youtube) return { provider: "youtube", ...post.youtube };
    return null;
  }

  async function refreshDatabasePosts() {
    const { data, error } = await database.rpc("get_dream_board_posts", { p_limit: 100 });
    if (error) throw error;
    const rows = Array.isArray(data) ? data : [];
    state.posts = rows.map(mapDatabasePost);
    state.loved = new Set(rows.filter((row) => row.loved_by_me).map((row) => row.id));
    state.backendLoading = false;
    state.backendError = "";
    renderBoard();
  }

  async function initBackend() {
    if (!state.backendConfigured) return;
    try {
      if (!window.supabase?.createClient) throw new Error("Supabase library unavailable");
      database = window.supabase.createClient(
        BACKEND_CONFIG.supabaseUrl,
        BACKEND_CONFIG.supabasePublishableKey,
        {
          auth: {
            persistSession: true,
            autoRefreshToken: true,
            detectSessionInUrl: false
          }
        }
      );
      const { data: sessionData, error: sessionError } = await database.auth.getSession();
      if (sessionError) throw sessionError;
      if (!sessionData.session) {
        const { error: signInError } = await database.auth.signInAnonymously();
        if (signInError) throw signInError;
      }
      state.backendReady = true;
      await refreshDatabasePosts();
    } catch (error) {
      state.backendReady = false;
      state.backendLoading = false;
      state.backendError = error?.message || "Dream Board connection failed";
      renderBoard();
      showToast("The shared Dream Board is temporarily unavailable.");
    }
  }

  function friendlyBackendError(error, fallback) {
    const message = String(error?.message || "").toLowerCase();
    if (message.includes("wait before posting")) return "You’ve shared three messages recently. Please wait a few minutes before posting again.";
    if (message.includes("wait before commenting")) return "You’ve added several comments recently. Please wait a few minutes before commenting again.";
    if (message.includes("daily posting limit")) return "You’ve reached today’s posting limit. Please come back tomorrow.";
    if (message.includes("daily comment limit")) return "You’ve reached today’s comment limit. Please come back tomorrow.";
    if (message.includes("already submitted")) return "This message was already submitted.";
    if (message.includes("already added that comment")) return "You already added that comment recently.";
    if (message.includes("excessive repeated")) return "Please remove excessive repeated characters.";
    if (message.includes("anonymous sign-ins are disabled")) return "Anonymous posting is not enabled yet.";
    if (message.includes("schema cache") || message.includes("could not find the function")) return "The Dream Board was just updated. Please refresh this page and try again.";
    return fallback;
  }

  function randomId() {
    return typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `post-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
  }

  function debounce(fn, delay) {
    let timer;
    return (...args) => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => fn(...args), delay);
    };
  }

  function showToast(message) {
    el.toast.textContent = message;
    el.toast.classList.add("visible");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => el.toast.classList.remove("visible"), 3200);
  }

  function setTheme(theme, persist = true) {
    const safeTheme = theme === "dark" ? "dark" : "light";
    el.html.dataset.theme = safeTheme;
    document.querySelectorAll("[data-theme-value]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.themeValue === safeTheme));
    });
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", safeTheme === "dark" ? "#060a12" : "#f8f9fd");
    if (persist) localStorage.setItem(STORAGE.theme, safeTheme);
  }

  function initTheme() {
    const saved = localStorage.getItem(STORAGE.theme);
    const preferred = window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    setTheme(saved || preferred, false);
  }

  function renderComposerTypes() {
    el.composerTypes.replaceChildren();
    Object.entries(TYPES).forEach(([value, info], index) => {
      const label = document.createElement("label");
      label.className = "type-choice";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "type";
      input.value = value;
      input.checked = index === 0;
      const span = document.createElement("span");
      span.className = "choice-content";
      const icon = makeText("span", "category-icon", info.icon);
      icon.setAttribute("aria-hidden", "true");
      span.append(icon, makeText("span", "category-label", info.label));
      label.dataset.type = value;
      label.append(input, span);
      el.composerTypes.append(label);
    });
  }

  function renderFilters() {
    el.categoryFilters.replaceChildren();
    const filters = [
      ["all", "▦", "All"],
      ...Object.entries(TYPES).map(([key, info]) => [key, info.icon, info.label]),
      ["music", "🎬", "With Media"]
    ];
    filters.forEach(([key, icon, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `filter-chip${state.filter === key ? " active" : ""}`;
      button.dataset.filter = key;
      button.setAttribute("aria-pressed", String(state.filter === key));
      const iconNode = makeText("span", "category-icon", icon);
      iconNode.setAttribute("aria-hidden", "true");
      button.append(iconNode, makeText("span", "category-label", label));
      el.categoryFilters.append(button);
    });
  }

  function updateUrl() {
    // Changing the parent URL can reset third-party media embeds in some browsers.
    // Apply the URL state once playback pauses instead of interrupting the listener.
    if (playingSpotifyPosts.size || playingYouTubePosts.size) return;
    const query = new URLSearchParams();
    if (state.filter === "music") query.set("music", "true");
    else if (state.filter !== "all") query.set("type", state.filter);
    if (state.sort !== "latest") query.set("sort", state.sort);
    if (state.period !== "all") query.set("period", state.period);
    if (state.search) query.set("search", state.search);
    const suffix = query.toString();
    history.replaceState(null, "", `${window.location.pathname}${suffix ? `?${suffix}` : ""}${window.location.hash}`);
  }

  function isWithinPeriod(dateString, period) {
    if (period === "all") return true;
    const date = new Date(dateString);
    const now = new Date();
    const start = new Date(now);
    if (period === "today") start.setHours(0, 0, 0, 0);
    if (period === "week") start.setDate(now.getDate() - 7);
    if (period === "month") start.setMonth(now.getMonth() - 1);
    if (period === "year") start.setFullYear(now.getFullYear() - 1);
    return date >= start;
  }

  function getVisiblePosts() {
    const needle = state.search.toLocaleLowerCase();
    const filtered = state.posts.filter((post) => {
      if (state.filter === "music" && !getPostMedia(post)) return false;
      if (state.filter !== "all" && state.filter !== "music" && post.type !== state.filter) return false;
      if (!isWithinPeriod(post.createdAt, state.period)) return false;
      if (!needle) return true;
      return [post.message, post.displayName, post.spotify?.title, post.spotify?.creator, post.youtube?.title, post.youtube?.creator]
        .filter(Boolean)
        .some((value) => value.toLocaleLowerCase().includes(needle));
    });

    if (state.sort === "random") {
      filtered.forEach((post) => {
        if (!state.randomOrder.has(post.id)) state.randomOrder.set(post.id, Math.random());
      });
      return filtered.sort((a, b) => state.randomOrder.get(a.id) - state.randomOrder.get(b.id));
    }
    if (state.sort === "loved") {
      return filtered.sort((a, b) => b.reactionCount - a.reactionCount || new Date(b.createdAt) - new Date(a.createdAt));
    }
    const direction = state.sort === "oldest" ? 1 : -1;
    return filtered.sort((a, b) => direction * (new Date(a.createdAt) - new Date(b.createdAt)));
  }

  function relativeTime(dateString) {
    const seconds = Math.max(1, Math.round((Date.now() - new Date(dateString).getTime()) / 1000));
    const units = [
      [31536000, "year"],
      [2592000, "month"],
      [604800, "week"],
      [86400, "day"],
      [3600, "hour"],
      [60, "minute"]
    ];
    for (const [size, label] of units) {
      if (seconds >= size) {
        const amount = Math.floor(seconds / size);
        return `${amount} ${label}${amount === 1 ? "" : "s"} ago`;
      }
    }
    return "just now";
  }

  function makeText(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = text;
    return node;
  }

  function makePlaylist(post) {
    const wrapper = document.createElement("div");
    wrapper.className = "playlist-card media-card";
    wrapper.dataset.postId = String(post.id);
    wrapper.dataset.spotifyType = post.spotify.type;
    wrapper.dataset.spotifyUrl = post.spotify.canonicalUrl || post.spotify.embedUrl;
    const spotifyLabel = SPOTIFY_TYPES[post.spotify.type] || "music";
    const embed = document.createElement("div");
    embed.className = "spotify-embed-host";
    embed.setAttribute("role", "group");
    embed.setAttribute("aria-label", `Spotify ${spotifyLabel}: ${post.spotify.title}`);

    const actions = document.createElement("div");
    actions.className = "player-actions";
    const open = makeText("a", "", "Open in Spotify ↗");
    open.href = post.spotify.canonicalUrl;
    open.target = "_blank";
    open.rel = "noopener";
    actions.append(open);
    wrapper.append(embed, actions);

    return wrapper;
  }

  function makeYouTubePlayer(post) {
    const wrapper = document.createElement("div");
    wrapper.className = "youtube-card media-card";
    wrapper.dataset.postId = String(post.id);
    const youtubeLabel = YOUTUBE_TYPES[post.youtube.type] || "video";
    const iframe = document.createElement("iframe");
    const embedUrl = new URL(post.youtube.embedUrl);
    embedUrl.searchParams.set("enablejsapi", "1");
    embedUrl.searchParams.set("playsinline", "1");
    embedUrl.searchParams.set("rel", "0");
    if (/^https?:$/.test(window.location.protocol)) embedUrl.searchParams.set("origin", window.location.origin);
    iframe.src = embedUrl.toString();
    iframe.loading = "lazy";
    iframe.allowFullscreen = true;
    iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
    iframe.title = `YouTube ${youtubeLabel}: ${post.youtube.title}`;

    const actions = document.createElement("div");
    actions.className = "player-actions youtube-actions";
    const open = makeText("a", "", "Open on YouTube ↗");
    open.href = post.youtube.canonicalUrl;
    open.target = "_blank";
    open.rel = "noopener";
    actions.append(open);
    wrapper.append(iframe, actions);
    return wrapper;
  }

  function setSpotifyPlaying(postId, playing) {
    const key = String(postId);
    const changed = playing ? !playingSpotifyPosts.has(key) : playingSpotifyPosts.has(key);
    if (!changed) return;
    if (playing) playingSpotifyPosts.add(key);
    else playingSpotifyPosts.delete(key);
    renderBoard();
  }

  function initializeSpotifyEmbed(wrapper) {
    if (!spotifyIframeApi || wrapper.dataset.spotifyReady === "true") return;
    const host = wrapper.querySelector(".spotify-embed-host");
    if (!host) return;
    const postId = wrapper.dataset.postId;
    wrapper.dataset.spotifyReady = "true";
    spotifyIframeApi.createController(host, {
      url: wrapper.dataset.spotifyUrl,
      width: "100%",
      height: wrapper.dataset.spotifyType === "track" ? 152 : 352
    }, (controller) => {
      spotifyControllers.set(postId, controller);
      controller.addListener("playback_started", () => setSpotifyPlaying(postId, true));
      controller.addListener("playback_update", (event) => {
        if (typeof event?.data?.isPaused === "boolean") {
          setSpotifyPlaying(postId, !event.data.isPaused);
        }
      });
    });
  }

  function initializeSpotifyEmbeds(root = document) {
    root.querySelectorAll(".playlist-card").forEach(initializeSpotifyEmbed);
  }

  function setYouTubePlaying(postId, playing) {
    const key = String(postId);
    const changed = playing ? !playingYouTubePosts.has(key) : playingYouTubePosts.has(key);
    if (!changed) return;
    if (playing) playingYouTubePosts.add(key);
    else playingYouTubePosts.delete(key);
    renderBoard();
  }

  function initializeYouTubeEmbed(wrapper) {
    if (!youtubeIframeApiReady || wrapper.dataset.youtubeReady === "true" || !window.YT?.Player) return;
    const iframe = wrapper.querySelector("iframe");
    if (!iframe) return;
    const postId = wrapper.dataset.postId;
    wrapper.dataset.youtubeReady = "true";
    const player = new window.YT.Player(iframe, {
      events: {
        onStateChange: (event) => {
          if (event.data === window.YT.PlayerState.PLAYING) setYouTubePlaying(postId, true);
          if ([window.YT.PlayerState.PAUSED, window.YT.PlayerState.ENDED, window.YT.PlayerState.CUED].includes(event.data)) {
            setYouTubePlaying(postId, false);
          }
        },
        onError: () => setYouTubePlaying(postId, false)
      }
    });
    youtubePlayers.set(postId, player);
  }

  function initializeYouTubeEmbeds(root = document) {
    root.querySelectorAll(".youtube-card").forEach(initializeYouTubeEmbed);
  }

  function preserveMediaPlayback() {
    const activeControllers = [...playingSpotifyPosts]
      .map((postId) => spotifyControllers.get(postId))
      .filter(Boolean);
    activeControllers.forEach((controller) => controller.resume());
    const activeYouTubePlayers = [...playingYouTubePosts]
      .map((postId) => youtubePlayers.get(postId))
      .filter(Boolean);
    activeYouTubePlayers.forEach((player) => player.playVideo());
    if (!activeControllers.length && !activeYouTubePlayers.length) return;
    requestAnimationFrame(() => {
      activeControllers.forEach((controller) => controller.resume());
      activeYouTubePlayers.forEach((player) => player.playVideo());
    });
  }

  window.onSpotifyIframeApiReady = (api) => {
    spotifyIframeApi = api;
    initializeSpotifyEmbeds();
  };

  window.onYouTubeIframeAPIReady = () => {
    youtubeIframeApiReady = true;
    initializeYouTubeEmbeds();
  };

  function mapDatabaseComment(row) {
    return {
      id: row.id,
      message: row.message,
      displayName: row.is_anonymous ? "Anonymous" : (row.display_name || "Anonymous"),
      isAnonymous: row.is_anonymous,
      createdAt: row.created_at
    };
  }

  function getLocalComments(postId) {
    return readJson(STORAGE.comments, [])
      .filter((comment) => String(comment.postId) === String(postId))
      .sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));
  }

  function renderCommentList(panel, comments, message = "") {
    const list = panel.querySelector(".comment-list");
    if (message) {
      list.replaceChildren(makeText("p", "comment-empty", message));
      return;
    }
    if (!comments.length) {
      list.replaceChildren(makeText("p", "comment-empty", "Start the conversation with something kind ✨"));
      return;
    }
    const items = comments.map((comment) => {
      const item = document.createElement("article");
      item.className = "comment-item";
      const meta = document.createElement("div");
      meta.className = "comment-meta";
      const author = document.createElement("span");
      author.className = "comment-author";
      author.append(
        makeText("span", "comment-avatar", comment.isAnonymous ? "👤" : "✦"),
        makeText("strong", "", comment.displayName || "Anonymous")
      );
      const time = makeText("time", "", relativeTime(comment.createdAt));
      time.dateTime = comment.createdAt;
      meta.append(author, time);
      item.append(meta, makeText("p", "comment-message", comment.message));
      return item;
    });
    list.replaceChildren(...items);
  }

  async function loadComments(postId, panel, force = false) {
    const key = String(postId);
    const cached = commentThreads.get(key);
    if (cached?.loaded && !force) {
      renderCommentList(panel, cached.items);
      return;
    }
    renderCommentList(panel, [], "Loading comments…");
    try {
      let comments;
      if (state.backendConfigured) {
        if (!state.backendReady) throw new Error("The shared Dream Board is still connecting.");
        const { data, error } = await database.rpc("get_dream_board_comments", {
          p_post_id: postId,
          p_limit: 50
        });
        if (error) throw error;
        comments = (Array.isArray(data) ? data : []).map(mapDatabaseComment);
      } else {
        comments = getLocalComments(postId);
      }
      commentThreads.set(key, { loaded: true, items: comments });
      renderCommentList(panel, comments);
    } catch (error) {
      renderCommentList(panel, [], friendlyBackendError(error, "Comments could not be loaded. Please try again."));
    }
  }

  function updateCommentCount(postId, value) {
    const post = state.posts.find((item) => String(item.id) === String(postId));
    if (post) post.commentCount = Math.max(0, Number(value || 0));
    const card = postCardCache.get(String(postId));
    const count = card?.querySelector(".comment-count");
    if (count) count.textContent = String(post?.commentCount || 0);
  }

  function localCommentRateLimitError() {
    const now = Date.now();
    const history = readJson(STORAGE.commentSubmissions, []).filter((stamp) => now - stamp < 24 * 60 * 60 * 1000);
    if (history.filter((stamp) => now - stamp < 10 * 60 * 1000).length >= 8) return "You’ve added several comments recently. Please wait a few minutes before commenting again.";
    if (history.length >= 40) return "You’ve reached today’s comment limit. Please come back tomorrow.";
    return "";
  }

  async function submitComment(event, postId, panel) {
    event.preventDefault();
    const form = event.currentTarget;
    const messageInput = form.querySelector(".comment-input");
    const nameToggle = form.querySelector(".comment-name-toggle input");
    const nameInput = form.querySelector(".comment-name-input");
    const submitButton = form.querySelector(".comment-submit");
    const status = form.querySelector(".comment-status");
    const message = messageInput.value.trim();
    const named = nameToggle.checked;
    const name = nameInput.value.trim();
    let error = "";
    if (!message) error = "Write a comment first.";
    else if (message.length > 280) error = "Please keep your comment to 280 characters.";
    else if (named && name.length < 2) error = "Enter at least 2 characters for your name.";
    else if (named && name.length > 40) error = "Please keep your name to 40 characters.";
    else error = moderationError(message) || (state.backendConfigured ? "" : localCommentRateLimitError());
    if (!error && state.backendConfigured && !state.backendReady) error = "The shared Dream Board is still connecting. Please try again shortly.";
    if (error) {
      status.textContent = error;
      status.className = "comment-status error";
      return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Posting…";
    status.textContent = "";
    try {
      let nextCount;
      if (state.backendConfigured) {
        const { data, error: databaseError } = await database.rpc("create_dream_board_comment", {
          p_post_id: postId,
          p_message: message,
          p_is_anonymous: !named,
          p_display_name: named ? name : null
        });
        if (databaseError) throw databaseError;
        const result = Array.isArray(data) ? data[0] : data;
        nextCount = Number(result?.comment_count || 0);
      } else {
        const comments = readJson(STORAGE.comments, []);
        comments.push({
          id: randomId(),
          postId,
          message,
          displayName: named ? name : "Anonymous",
          isAnonymous: !named,
          createdAt: new Date().toISOString()
        });
        writeJson(STORAGE.comments, comments);
        const history = readJson(STORAGE.commentSubmissions, []);
        writeJson(STORAGE.commentSubmissions, [...history, Date.now()]);
        nextCount = comments.filter((comment) => String(comment.postId) === String(postId)).length;
      }
      updateCommentCount(postId, nextCount);
      if (!state.backendConfigured) writeJson(STORAGE.posts, state.posts);
      messageInput.value = "";
      await loadComments(postId, panel, true);
      status.textContent = "Comment added ✨";
      status.className = "comment-status success";
    } catch (databaseError) {
      status.textContent = friendlyBackendError(databaseError, "We couldn’t add your comment. Please try again.");
      status.className = "comment-status error";
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Comment";
    }
  }

  function makeCommentsPanel(postId) {
    const panel = document.createElement("section");
    panel.className = "comments-panel";
    panel.id = `comments-${postId}`;
    panel.hidden = true;
    panel.setAttribute("aria-label", "Comments");

    const heading = document.createElement("div");
    heading.className = "comments-heading";
    heading.append(makeText("strong", "", "Comments"), makeText("span", "", "Kind words make the board brighter"));
    const list = document.createElement("div");
    list.className = "comment-list";
    list.setAttribute("aria-live", "polite");

    const form = document.createElement("form");
    form.className = "comment-form";
    const inputLabel = makeText("label", "sr-only", "Add a comment");
    const input = document.createElement("textarea");
    input.className = "comment-input";
    input.rows = 2;
    input.maxLength = 280;
    input.required = true;
    input.placeholder = "Add a kind comment…";
    inputLabel.htmlFor = `comment-input-${postId}`;
    input.id = `comment-input-${postId}`;

    const options = document.createElement("div");
    options.className = "comment-options";
    const identity = document.createElement("label");
    identity.className = "comment-name-toggle";
    const identityInput = document.createElement("input");
    identityInput.type = "checkbox";
    identity.append(identityInput, makeText("span", "", "Add my name"));
    const nameInput = document.createElement("input");
    nameInput.className = "comment-name-input";
    nameInput.type = "text";
    nameInput.minLength = 2;
    nameInput.maxLength = 40;
    nameInput.placeholder = "Name or nickname";
    nameInput.autocomplete = "nickname";
    nameInput.hidden = true;
    const submit = makeText("button", "comment-submit", "Comment");
    submit.type = "submit";
    options.append(identity, nameInput, submit);
    const status = makeText("p", "comment-status", "");
    status.setAttribute("aria-live", "polite");
    form.append(inputLabel, input, options, status);
    form.addEventListener("submit", (event) => submitComment(event, postId, panel));
    identityInput.addEventListener("change", () => {
      nameInput.hidden = !identityInput.checked;
      nameInput.required = identityInput.checked;
      if (identityInput.checked) nameInput.focus();
    });
    panel.append(heading, list, form);
    return panel;
  }

  function toggleComments(card, postId, button, panel) {
    const opening = panel.hidden;
    panel.hidden = !opening;
    card.classList.toggle("comments-open", opening);
    button.setAttribute("aria-expanded", String(opening));
    if (opening) loadComments(postId, panel);
  }

  function makePostCard(post, index) {
    const card = document.createElement("article");
    card.className = "post-card";
    if (post.spotify) card.classList.add("has-media", "has-spotify");
    if (post.youtube) card.classList.add("has-media", "has-youtube");
    card.dataset.type = post.type;
    card.dataset.postId = post.id;
    card.style.animationDelay = `${Math.min(index * 35, 280)}ms`;

    const head = document.createElement("div");
    head.className = "card-head";
    const type = TYPES[post.type] || TYPES.general;
    const typePill = document.createElement("span");
    typePill.className = "type-pill";
    const typeIcon = makeText("span", "category-icon", type.icon);
    typeIcon.setAttribute("aria-hidden", "true");
    typePill.append(makeText("span", "category-label", type.label), typeIcon);
    head.append(typePill);
    const menuWrap = document.createElement("div");
    menuWrap.className = "menu-wrap";
    const menuButton = makeText("button", "menu-button", "⋮");
    menuButton.type = "button";
    menuButton.setAttribute("aria-label", "Post options");
    menuButton.setAttribute("aria-expanded", "false");
    const menu = document.createElement("div");
    menu.className = "card-menu";
    menu.hidden = true;
    const reportButton = makeText("button", "", "Report post");
    reportButton.type = "button";
    menu.append(reportButton);
    menuWrap.append(menuButton, menu);
    head.append(menuWrap);
    card.append(head, makeText("p", "post-message", post.message));

    if (post.spotify) card.append(makePlaylist(post));
    if (post.youtube) card.append(makeYouTubePlayer(post));

    const meta = document.createElement("div");
    meta.className = "card-meta";
    const author = document.createElement("span");
    author.className = "author";
    author.append(makeText("span", "author-avatar", post.isAnonymous ? "👤" : "✦"), makeText("span", "author-name", post.displayName || "Anonymous"));
    const time = makeText("time", "post-time", relativeTime(post.createdAt));
    time.dateTime = post.createdAt;
    meta.append(author, time);
    const footer = document.createElement("div");
    footer.className = "card-footer";
    const love = document.createElement("button");
    love.type = "button";
    love.className = `love-button${state.loved.has(post.id) ? " loved" : ""}`;
    love.setAttribute("aria-label", state.loved.has(post.id) ? "Remove love reaction" : "Love this post");
    const heart = makeText("span", "heart-glyph", state.loved.has(post.id) ? "♥" : "♡");
    heart.setAttribute("aria-hidden", "true");
    const count = makeText("span", "love-count", String(post.reactionCount || 0));
    love.append(heart, count);
    const commentButton = document.createElement("button");
    commentButton.type = "button";
    commentButton.className = "comment-button";
    commentButton.setAttribute("aria-label", "Open comments");
    commentButton.setAttribute("aria-expanded", "false");
    const commentGlyph = makeText("span", "comment-glyph", "💬");
    commentGlyph.setAttribute("aria-hidden", "true");
    const commentCount = makeText("span", "comment-count", String(post.commentCount || 0));
    commentButton.append(commentGlyph, commentCount);
    const commentsPanel = makeCommentsPanel(post.id);
    commentButton.setAttribute("aria-controls", commentsPanel.id);
    footer.append(love, commentButton);
    card.append(meta, footer, commentsPanel);

    menuButton.addEventListener("click", () => {
      const next = menu.hidden;
      document.querySelectorAll(".card-menu").forEach((other) => { other.hidden = true; });
      document.querySelectorAll(".menu-button").forEach((other) => other.setAttribute("aria-expanded", "false"));
      menu.hidden = !next;
      menuButton.setAttribute("aria-expanded", String(next));
    });

    reportButton.addEventListener("click", () => {
      menu.hidden = true;
      state.reportPostId = post.id;
      el.reportReason.value = "";
      if (typeof el.reportDialog.showModal === "function") el.reportDialog.showModal();
    });

    love.addEventListener("click", () => toggleLove(post.id));
    commentButton.addEventListener("click", () => toggleComments(card, post.id, commentButton, commentsPanel));
    return card;
  }

  function updatePostCard(card, post, index) {
    const type = TYPES[post.type] || TYPES.general;
    const loved = state.loved.has(post.id);
    card.dataset.type = post.type;
    card.style.animationDelay = `${Math.min(index * 35, 280)}ms`;
    card.querySelector(".type-pill .category-label").textContent = type.label;
    card.querySelector(".type-pill .category-icon").textContent = type.icon;
    card.querySelector(".post-message").textContent = post.message;
    card.querySelector(".author-avatar").textContent = post.isAnonymous ? "👤" : "✦";
    card.querySelector(".author-name").textContent = post.displayName || "Anonymous";
    const time = card.querySelector(".post-time");
    time.dateTime = post.createdAt;
    time.textContent = relativeTime(post.createdAt);
    const love = card.querySelector(".love-button");
    love.classList.toggle("loved", loved);
    love.setAttribute("aria-label", loved ? "Remove love reaction" : "Love this post");
    love.querySelector(".heart-glyph").textContent = loved ? "♥" : "♡";
    love.querySelector(".love-count").textContent = String(post.reactionCount || 0);
    card.querySelector(".comment-count").textContent = String(post.commentCount || 0);
  }

  function getPersistentPostCard(post, index) {
    const key = String(post.id);
    let card = postCardCache.get(key);
    if (!card) {
      card = makePostCard(post, index);
      postCardCache.set(key, card);
      el.board.append(card);
      initializeSpotifyEmbeds(card);
      initializeYouTubeEmbeds(card);
    }
    updatePostCard(card, post, index);
    return card;
  }

  function renderBoard() {
    renderFilters();
    el.sortControl.querySelectorAll("button").forEach((button) => {
      const active = button.dataset.sort === state.sort;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    el.timeFilter.value = state.period;
    updateUrl();

    if (state.backendLoading) {
      el.board.replaceChildren();
      el.boardLoading.hidden = false;
      el.emptyState.hidden = true;
      el.messageCount.textContent = "—";
      el.playlistCount.textContent = "—";
      el.youtubeCount.textContent = "—";
      el.boardSummary.textContent = "Loading the board…";
      return;
    }

    el.boardLoading.hidden = true;
    const posts = getVisiblePosts();
    const liveIds = new Set(state.posts.map((post) => String(post.id)));
    postCardCache.forEach((card, id) => {
      if (!liveIds.has(id)) {
        spotifyControllers.get(id)?.destroy();
        spotifyControllers.delete(id);
        playingSpotifyPosts.delete(id);
        youtubePlayers.get(id)?.destroy();
        youtubePlayers.delete(id);
        playingYouTubePosts.delete(id);
        card.remove();
        postCardCache.delete(id);
      }
    });
    const visibleOrder = new Map(posts.map((post, index) => [String(post.id), index]));
    state.posts.forEach((post, index) => {
      const card = getPersistentPostCard(post, index);
      const order = visibleOrder.get(String(post.id));
      const visible = order !== undefined;
      const postId = String(post.id);
      const isPlayingOutsideFilter = !visible && (
        (post.spotify && playingSpotifyPosts.has(postId)) ||
        (post.youtube && playingYouTubePosts.has(postId))
      );
      card.hidden = !visible && !isPlayingOutsideFilter;
      card.classList.toggle("is-playing-filtered", Boolean(isPlayingOutsideFilter));
      card.setAttribute("aria-label", isPlayingOutsideFilter ? "Attached media continues playing" : "Dream Board post");
      card.style.order = String(order ?? (posts.length + index));
    });
    el.emptyState.hidden = posts.length > 0;
    if (!posts.length) {
      const boardIsEmpty = state.posts.length === 0;
      const boardUnavailable = state.backendConfigured && state.backendError && boardIsEmpty;
      el.emptyState.querySelector("h2").textContent = boardUnavailable ? "Dream Board unavailable" : boardIsEmpty ? "Be the first to share" : "No messages found";
      el.emptyState.querySelector("p").textContent = boardUnavailable
        ? "The shared board could not load. Please refresh and try again."
        : boardIsEmpty
        ? "Leave the first hope, dream, or message on Vito’s Dream Board."
        : state.search
          ? "No posts match your search."
          : "No messages match these filters.";
      el.clearFilters.hidden = boardIsEmpty || boardUnavailable;
    }
    el.messageCount.textContent = state.posts.length.toLocaleString();
    el.playlistCount.textContent = state.posts.filter((post) => post.spotify).length.toLocaleString();
    el.youtubeCount.textContent = state.posts.filter((post) => post.youtube).length.toLocaleString();
    const visibleLabel = `${posts.length.toLocaleString()} ${posts.length === 1 ? "note" : "notes"}`;
    el.boardSummary.textContent = posts.length === state.posts.length
      ? `${visibleLabel} · ${state.sort === "latest" ? "Newest first" : state.sort === "oldest" ? "Oldest first" : state.sort === "loved" ? "Most loved first" : "Shuffled"}`
      : `${visibleLabel} matching your view`;
    preserveMediaPlayback();
  }

  function renderEmojiPicker() {
    const buttons = EMOJIS.map((emoji) => {
      const button = makeText("button", "emoji-option", emoji);
      button.type = "button";
      button.dataset.emoji = emoji;
      button.setAttribute("aria-label", `Add ${emoji}`);
      return button;
    });
    el.emojiPicker.replaceChildren(...buttons);
  }

  function setEmojiPicker(open) {
    el.emojiPicker.hidden = !open;
    el.emojiButton.setAttribute("aria-expanded", String(open));
  }

  function setComposerExpanded(expanded) {
    el.composerFields.hidden = !expanded;
    el.composerShell.classList.toggle("is-collapsed", !expanded);
    el.composerToggle.setAttribute("aria-expanded", String(expanded));
    el.composerToggle.setAttribute("aria-label", expanded ? "Collapse form" : "Open form");
    el.composerToggleLabel.textContent = expanded ? "Collapse form" : "Open form";
    el.composerToggleIcon.textContent = expanded ? "⌃" : "⌄";
    if (!expanded) setEmojiPicker(false);
  }

  function insertEmoji(emoji) {
    const start = el.message.selectionStart ?? el.message.value.length;
    const end = el.message.selectionEnd ?? start;
    if (el.message.value.length - (end - start) + emoji.length > 500) {
      showToast("Your message is already at the 500-character limit.");
      return;
    }
    el.message.setRangeText(emoji, start, end, "end");
    el.message.focus();
    updateComposer();
  }

  async function toggleLove(postId) {
    const post = state.posts.find((item) => item.id === postId);
    if (!post) return;
    if (state.backendConfigured) {
      if (!state.backendReady) {
        showToast("The shared Dream Board is still connecting. Please try again shortly.");
        return;
      }
      const wasLoved = state.loved.has(postId);
      const previousCount = post.reactionCount || 0;
      if (wasLoved) {
        state.loved.delete(postId);
        post.reactionCount = Math.max(0, previousCount - 1);
      } else {
        state.loved.add(postId);
        post.reactionCount = previousCount + 1;
      }
      renderBoard();
      const { data, error } = await database.rpc("toggle_dream_board_reaction", { p_post_id: postId });
      if (error) {
        post.reactionCount = previousCount;
        if (wasLoved) state.loved.add(postId);
        else state.loved.delete(postId);
        renderBoard();
        showToast("We couldn’t save that reaction. Please try again.");
        return;
      }
      const result = Array.isArray(data) ? data[0] : data;
      if (result) {
        post.reactionCount = Number(result.reaction_count || 0);
        if (result.loved) state.loved.add(postId);
        else state.loved.delete(postId);
        renderBoard();
      }
      return;
    }
    if (state.loved.has(postId)) {
      state.loved.delete(postId);
      post.reactionCount = Math.max(0, (post.reactionCount || 0) - 1);
    } else {
      state.loved.add(postId);
      post.reactionCount = (post.reactionCount || 0) + 1;
    }
    writeJson(STORAGE.loved, [...state.loved]);
    writeJson(STORAGE.posts, state.posts);
    renderBoard();
  }

  function parseSpotify(value) {
    const input = value.trim();
    const uri = input.match(/^spotify:(playlist|album|track):([A-Za-z0-9]{10,30})$/i);
    if (uri) return { type: uri[1].toLowerCase(), id: uri[2], isShort: false };
    let url;
    try { url = new URL(input); } catch { return null; }
    const hostname = url.hostname.toLowerCase();
    if (hostname === "spotify.link" || hostname.endsWith(".spotify.link")) return { shortUrl: url.toString(), isShort: true };
    if (hostname !== "open.spotify.com") return null;
    const match = url.pathname.match(/^\/(?:intl-[a-z]{2}\/)?(playlist|album|track)\/([A-Za-z0-9]{10,30})\/?$/i);
    return match ? { type: match[1].toLowerCase(), id: match[2], isShort: false } : null;
  }

  function parseYouTube(value) {
    let url;
    try { url = new URL(value.trim()); } catch { return null; }
    const hostname = url.hostname.toLowerCase().replace(/^(www\.|m\.|music\.)/, "");
    let videoId = null;
    let playlistId = null;
    if (hostname === "youtu.be") videoId = url.pathname.split("/").filter(Boolean)[0] || null;
    if (hostname === "youtube.com" || hostname === "youtube-nocookie.com") {
      if (url.pathname === "/watch") videoId = url.searchParams.get("v");
      const pathMatch = url.pathname.match(/^\/(?:shorts|embed|live)\/([A-Za-z0-9_-]{11})/i);
      if (pathMatch) videoId = pathMatch[1];
      if (url.pathname === "/playlist" || (!videoId && url.searchParams.has("list"))) playlistId = url.searchParams.get("list");
    }
    if (videoId && /^[A-Za-z0-9_-]{11}$/.test(videoId)) return { type: "video", id: videoId };
    if (playlistId && /^[A-Za-z0-9_-]{10,80}$/.test(playlistId)) return { type: "playlist", id: playlistId };
    return null;
  }

  async function resolveMediaInput(rawValue) {
    const request = ++state.mediaRequest;
    const provider = state.mediaProvider;
    state.media = null;
    renderMediaPreview();
    if (!rawValue.trim()) {
      setMediaStatus("", "");
      return;
    }

    if (provider === "youtube") {
      const parsed = parseYouTube(rawValue);
      if (!parsed) {
        setMediaStatus(/spotify/i.test(rawValue) ? "Switch to Spotify for that link." : "Share a YouTube video, Short, live video, or playlist link.", "error");
        return;
      }
      setMediaStatus("Validating YouTube link…", "");
      const contentLabel = YOUTUBE_TYPES[parsed.type];
      const canonicalUrl = parsed.type === "playlist"
        ? `https://www.youtube.com/playlist?list=${parsed.id}`
        : `https://www.youtube.com/watch?v=${parsed.id}`;
      const embedUrl = parsed.type === "playlist"
        ? `https://www.youtube.com/embed/videoseries?list=${parsed.id}`
        : `https://www.youtube.com/embed/${parsed.id}`;
      const youtube = {
        provider: "youtube",
        id: parsed.id,
        type: parsed.type,
        canonicalUrl,
        embedUrl,
        title: `YouTube ${contentLabel}`,
        creator: "Ready to play",
        thumbnailUrl: parsed.type === "video" ? `https://i.ytimg.com/vi/${parsed.id}/hqdefault.jpg` : null
      };
      try {
        const response = await fetch(`https://www.youtube.com/oembed?url=${encodeURIComponent(canonicalUrl)}&format=json`);
        if (response.ok) {
          const metadata = await response.json();
          youtube.title = String(metadata.title || youtube.title).slice(0, 120);
          youtube.creator = String(metadata.author_name || "YouTube").slice(0, 80);
          if (/^https:\/\//i.test(metadata.thumbnail_url || "")) youtube.thumbnailUrl = metadata.thumbnail_url;
        }
      } catch { /* The embed remains usable when optional metadata is unavailable. */ }
      if (request !== state.mediaRequest || state.mediaProvider !== provider) return;
      state.media = youtube;
      setMediaStatus(`${contentLabel[0].toUpperCase()}${contentLabel.slice(1)} ready to attach.`, "success");
      renderMediaPreview();
      return;
    }

    const parsed = parseSpotify(rawValue);
    if (!parsed) {
      setMediaStatus(/youtu(?:be|\.be)/i.test(rawValue) ? "Switch to YouTube for that link." : "Share a Spotify song, album, or playlist link.", "error");
      return;
    }
    setMediaStatus("Validating Spotify link…", "");
    let itemId = parsed.id;
    let contentType = parsed.type;
    if (parsed.isShort) {
      try {
        const response = await fetch(parsed.shortUrl, { method: "GET", redirect: "follow" });
        const resolved = parseSpotify(response.url);
        if (!resolved?.id || !resolved?.type) throw new Error("Unsupported Spotify link");
        itemId = resolved.id;
        contentType = resolved.type;
      } catch {
        if (request === state.mediaRequest) setMediaStatus("This short link could not be resolved here. Paste the full open.spotify.com link instead.", "error");
        return;
      }
    }
    if (request !== state.mediaRequest || state.mediaProvider !== provider) return;
    const contentLabel = SPOTIFY_TYPES[contentType];
    if (!contentLabel) {
      setMediaStatus("Only Spotify songs, albums, and playlists are supported.", "error");
      return;
    }
    const canonicalUrl = `https://open.spotify.com/${contentType}/${itemId}`;
    const spotify = {
      provider: "spotify",
      id: itemId,
      type: contentType,
      canonicalUrl,
      embedUrl: `https://open.spotify.com/embed/${contentType}/${itemId}`,
      title: `Spotify ${contentLabel}`,
      creator: "Ready to play"
    };
    try {
      const response = await fetch(`https://open.spotify.com/oembed?url=${encodeURIComponent(canonicalUrl)}`);
      if (response.ok) {
        const metadata = await response.json();
        spotify.title = String(metadata.title || spotify.title).slice(0, 120);
        spotify.creator = String(metadata.author_name || "Spotify").slice(0, 80);
        if (/^https:\/\//i.test(metadata.thumbnail_url || "")) spotify.thumbnailUrl = metadata.thumbnail_url;
      }
    } catch { /* The controlled embed remains valid even if optional metadata is unavailable. */ }
    if (request !== state.mediaRequest || state.mediaProvider !== provider) return;
    state.media = spotify;
    setMediaStatus(`${contentLabel[0].toUpperCase()}${contentLabel.slice(1)} ready to attach.`, "success");
    renderMediaPreview();
  }

  function setMediaStatus(message, tone) {
    el.mediaStatus.textContent = message;
    el.mediaStatus.className = `field-status${tone ? ` ${tone}` : ""}`;
    el.clearMedia.hidden = !el.mediaUrl.value;
  }

  function renderMediaPreview() {
    if (!state.media) {
      el.mediaPreview.hidden = true;
      return;
    }
    el.mediaPreview.hidden = false;
    el.mediaPreview.classList.toggle("youtube-preview", state.media.provider === "youtube");
    el.mediaPreviewIcon.src = state.media.provider === "youtube" ? YOUTUBE_ICON_URL : "assets/spotify-logo.png";
    const text = el.mediaPreview.querySelector("span");
    text.querySelector("strong").textContent = state.media.title;
    const labels = state.media.provider === "youtube" ? YOUTUBE_TYPES : SPOTIFY_TYPES;
    const contentLabel = labels[state.media.type] || "media";
    text.querySelector("small").textContent = `${state.media.provider === "youtube" ? "YouTube" : "Spotify"} ${contentLabel} · ${state.media.creator}`;
  }

  function updateMediaProvider(provider) {
    state.mediaProvider = provider === "youtube" ? "youtube" : "spotify";
    clearMedia();
    const isYouTube = state.mediaProvider === "youtube";
    el.mediaProviderIcon.src = isYouTube ? YOUTUBE_ICON_URL : "assets/spotify-logo.png";
    el.mediaProviderLink.href = isYouTube ? "https://www.youtube.com/" : "https://open.spotify.com/";
    el.mediaProviderLink.setAttribute("aria-label", `Open ${isYouTube ? "YouTube" : "Spotify"}`);
    el.mediaUrl.placeholder = isYouTube
      ? "Paste a video, Short, live, or playlist link"
      : "Paste a song, album, or playlist link";
  }

  function clearMedia() {
    state.mediaRequest += 1;
    state.media = null;
    el.mediaUrl.value = "";
    el.clearMedia.hidden = true;
    setMediaStatus("", "");
    renderMediaPreview();
  }

  function updateComposer() {
    const count = el.message.value.length;
    el.characterCount.textContent = `${count} / 500`;
    el.characterCount.classList.toggle("near-limit", count >= 450);
    const identity = el.form.elements.identity.value;
    const named = identity === "named";
    el.nameField.hidden = !named;
    el.displayName.required = named;
    const name = el.displayName.value.trim();
    el.publishLabel.textContent = named
      ? (name.length > 18 ? "Post with Name" : `Post as ${name || "…"}`)
      : "Post Anonymously";
  }

  function moderationError(message) {
    if (/([!?*._\-])\1{14,}/.test(message) || /(.)\1{19,}/i.test(message)) return "Please remove excessive repeated characters.";
    if ((message.match(/https?:\/\//gi) || []).length > 2) return "Please limit your message to two links.";
    if (/<\/?[a-z][\s\S]*>/i.test(message)) return "HTML is not allowed in messages.";
    return "";
  }

  function rateLimitError() {
    const now = Date.now();
    const history = readJson(STORAGE.submissions, []).filter((stamp) => now - stamp < 24 * 60 * 60 * 1000);
    if (history.filter((stamp) => now - stamp < 10 * 60 * 1000).length >= 3) return "You’ve shared three messages recently. Please wait a few minutes before posting again.";
    if (history.length >= 10) return "You’ve reached today’s posting limit. Please come back tomorrow.";
    return "";
  }

  async function submitPost(event) {
    event.preventDefault();
    el.formError.textContent = "";
    const message = el.message.value.trim();
    const type = el.form.elements.type.value;
    const identity = el.form.elements.identity.value;
    const name = el.displayName.value.trim();
    let error = "";
    if (message.length < 3) error = "Please write at least 3 characters.";
    else if (message.length > 500) error = "Please keep your message to 500 characters.";
    else if (identity === "named" && name.length < 2) error = "Please enter a name or switch to Anonymous.";
    else if (identity === "named" && name.length > 40) error = "Please keep your name to 40 characters.";
    else if (el.mediaUrl.value.trim() && !state.media) error = `Please attach a valid ${state.mediaProvider === "youtube" ? "YouTube" : "Spotify"} link—or remove it.`;
    else error = moderationError(message) || (state.backendConfigured ? "" : rateLimitError());
    if (!error && state.backendConfigured && !state.backendReady) {
      error = "The shared Dream Board is still connecting. Please try again shortly.";
    }
    if (error) {
      el.formError.textContent = error;
      return;
    }

    el.publishButton.disabled = true;
    el.publishLabel.textContent = "Posting…";
    const isAnonymous = identity !== "named";
    if (state.backendConfigured) {
      const { error: databaseError } = await database.rpc("create_dream_board_post_v2", {
        p_message: message,
        p_type: type,
        p_is_anonymous: isAnonymous,
        p_display_name: isAnonymous ? null : name,
        p_media_provider: state.media?.provider || null,
        p_media_item_id: state.media?.id || null,
        p_media_content_type: state.media?.type || null,
        p_media_title: state.media?.title || null,
        p_media_creator_name: state.media?.creator || null,
        p_media_thumbnail_url: state.media?.thumbnailUrl || null
      });
      if (databaseError) {
        el.publishButton.disabled = false;
        updateComposer();
        el.formError.textContent = friendlyBackendError(databaseError, "We couldn’t publish your message. Please try again.");
        return;
      }
      try {
        await refreshDatabasePosts();
      } catch {
        showToast("Your message was published, but the board could not refresh yet.");
      }
    } else {
      await new Promise((resolve) => window.setTimeout(resolve, 350));
      const newPost = {
        id: randomId(),
        message,
        type,
        displayName: isAnonymous ? "Anonymous" : name,
        isAnonymous,
        reactionCount: 0,
        commentCount: 0,
        createdAt: new Date().toISOString(),
        spotify: state.media?.provider === "spotify" ? { ...state.media } : null,
        youtube: state.media?.provider === "youtube" ? { ...state.media } : null
      };
      state.posts.unshift(newPost);
      writeJson(STORAGE.posts, state.posts);
      const history = readJson(STORAGE.submissions, []);
      writeJson(STORAGE.submissions, [...history, Date.now()]);
    }

    el.form.reset();
    updateMediaProvider("spotify");
    updateComposer();
    el.publishButton.disabled = false;
    state.filter = "all";
    state.sort = "latest";
    state.period = "all";
    state.search = "";
    el.searchInput.value = "";
    renderBoard();
    showToast("Your message has been added to the Dream Board ✨");
    el.board.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  }

  function clearAllFilters() {
    state.filter = "all";
    state.sort = "latest";
    state.period = "all";
    state.search = "";
    state.randomOrder.clear();
    el.searchInput.value = "";
    renderBoard();
  }

  function wireEvents() {
    document.querySelectorAll("[data-theme-value]").forEach((button) => {
      button.addEventListener("click", () => setTheme(button.dataset.themeValue));
    });
    el.message.addEventListener("input", updateComposer);
    el.composerToggle.addEventListener("click", () => {
      setComposerExpanded(el.composerFields.hidden);
    });
    el.emojiButton.addEventListener("click", () => setEmojiPicker(el.emojiPicker.hidden));
    el.emojiPicker.addEventListener("click", (event) => {
      const button = event.target.closest("[data-emoji]");
      if (!button) return;
      insertEmoji(button.dataset.emoji);
      setEmojiPicker(false);
    });
    el.displayName.addEventListener("input", updateComposer);
    el.form.querySelectorAll('input[name="identity"]').forEach((radio) => radio.addEventListener("change", updateComposer));
    el.mediaUrl.addEventListener("input", debounce(() => resolveMediaInput(el.mediaUrl.value), 450));
    el.clearMedia.addEventListener("click", clearMedia);
    el.removeMedia.addEventListener("click", clearMedia);
    el.form.querySelectorAll('input[name="mediaProvider"]').forEach((radio) => {
      radio.addEventListener("change", () => updateMediaProvider(radio.value));
    });
    el.form.addEventListener("submit", submitPost);

    el.categoryFilters.addEventListener("click", (event) => {
      const button = event.target.closest("[data-filter]");
      if (!button) return;
      state.filter = button.dataset.filter;
      renderBoard();
    });
    el.sortControl.addEventListener("click", (event) => {
      const button = event.target.closest("[data-sort]");
      if (!button) return;
      if (button.dataset.sort === "random") state.randomOrder.clear();
      state.sort = button.dataset.sort;
      renderBoard();
    });
    el.timeFilter.addEventListener("change", () => {
      state.period = el.timeFilter.value;
      renderBoard();
    });
    el.searchInput.addEventListener("input", debounce(() => {
      state.search = el.searchInput.value.trim();
      renderBoard();
    }, 300));
    el.clearFilters.addEventListener("click", clearAllFilters);

    el.reportForm.addEventListener("submit", async (event) => {
      if (event.submitter?.value !== "submit") return;
      event.preventDefault();
      if (!el.reportReason.value) {
        el.reportReason.focus();
        return;
      }
      if (state.backendConfigured) {
        if (!state.backendReady) {
          showToast("The shared Dream Board is still connecting. Please try again shortly.");
          return;
        }
        const { data, error } = await database.rpc("report_dream_board_post", {
          p_post_id: state.reportPostId,
          p_reason: el.reportReason.value
        });
        if (error) {
          showToast("We couldn’t save that report. Please try again.");
          return;
        }
        if (!data) {
          el.reportDialog.close();
          showToast("You have already reported this post.");
          return;
        }
      } else {
        const reports = readJson(STORAGE.reports, []);
        reports.push({ id: randomId(), postId: state.reportPostId, reason: el.reportReason.value, createdAt: new Date().toISOString(), status: "pending" });
        writeJson(STORAGE.reports, reports);
      }
      el.reportDialog.close();
      showToast("Thank you. Your report has been recorded for review.");
    });

    document.addEventListener("click", (event) => {
      if (!event.target.closest(".emoji-control")) setEmojiPicker(false);
      if (!event.target.closest(".menu-wrap")) {
        document.querySelectorAll(".card-menu").forEach((menu) => { menu.hidden = true; });
        document.querySelectorAll(".menu-button").forEach((button) => button.setAttribute("aria-expanded", "false"));
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !el.emojiPicker.hidden) {
        setEmojiPicker(false);
        el.emojiButton.focus();
      }
    });
  }

  async function init() {
    initTheme();
    renderComposerTypes();
    renderEmojiPicker();
    el.searchInput.value = state.search;
    el.timeFilter.value = state.period;
    wireEvents();
    updateMediaProvider("spotify");
    if (window.YT?.Player) youtubeIframeApiReady = true;
    updateComposer();
    renderBoard();
    await initBackend();
  }

  init();
})();

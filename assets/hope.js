(() => {
  "use strict";

  const STORAGE = {
    posts: "vitzz86-dream-board-posts-v1",
    loved: "vitzz86-dream-board-loved-v1",
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
    general: { label: "General", icon: "•••" }
  };

  const BACKEND_CONFIG = window.DREAM_BOARD_CONFIG || {};
  const backendConfigured = Boolean(
    /^https:\/\/[a-z0-9-]+\.supabase\.co$/i.test(BACKEND_CONFIG.supabaseUrl || "") &&
    /^sb_publishable_|^eyJ/i.test(BACKEND_CONFIG.supabasePublishableKey || "")
  );
  let database = null;

  const SEEDS = [
    {
      id: "seed-hope",
      message: "I hope one day everyone feels safe, loved, and free to be themselves. 🌈",
      type: "hope",
      displayName: "Anonymous",
      isAnonymous: true,
      reactionCount: 42,
      age: 2 * 60 * 60 * 1000
    },
    {
      id: "seed-motivation-music",
      message: "Songs that keep me going when nothing else does. 💚",
      type: "motivation",
      displayName: "Anonymous",
      isAnonymous: true,
      reactionCount: 56,
      age: 5 * 60 * 60 * 1000,
      spotify: {
        id: "37i9dQZF1DXcBWIGoYBM5M",
        canonicalUrl: "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
        embedUrl: "https://open.spotify.com/embed/playlist/37i9dQZF1DXcBWIGoYBM5M",
        title: "Keep Going 🌱",
        creator: "A playlist for hard days"
      }
    },
    {
      id: "seed-feedback",
      message: "Love the vibe of this site! Super clean and thoughtful design. Keep building! 🚀",
      type: "feedback",
      displayName: "Anonymous",
      isAnonymous: true,
      reactionCount: 29,
      age: 8 * 60 * 60 * 1000
    },
    {
      id: "seed-dream-music",
      message: "A playlist for when I imagine my future self. ✨",
      type: "dream",
      displayName: "Anonymous",
      isAnonymous: true,
      reactionCount: 73,
      age: 10 * 60 * 60 * 1000,
      spotify: {
        id: "37i9dQZF1DX4dyzvuaRJ0n",
        canonicalUrl: "https://open.spotify.com/playlist/37i9dQZF1DX4dyzvuaRJ0n",
        embedUrl: "https://open.spotify.com/embed/playlist/37i9dQZF1DX4dyzvuaRJ0n",
        title: "future me",
        creator: "vision board playlist"
      }
    },
    {
      id: "seed-gratitude",
      message: "Grateful for the people who stay, grow, and heal with me. 🌱",
      type: "gratitude",
      displayName: "Anonymous",
      isAnonymous: true,
      reactionCount: 34,
      age: 12 * 60 * 60 * 1000
    },
    {
      id: "seed-general",
      message: "Small steps every day. Big changes over time. ☀️",
      type: "general",
      displayName: "Anonymous",
      isAnonymous: true,
      reactionCount: 28,
      age: 13 * 60 * 60 * 1000
    },
    {
      id: "seed-advice",
      message: "Don’t compare your chapter 1 to someone else’s chapter 20. 🌟",
      type: "advice",
      displayName: "Anonymous",
      isAnonymous: true,
      reactionCount: 47,
      age: 14 * 60 * 60 * 1000
    },
    {
      id: "seed-dream",
      message: "I dream of traveling the world and collecting stories. ✈️🌍",
      type: "dream",
      displayName: "Anonymous",
      isAnonymous: true,
      reactionCount: 61,
      age: 16 * 60 * 60 * 1000
    },
    {
      id: "seed-motivation-two",
      message: "Focus on progress, not perfection. You’ve got this. 💪",
      type: "motivation",
      displayName: "Vito",
      isAnonymous: false,
      reactionCount: 38,
      age: 18 * 60 * 60 * 1000,
      spotify: {
        id: "37i9dQZF1DWZq91oLsHZvy",
        canonicalUrl: "https://open.spotify.com/playlist/37i9dQZF1DWZq91oLsHZvy",
        embedUrl: "https://open.spotify.com/embed/playlist/37i9dQZF1DWZq91oLsHZvy",
        title: "Progress Over Perfection",
        creator: "Elevate Mindset"
      }
    },
    {
      id: "seed-gratitude-two",
      message: "Thankful for quiet mornings, good coffee, and a clear mind. ☕✨",
      type: "gratitude",
      displayName: "Anonymous",
      isAnonymous: true,
      reactionCount: 31,
      age: 19 * 60 * 60 * 1000
    }
  ];

  const el = {
    html: document.documentElement,
    form: document.querySelector("#postForm"),
    message: document.querySelector("#message"),
    characterCount: document.querySelector("#characterCount"),
    composerTypes: document.querySelector("#composerTypes"),
    displayName: document.querySelector("#displayName"),
    nameField: document.querySelector("#nameField"),
    spotifyUrl: document.querySelector("#spotifyUrl"),
    spotifyStatus: document.querySelector("#spotifyStatus"),
    spotifyPreview: document.querySelector("#spotifyPreview"),
    clearSpotify: document.querySelector("#clearSpotify"),
    removeSpotify: document.querySelector("#removeSpotify"),
    publishButton: document.querySelector("#publishButton"),
    publishLabel: document.querySelector("#publishLabel"),
    formError: document.querySelector("#formError"),
    categoryFilters: document.querySelector("#categoryFilters"),
    searchInput: document.querySelector("#searchInput"),
    sortControl: document.querySelector("#sortControl"),
    timeFilter: document.querySelector("#timeFilter"),
    board: document.querySelector("#board"),
    emptyState: document.querySelector("#emptyState"),
    clearFilters: document.querySelector("#clearFilters"),
    messageCount: document.querySelector("#messageCount"),
    playlistCount: document.querySelector("#playlistCount"),
    reportDialog: document.querySelector("#reportDialog"),
    reportForm: document.querySelector("#reportForm"),
    reportReason: document.querySelector("#reportReason"),
    toast: document.querySelector("#toast")
  };

  const params = new URLSearchParams(window.location.search);
  const initialFilter = params.get("type") || (params.get("music") === "true" ? "music" : "all");
  const state = {
    posts: loadPosts(),
    loved: new Set(readJson(STORAGE.loved, [])),
    backendConfigured,
    backendReady: false,
    backendError: "",
    filter: initialFilter === "music" || TYPES[initialFilter] ? initialFilter : "all",
    sort: ["latest", "loved", "random", "oldest"].includes(params.get("sort")) ? params.get("sort") : "latest",
    period: ["all", "today", "week", "month", "year"].includes(params.get("period")) ? params.get("period") : "all",
    search: (params.get("search") || "").trim(),
    spotify: null,
    reportPostId: null,
    randomOrder: new Map(),
    spotifyRequest: 0
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
    if (Array.isArray(stored) && stored.length) return stored;
    const now = Date.now();
    const seeded = SEEDS.map(({ age, ...post }) => ({ ...post, createdAt: new Date(now - age).toISOString() }));
    writeJson(STORAGE.posts, seeded);
    return seeded;
  }

  function mapDatabasePost(row) {
    const spotify = row.spotify_playlist_id ? {
      id: row.spotify_playlist_id,
      canonicalUrl: row.spotify_canonical_url,
      embedUrl: row.spotify_embed_url,
      title: row.spotify_title || "Spotify playlist",
      creator: row.spotify_creator_name || "Spotify",
      thumbnailUrl: row.spotify_thumbnail_url || null
    } : null;
    return {
      id: row.id,
      message: row.message,
      type: row.type,
      displayName: row.is_anonymous ? "Anonymous" : (row.display_name || "Anonymous"),
      isAnonymous: row.is_anonymous,
      reactionCount: Number(row.reaction_count || 0),
      createdAt: row.created_at,
      spotify,
      lovedByMe: Boolean(row.loved_by_me)
    };
  }

  async function refreshDatabasePosts() {
    const { data, error } = await database.rpc("get_dream_board_posts", { p_limit: 100 });
    if (error) throw error;
    const rows = Array.isArray(data) ? data : [];
    state.posts = rows.map(mapDatabasePost);
    state.loved = new Set(rows.filter((row) => row.loved_by_me).map((row) => row.id));
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
      state.backendError = error?.message || "Dream Board connection failed";
      showToast("The shared Dream Board is temporarily unavailable.");
    }
  }

  function friendlyBackendError(error, fallback) {
    const message = String(error?.message || "").toLowerCase();
    if (message.includes("wait before posting")) return "You’ve shared three messages recently. Please wait a few minutes before posting again.";
    if (message.includes("daily posting limit")) return "You’ve reached today’s posting limit. Please come back tomorrow.";
    if (message.includes("already submitted")) return "This message was already submitted.";
    if (message.includes("excessive repeated")) return "Please remove excessive repeated characters.";
    if (message.includes("anonymous sign-ins are disabled")) return "Anonymous posting is not enabled yet.";
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
      span.textContent = `${info.icon} ${info.label}`;
      label.append(input, span);
      el.composerTypes.append(label);
    });
  }

  function renderFilters() {
    el.categoryFilters.replaceChildren();
    const filters = [
      ["all", "▦", "All"],
      ...Object.entries(TYPES).map(([key, info]) => [key, info.icon, info.label]),
      ["music", "♫", "With Music"]
    ];
    filters.forEach(([key, icon, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `filter-chip${state.filter === key ? " active" : ""}`;
      button.dataset.filter = key;
      button.setAttribute("aria-pressed", String(state.filter === key));
      button.textContent = `${icon} ${label}`;
      el.categoryFilters.append(button);
    });
  }

  function updateUrl() {
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
      if (state.filter === "music" && !post.spotify) return false;
      if (state.filter !== "all" && state.filter !== "music" && post.type !== state.filter) return false;
      if (!isWithinPeriod(post.createdAt, state.period)) return false;
      if (!needle) return true;
      return [post.message, post.displayName, post.spotify?.title, post.spotify?.creator]
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
    wrapper.className = "playlist-card";
    const row = document.createElement("div");
    row.className = "playlist-preview-row";
    const art = document.createElement("div");
    art.className = "playlist-art";
    if (post.spotify.thumbnailUrl) {
      const image = document.createElement("img");
      image.src = post.spotify.thumbnailUrl;
      image.alt = "";
      image.loading = "lazy";
      art.append(image);
    }
    const play = document.createElement("button");
    play.type = "button";
    play.textContent = "▶";
    play.dataset.action = "play";
    play.setAttribute("aria-label", `Play Spotify playlist: ${post.spotify.title}`);
    art.append(play);
    const meta = document.createElement("span");
    meta.className = "playlist-meta";
    meta.append(makeText("strong", "", post.spotify.title), makeText("small", "", `by ${post.spotify.creator || "Spotify"}`));
    const mark = document.createElement("img");
    mark.className = "spotify-mark";
    mark.src = "assets/spotify-logo.png";
    mark.alt = "Spotify";
    mark.width = 21;
    mark.height = 21;
    row.append(art, meta, mark);

    const playerShell = document.createElement("div");
    playerShell.className = "player-shell";
    playerShell.hidden = true;
    const actions = document.createElement("div");
    actions.className = "player-actions";
    const collapse = makeText("button", "", "Collapse player");
    collapse.type = "button";
    collapse.dataset.action = "collapse";
    const open = makeText("a", "", "Open in Spotify ↗");
    open.href = post.spotify.canonicalUrl;
    open.target = "_blank";
    open.rel = "noopener";
    actions.append(collapse, open);
    playerShell.append(actions);
    wrapper.append(row, playerShell);

    play.addEventListener("click", () => {
      document.querySelectorAll(".player-shell:not([hidden])").forEach((active) => {
        if (active !== playerShell) {
          active.hidden = true;
          active.querySelector("iframe")?.remove();
          const activeCard = active.closest(".playlist-card");
          const activePlay = activeCard?.querySelector('[data-action="play"]');
          if (activePlay) activePlay.hidden = false;
        }
      });
      if (!playerShell.querySelector("iframe")) {
        const iframe = document.createElement("iframe");
        iframe.src = post.spotify.embedUrl;
        iframe.loading = "lazy";
        iframe.allowFullscreen = true;
        iframe.allow = "autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture";
        iframe.title = `Spotify playlist: ${post.spotify.title}`;
        playerShell.prepend(iframe);
      }
      playerShell.hidden = false;
      play.hidden = true;
    });

    collapse.addEventListener("click", () => {
      playerShell.hidden = true;
      playerShell.querySelector("iframe")?.remove();
      play.hidden = false;
    });

    return wrapper;
  }

  function makePostCard(post, index) {
    const card = document.createElement("article");
    card.className = "post-card";
    card.dataset.type = post.type;
    card.dataset.postId = post.id;
    card.style.animationDelay = `${Math.min(index * 35, 280)}ms`;

    const head = document.createElement("div");
    head.className = "card-head";
    const type = TYPES[post.type] || TYPES.general;
    head.append(makeText("span", "type-pill", `${type.label} ${type.icon}`));
    const menuWrap = document.createElement("div");
    menuWrap.className = "menu-wrap";
    const menuButton = makeText("button", "menu-button", "•••");
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

    const meta = document.createElement("div");
    meta.className = "card-meta";
    const author = document.createElement("span");
    author.className = "author";
    author.append(makeText("span", "author-avatar", post.isAnonymous ? "👤" : "✦"), makeText("span", "author-name", post.displayName || "Anonymous"));
    meta.append(author, makeText("time", "", relativeTime(post.createdAt)));
    const footer = document.createElement("div");
    footer.className = "card-footer";
    const love = document.createElement("button");
    love.type = "button";
    love.className = `love-button${state.loved.has(post.id) ? " loved" : ""}`;
    love.setAttribute("aria-label", state.loved.has(post.id) ? "Remove love reaction" : "Love this post");
    const heart = makeText("span", "heart-glyph", state.loved.has(post.id) ? "♥" : "♡");
    heart.setAttribute("aria-hidden", "true");
    const count = makeText("span", "", String(post.reactionCount || 0));
    love.append(heart, count);
    footer.append(love);
    card.append(meta, footer);

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
    return card;
  }

  function renderBoard() {
    const posts = getVisiblePosts();
    el.board.replaceChildren(...posts.map(makePostCard));
    el.emptyState.hidden = posts.length > 0;
    if (!posts.length) {
      el.emptyState.querySelector("p").textContent = state.search
        ? "No posts match your search."
        : "No messages match these filters.";
    }
    el.messageCount.textContent = state.posts.length.toLocaleString();
    el.playlistCount.textContent = state.posts.filter((post) => post.spotify).length.toLocaleString();
    renderFilters();
    el.sortControl.querySelectorAll("button").forEach((button) => {
      const active = button.dataset.sort === state.sort;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    el.timeFilter.value = state.period;
    updateUrl();
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
    const uri = input.match(/^spotify:playlist:([A-Za-z0-9]{10,30})$/i);
    if (uri) return { id: uri[1], isShort: false };
    let url;
    try { url = new URL(input); } catch { return null; }
    const hostname = url.hostname.toLowerCase();
    if (hostname === "spotify.link" || hostname.endsWith(".spotify.link")) return { shortUrl: url.toString(), isShort: true };
    if (hostname !== "open.spotify.com") return null;
    const match = url.pathname.match(/^\/playlist\/([A-Za-z0-9]{10,30})\/?$/i);
    return match ? { id: match[1], isShort: false } : null;
  }

  async function resolveSpotifyInput(rawValue) {
    const request = ++state.spotifyRequest;
    const parsed = parseSpotify(rawValue);
    state.spotify = null;
    renderSpotifyPreview();
    if (!rawValue.trim()) {
      setSpotifyStatus("", "");
      return;
    }
    if (!parsed) {
      const looksSpotify = /spotify/i.test(rawValue);
      setSpotifyStatus(looksSpotify ? "This link is not a Spotify playlist. Please share a playlist link." : "Please enter a valid Spotify playlist link.", "error");
      return;
    }
    setSpotifyStatus("Validating playlist…", "");
    let playlistId = parsed.id;
    if (parsed.isShort) {
      try {
        const response = await fetch(parsed.shortUrl, { method: "GET", redirect: "follow" });
        const resolved = parseSpotify(response.url);
        if (!resolved?.id) throw new Error("Not a playlist");
        playlistId = resolved.id;
      } catch {
        if (request === state.spotifyRequest) setSpotifyStatus("This short link could not be resolved here. Paste the full open.spotify.com playlist link instead.", "error");
        return;
      }
    }
    if (request !== state.spotifyRequest) return;
    const canonicalUrl = `https://open.spotify.com/playlist/${playlistId}`;
    const spotify = {
      id: playlistId,
      canonicalUrl,
      embedUrl: `https://open.spotify.com/embed/playlist/${playlistId}`,
      title: "Spotify playlist",
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
    if (request !== state.spotifyRequest) return;
    state.spotify = spotify;
    setSpotifyStatus("Playlist ready to attach.", "success");
    renderSpotifyPreview();
  }

  function setSpotifyStatus(message, tone) {
    el.spotifyStatus.textContent = message;
    el.spotifyStatus.className = `field-status${tone ? ` ${tone}` : ""}`;
    el.clearSpotify.hidden = !el.spotifyUrl.value;
  }

  function renderSpotifyPreview() {
    if (!state.spotify) {
      el.spotifyPreview.hidden = true;
      return;
    }
    el.spotifyPreview.hidden = false;
    const text = el.spotifyPreview.querySelector("span");
    text.querySelector("strong").textContent = state.spotify.title;
    text.querySelector("small").textContent = state.spotify.creator;
  }

  function clearSpotify() {
    state.spotifyRequest += 1;
    state.spotify = null;
    el.spotifyUrl.value = "";
    el.clearSpotify.hidden = true;
    setSpotifyStatus("", "");
    renderSpotifyPreview();
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
    else if (el.spotifyUrl.value.trim() && !state.spotify) error = "Please attach a valid Spotify playlist or remove the link.";
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
      const { error: databaseError } = await database.rpc("create_dream_board_post", {
        p_message: message,
        p_type: type,
        p_is_anonymous: isAnonymous,
        p_display_name: isAnonymous ? null : name,
        p_spotify_playlist_id: state.spotify?.id || null,
        p_spotify_title: state.spotify?.title || null,
        p_spotify_creator_name: state.spotify?.creator || null,
        p_spotify_thumbnail_url: state.spotify?.thumbnailUrl || null
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
        createdAt: new Date().toISOString(),
        spotify: state.spotify ? { ...state.spotify } : null
      };
      state.posts.unshift(newPost);
      writeJson(STORAGE.posts, state.posts);
      const history = readJson(STORAGE.submissions, []);
      writeJson(STORAGE.submissions, [...history, Date.now()]);
    }

    el.form.reset();
    clearSpotify();
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
    el.displayName.addEventListener("input", updateComposer);
    el.form.querySelectorAll('input[name="identity"]').forEach((radio) => radio.addEventListener("change", updateComposer));
    el.spotifyUrl.addEventListener("input", debounce(() => resolveSpotifyInput(el.spotifyUrl.value), 450));
    el.clearSpotify.addEventListener("click", clearSpotify);
    el.removeSpotify.addEventListener("click", clearSpotify);
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
      if (!event.target.closest(".menu-wrap")) {
        document.querySelectorAll(".card-menu").forEach((menu) => { menu.hidden = true; });
        document.querySelectorAll(".menu-button").forEach((button) => button.setAttribute("aria-expanded", "false"));
      }
    });
  }

  async function init() {
    initTheme();
    renderComposerTypes();
    el.searchInput.value = state.search;
    el.timeFilter.value = state.period;
    wireEvents();
    updateComposer();
    renderBoard();
    await initBackend();
  }

  init();
})();

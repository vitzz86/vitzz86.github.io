const DATA_ROOT = "/ai-intelligence/data";
const WORLD_GEOJSON = "https://cdn.jsdelivr.net/gh/holtzy/D3-graph-gallery@master/DATA/world.geojson";
const MAP_STYLE = "https://tiles.openfreemap.org/styles/positron";

const layerMeta = {
  6: { name: "Applications & Autonomous Agents", short: "Applications", color: "#d89200", definition: "Products and agents that apply AI to consumer, enterprise and industry workflows." },
  5: { name: "Software & Platform Layer", short: "Software", color: "#168a7a", definition: "Data platforms, developer tools, orchestration, observability, safety and governance." },
  4: { name: "AI Models", short: "Models", color: "#2f9b61", definition: "Foundation and specialised models that generate, reason, perceive or predict." },
  3: { name: "Data Centres & Cloud Compute", short: "Compute", color: "#2d82bd", definition: "Cloud services, GPU capacity, servers, networking, storage and data-centre operators." },
  2: { name: "Semiconductor Layer", short: "Semiconductors", color: "#175f9f", definition: "Chip design, fabrication, equipment, memory, materials, packaging and testing." },
  1: { name: "Electricity, Power & Cooling", short: "Energy", color: "#0b2a5d", definition: "Power generation, grids, backup systems and cooling that keep AI infrastructure running." },
};

// Country centres are used only when a verified city-level coordinate is unavailable.
// The interface labels these points as country-level placement rather than exact offices.
const coordinates = {
  Australia: [133.7751, -25.2744], Austria: [14.5501, 47.5162], Canada: [-106.3468, 56.1304], China: [104.1954, 35.8617],
  "Czech Republic": [15.473, 49.8175], Finland: [25.7482, 61.9241], France: [2.2137, 46.2276], Germany: [10.4515, 51.1657],
  "Hong Kong": [114.1694, 22.3193], India: [78.9629, 20.5937], Indonesia: [118.0149, -2.5489],
  Ireland: [-7.6921, 53.1424], Israel: [34.8516, 31.0461], Japan: [138.2529, 36.2048], Malaysia: [101.9758, 4.2105],
  Netherlands: [5.2913, 52.1326], "New Zealand": [174.886, -40.9006], "North America": [-100, 45], Philippines: [121.774, 12.8797],
  Singapore: [103.8198, 1.3521], "South Korea": [127.7669, 35.9078], Spain: [-3.7492, 40.4637], Sweden: [18.6435, 60.1282],
  Switzerland: [8.2275, 46.8182], Taiwan: [120.9605, 23.6978], Thailand: [100.9925, 15.87], "United Kingdom": [-3.436, 55.3781],
  "United States": [-95.7129, 37.0902], Vietnam: [108.2772, 14.0583],
};

const ecosystemHubs = {
  Indonesia: { name: "Jakarta ecosystem hub, Indonesia", coordinates: [106.8456, -6.2088], radius: 0.42 },
  Singapore: { name: "Singapore", coordinates: [103.8198, 1.3521], radius: 0.25 },
  Malaysia: { name: "Kuala Lumpur ecosystem hub, Malaysia", coordinates: [101.6869, 3.139], radius: 0.38 },
  Thailand: { name: "Bangkok ecosystem hub, Thailand", coordinates: [100.5018, 13.7563], radius: 0.38 },
  Philippines: { name: "Metro Manila ecosystem hub, Philippines", coordinates: [120.9842, 14.5995], radius: 0.42 },
};

const aliases = {
  USA: "United States",
  "United States of America": "United States",
  England: "United Kingdom",
  UK: "United Kingdom",
  "U.K.": "United Kingdom",
  "Great Britain": "United Kingdom",
  "The United Kingdom": "United Kingdom",
  Czechia: "Czech Republic",
  "Republic of Korea": "South Korea",
  Korea: "South Korea",
  "Viet Nam": "Vietnam",
};
const state = { records: [], densityRecords: [], visible: [], world: [], region: "all", layer: "all", country: "all", ownership: "all", vertical: "all", search: "", selectedId: null, profileTab: "company", map: null, mapReady: false, hoverPopup: null };
const databaseState = { search: "", region: "all", layer: "all", country: "all", ownership: "all", vertical: "all" };

const el = {
  stage: document.querySelector("#companyMap"), loading: document.querySelector("#mapLoading"), search: document.querySelector("#mapSearch"),
  filtersToggle: document.querySelector("#mapFiltersToggle"), controls: document.querySelector("#mapControls"),
  region: document.querySelector("#mapRegion"), layer: document.querySelector("#mapLayer"), country: document.querySelector("#mapCountry"), ownership: document.querySelector("#mapOwnership"), vertical: document.querySelector("#mapVertical"), count: document.querySelector("#mapVisibleCount"),
  countryCount: document.querySelector("#mapCountryCount"), topHub: document.querySelector("#mapTopHub"), reset: document.querySelector("#mapReset"),
  fullscreen: document.querySelector("#mapFullscreen"), resetView: document.querySelector("#mapResetView"), workspace: document.querySelector("#world-map"), context: document.querySelector("#mapContext"),
  resultTray: document.querySelector("#mapResultTray"), tray: document.querySelector("#mapCompanyTray"), trayCount: document.querySelector("#mapTrayCount"), trayLabel: document.querySelector("#mapTrayLabel"),
  database: document.querySelector("#mapDatabase"), databaseOpen: document.querySelector("#mapDatabaseOpen"), databaseClose: document.querySelector("#mapDatabaseClose"),
  databaseSearch: document.querySelector("#databaseSearch"), databaseRegion: document.querySelector("#databaseRegion"), databaseLayer: document.querySelector("#databaseLayer"), databaseCountry: document.querySelector("#databaseCountry"), databaseOwnership: document.querySelector("#databaseOwnership"), databaseVertical: document.querySelector("#databaseVertical"),
  databaseCount: document.querySelector("#databaseCount"), databaseRows: document.querySelector("#databaseRows"), databaseRange: document.querySelector("#databaseRange"), databaseReset: document.querySelector("#databaseReset"),
  onboarding: document.querySelector("#mapOnboarding"), opening: document.querySelector("#mapOpening"),
  hubInsights: document.querySelector("#mapHubInsights"), layerInsights: document.querySelector("#mapLayerInsights"), verticalInsights: document.querySelector("#mapVerticalInsights"),
};

function escapeHTML(value = "") { return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;"); }
function initials(name) { return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase(); }
function domain(source) { try { return new URL(source).hostname.replace(/^www\./, ""); } catch (_) { return ""; } }
function hasURL(value) { return /^https?:\/\//i.test(String(value || "")); }
function displayValue(value, fallback = "No verified record") { return value === null || value === undefined || value === "" ? fallback : String(value); }
function externalLink(url, label, className = "") { return hasURL(url) ? `<a class="${className}" href="${escapeHTML(url)}" target="_blank" rel="noopener">${escapeHTML(label)} ↗</a>` : ""; }
function formatUsd(value) { const amount = Number(value); if (!Number.isFinite(amount) || amount <= 0) return "No disclosed amount"; return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }).format(amount); }
function logoFor(record) { const host = domain(record.website || record.profile?.website || record.source); return host ? `https://www.google.com/s2/favicons?domain=${encodeURIComponent(host)}&sz=128` : ""; }
function logoMarkup(record, className = "map-company-logo") { const url = logoFor(record); const letters = escapeHTML(initials(record.name)); return url ? `<span class="${className}"><img src="${escapeHTML(url)}" alt="" loading="lazy" decoding="async" data-map-logo /><span hidden>${letters}</span></span>` : `<span class="${className}"><span>${letters}</span></span>`; }
function attachLogoFallbacks(root = document) { root.querySelectorAll("img[data-map-logo]").forEach((image) => { if (image.dataset.bound) return; image.dataset.bound = "1"; image.addEventListener("error", () => { image.hidden = true; if (image.nextElementSibling) image.nextElementSibling.hidden = false; }, { once: true }); }); }
function meaningful(value) { return value !== null && value !== undefined && value !== "" && !/^(not |no |unknown|unavailable|research pending|not applicable)/i.test(String(value).trim()); }
function cleanLocationPart(value) {
  const part=String(value||"").trim();
  return !part||/country[- ]level|location only|hq_location|not (publicly )?disclosed|unknown/i.test(part)?"":part;
}
function formatHeadquarters(record) {
  const hq=record.profile?.headquarters||{};
  const country=cleanLocationPart(hq.country)||cleanLocationPart(record.country);
  const city=cleanLocationPart(hq.city);
  if(city&&country&&city.localeCompare(country,undefined,{sensitivity:"accent"})!==0) return `${city}, ${country}`;
  if(country) return country;
  if(city) return city;
  return cleanLocationPart(record.location)||"Location not verified";
}
function socialKind(url = "") { const host=domain(url); if(host.includes("linkedin")) return "linkedin"; if(host==="x.com"||host.includes("twitter")) return "x"; if(host.includes("instagram")) return "instagram"; if(host.includes("crunchbase")) return "crunchbase"; if(host.includes("yahoo")) return "market"; return "website"; }
function socialLabel(url = "", fallback = "Open link") { const kind=socialKind(url); return ({linkedin:"LinkedIn",x:"X",instagram:"Instagram",crunchbase:"Crunchbase",market:"Yahoo Finance",website:fallback})[kind]; }
function profileIcon(kind) {
  if(kind==="linkedin") return `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5.2 7.9H1.8V22h3.4V7.9ZM3.5 2A2 2 0 1 0 3.5 6a2 2 0 0 0 0-4ZM22 14c0-4.3-2.3-6.3-5.4-6.3-2.5 0-3.6 1.4-4.2 2.3V7.9H9V22h3.4v-7c0-1.8.4-3.6 2.7-3.6 2.3 0 2.3 2.1 2.3 3.7V22H22v-8Z"/></svg>`;
  if(kind==="x") return `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18.9 2H22l-6.8 7.8L23.2 22H17l-4.9-6.4L6.5 22H3.4l7.2-8.3L2.8 2h6.4l4.4 5.8L18.9 2Zm-1.1 17.9h1.7L8.3 4H6.5l11.3 15.9Z"/></svg>`;
  if(kind==="instagram") return `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 2h10a5 5 0 0 1 5 5v10a5 5 0 0 1-5 5H7a5 5 0 0 1-5-5V7a5 5 0 0 1 5-5Zm0 2a3 3 0 0 0-3 3v10a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3V7a3 3 0 0 0-3-3H7Zm10.5 1.5a1 1 0 1 1 0 2 1 1 0 0 1 0-2ZM12 7a5 5 0 1 1 0 10 5 5 0 0 1 0-10Zm0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"/></svg>`;
  if(kind==="crunchbase") return `<strong aria-hidden="true">cb</strong>`;
  if(kind==="market") return `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19h16v2H2V3h2v16Zm3-3-1.5-1.3 4.2-5 3.1 2.5 4.7-6 1.6 1.2-6 7.7-3.2-2.6L7 16Z"/></svg>`;
  return `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm6.9 6h-3.1a15.8 15.8 0 0 0-1.4-3.3A8.1 8.1 0 0 1 18.9 8ZM12 4c.8 1 1.5 2.3 1.8 4h-3.6c.3-1.7 1-3 1.8-4ZM9.6 4.7A15.8 15.8 0 0 0 8.2 8H5.1a8.1 8.1 0 0 1 4.5-3.3ZM4 12c0-.7.1-1.4.3-2h3.6a18 18 0 0 0 0 4H4.3A8 8 0 0 1 4 12Zm1.1 4h3.1c.3 1.3.8 2.4 1.4 3.3A8.1 8.1 0 0 1 5.1 16Zm6.9 4c-.8-1-1.5-2.3-1.8-4h3.6c-.3 1.7-1 3-1.8 4Zm2.2-6H9.8a15.8 15.8 0 0 1 0-4h4.4a15.8 15.8 0 0 1 0 4Zm.2 5.3c.6-.9 1.1-2 1.4-3.3h3.1a8.1 8.1 0 0 1-4.5 3.3ZM16.1 14a18 18 0 0 0 0-4h3.6a8.2 8.2 0 0 1 0 4h-3.6Z"/></svg>`;
}
function profileLink(url, fallbackLabel = "Official source") { if(!hasURL(url)) return ""; const kind=socialKind(url),label=socialLabel(url,fallbackLabel); return `<a class="map-profile-icon-link is-${kind}" href="${escapeHTML(url)}" target="_blank" rel="noopener" aria-label="${escapeHTML(label)}" title="${escapeHTML(label)}">${profileIcon(kind)}<span class="sr-only">${escapeHTML(label)}</span></a>`; }
function credibleDirectoryLink(url, record) {
  if (!hasURL(url)) return false;
  let slug=""; try { slug=new URL(url).pathname.split("/").filter(Boolean).pop()||""; } catch (_) { return false; }
  const clean=(value)=>String(value||"").toLowerCase().replace(/[^a-z0-9]/g,"");
  const slugClean=clean(slug), candidates=[record.name,record.companyId,record.id].map(clean).filter((value)=>value.length>=3);
  return candidates.some((value)=>slugClean.includes(value)||value.includes(slugClean));
}

function normaliseEntity(entity) {
  const layers = entity.layers.map(Number).filter(Boolean);
  return { id: `entity:${entity.id}`, companyId: entity.id, name: entity.name, country: entity.headquarters, location: entity.location || entity.headquarters, region: entity.region, organisationType: entity.organisationType || "Organisation", layers, primaryLayer: Number(entity.primaryLayer) || Math.max(...layers), verticals: [], offering: entity.offerings?.[0] || entity.roles?.[0] || entity.segments?.[0] || "AI value-chain capability", searchable: [...(entity.offerings || []), ...(entity.roles || []), ...(entity.segments || [])].join(" "), source: entity.sources?.[0] || "", logo: entity.logo || null, featured: Boolean(entity.globalMap || entity.apacMap), coordinates: Array.isArray(entity.coordinates) && entity.coordinates.length === 2 ? entity.coordinates.map(Number) : null };
}

function normaliseApplication(row, columns, verticalNames) {
  const raw = Object.fromEntries(columns.map((column, index) => [column, row[index]]));
  const verticals = String(raw.verticalIds || "").split("|").filter(Boolean).map((id) => verticalNames.get(id) || id);
  return { id: `application:${raw.id}`, companyId: raw.id, name: raw.name, country: raw.country, location: raw.location || raw.country, region: raw.region, organisationType: raw.organisationType || "Organisation", layers: [6], primaryLayer: 6, verticals, offering: raw.offering || "AI application and workflow capability", searchable: verticals.join(" "), source: raw.source || "", logo: null, featured: false, coordinates: null };
}

function enrichRecord(record, profile) {
  if (!profile) return record;
  const hq = profile.headquarters || {};
  const ai = profile.aiPosition || {};
  const profileLayers = [Number(ai.primaryLayer), ...(ai.secondaryLayers || []).map(Number)].filter(Boolean);
  record.profile = profile;
  record.companyId = profile.id || record.companyId;
  record.name = profile.name || record.name;
  record.country = hq.country || record.country;
  record.location = formatHeadquarters(record);
  record.region = hq.region || record.region;
  record.organisationType = profile.entityType || record.organisationType;
  record.ownershipStatus = profile.ownershipStatus || "Ownership not classified";
  record.lifecycleStatus = profile.lifecycleStatus || "Status not classified";
  record.layers = [...new Set([...record.layers, ...profileLayers])];
  record.primaryLayer = Number(ai.primaryLayer) || record.primaryLayer;
  record.verticals = [...new Set([...record.verticals, ai.primaryVertical, ...(ai.secondaryVerticals || [])].filter(Boolean))];
  record.offering = profile.description || record.offering;
  record.searchable = [record.searchable, ai.primaryCapability, ai.aiIntensity, ai.whyIncluded, record.ownershipStatus, record.lifecycleStatus].filter(Boolean).join(" ");
  record.source = profile.website || profile.verification?.companySource || record.source;
  record.website = profile.website || record.source;
  record.linkedin = profile.linkedin || "";
  if (!record.logo && profile.logo) record.logo = { url: profile.logo };
  if (hq.coordinatesVerified && [hq.longitude, hq.latitude].every((value) => Number.isFinite(Number(value)))) {
    record.coordinates = [Number(hq.longitude), Number(hq.latitude)];
    record.coordinatePrecision = "verified";
  }
  return record;
}

function mergeDirectories(entitiesData, applicationsData, verticalsData, profilesData, marketData = {}) {
  const verticalNames = new Map(verticalsData.verticals.map((vertical) => [vertical.id, vertical.name]));
  const profilesById = new Map((profilesData.companies || []).map((profile) => [String(profile.id || "").toLowerCase(), profile]));
  const profilesByName = new Map((profilesData.companies || []).map((profile) => [String(profile.name || "").trim().toLowerCase(), profile]));
  const identityAliases = new Map([["captions","mirage"],["indosat and goto","sahabat-ai"],["pure storage","everpure"]]);
  const records = new Map();
  entitiesData.entities.map(normaliseEntity).forEach((record) => records.set(record.name.trim().toLowerCase(), record));
  applicationsData.rows.map((row) => normaliseApplication(row, applicationsData.meta.columns, verticalNames)).forEach((record) => {
    const key = record.name.trim().toLowerCase();
    if (!records.has(key)) records.set(key, record);
    else { const current = records.get(key); current.verticals = [...new Set([...current.verticals, ...record.verticals])]; if (!current.source) current.source = record.source; }
  });
  const merged = [...records.values()].map((record) => { const key=record.name.trim().toLowerCase(); const enriched=enrichRecord(record, profilesById.get(String(record.companyId || "").toLowerCase()) || profilesByName.get(key) || profilesById.get(identityAliases.get(key))); enriched.marketSnapshot=(marketData.companies||{})[enriched.companyId]||null; return enriched; });
  return assignMapCoordinates(merged.sort((a, b) => a.name.localeCompare(b.name)));
}

function hashString(value) { let hash = 2166136261; for (const char of value) { hash ^= char.charCodeAt(0); hash = Math.imul(hash, 16777619); } return hash >>> 0; }
function assignMapCoordinates(records) {
  const groups = new Map();
  records.forEach((record) => { if (!groups.has(record.country)) groups.set(record.country, []); groups.get(record.country).push(record); });
  groups.forEach((group, country) => {
    const hub = ecosystemHubs[country];
    const centre = hub?.coordinates || coordinates[country];
    group.sort((a, b) => a.name.localeCompare(b.name)).forEach((record, index) => {
      if (record.coordinates?.every(Number.isFinite)) { record.mapCoordinates = record.coordinates; record.coordinatePrecision = "verified"; record.mapLocation = formatHeadquarters(record); return; }
      if (!centre) { record.mapCoordinates = null; record.coordinatePrecision = "unlocated"; record.mapLocation = "Not placed on map"; return; }
      const compact = ["Singapore", "Hong Kong"].includes(country);
      const radiusLimit = hub?.radius || (compact ? 0.34 : Math.min(3.2, 0.5 + Math.sqrt(group.length) * 0.18));
      const seed = hashString(record.id);
      const angle = (index * 137.508 + seed % 37) * Math.PI / 180;
      const radius = radiusLimit * Math.sqrt((index + 0.7) / Math.max(1, group.length));
      const longitudeScale = Math.max(0.35, Math.cos(centre[1] * Math.PI / 180));
      record.mapCoordinates = [centre[0] + Math.cos(angle) * radius / longitudeScale, centre[1] + Math.sin(angle) * radius * 0.62];
      record.coordinatePrecision = hub ? "hub" : "country";
      record.mapLocation = formatHeadquarters(record);
    });
  });
  return records;
}

function regionValueMatches(record, value) { if (value === "all") return true; if (value === "apac") return record.region === "APAC" || record.region === "Southeast Asia"; if (value === "sea") return record.region === "Southeast Asia"; return record.region === value; }
function ownershipValueMatches(record, value) { return value === "all" || record.profile?.market?.type === value; }
function searchMatches(record, query = state.search) { if (!query) return true; return [record.name, record.country, record.location, record.region, record.organisationType, record.offering, record.searchable, ...record.verticals].join(" ").toLowerCase().includes(query); }
function recordMatches(record, omit = "") {
  if (omit !== "region" && !regionValueMatches(record, state.region)) return false;
  if (omit !== "layer" && state.layer !== "all" && !record.layers.includes(Number(state.layer))) return false;
  if (omit !== "country" && state.country !== "all" && record.country !== state.country) return false;
  if (omit !== "ownership" && !ownershipValueMatches(record, state.ownership)) return false;
  if (omit !== "vertical" && state.vertical !== "all" && !record.verticals.includes(state.vertical)) return false;
  return searchMatches(record);
}
function facetRecords(omit = "") { return state.records.filter((record) => recordMatches(record, omit)); }
function countrySummary(records) { const counts = new Map(); records.forEach((record) => counts.set(record.country, (counts.get(record.country) || 0) + 1)); return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])); }
function verticalSummary(records) { const counts = new Map(); records.forEach((record) => record.verticals.forEach((vertical) => counts.set(vertical, (counts.get(vertical) || 0) + 1))); return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])); }
function featureCountry(feature) { const name = feature?.properties?.name || ""; return aliases[name] || name; }
function recordsGeoJSON(records) { return { type: "FeatureCollection", features: records.filter((record) => record.mapCoordinates).map((record) => ({ type: "Feature", id: hashString(record.id), properties: { id: record.id, name: record.name, country: record.country, layer: record.primaryLayer, offering: record.offering, precision: record.coordinatePrecision }, geometry: { type: "Point", coordinates: record.mapCoordinates } })) }; }
function countriesGeoJSON(records) {
  const counts = new Map(countrySummary(records));
  return { type: "FeatureCollection", features: state.world.map((feature, index) => { const country = featureCountry(feature); return { ...feature, id: index + 1, properties: { ...(feature.properties || {}), canonical: country, density: counts.get(country) || 0, selected: state.country === country } }; }) };
}

function updateMapSources() {
  if (!state.mapReady) return;
  state.map.getSource("ai-countries")?.setData(countriesGeoJSON(state.densityRecords));
  state.map.getSource("ai-organisations")?.setData(recordsGeoJSON(state.visible));
  state.map.setFilter("company-selected", ["==", ["get", "id"], state.selectedId || "__none__"]);
  renderTray();
}

function flyCountry(country) { const centre = ecosystemHubs[country]?.coordinates || coordinates[country]; if (!centre || !state.map) return; state.map.flyTo({ center: centre, zoom: ["Singapore", "Hong Kong"].includes(country) ? 6.7 : 4.1, duration: 950, curve: 1.1, essential: true }); }
function selectCountry(country) { state.country = country; state.selectedId = null; el.country.value = country; applyFilters(); flyCountry(country); }
function selectedRecord() { return state.records.find((record) => record.id === state.selectedId); }
function layerChips(record) { return [...record.layers].sort((a, b) => b - a).map((layer) => `<span style="--chip:${layerMeta[layer]?.color || "#0d665b"}">Layer ${layer} · ${escapeHTML(layerMeta[layer]?.short || "AI")}</span>`).join(""); }

function leaderMarkup(record) {
  const leader = record.profile?.leader || {};
  if (!meaningful(leader.name)) return "";
  const name = String(leader.name);
  const position = meaningful(leader.position) ? String(leader.position) : "";
  const photo = hasURL(leader.photo) ? `<img src="${escapeHTML(leader.photo)}" alt="${escapeHTML(name)}" loading="lazy" decoding="async" data-leader-photo />` : `<span>${escapeHTML(initials(name))}</span>`;
  const links = [profileLink(leader.linkedin,"Leadership profile"),profileLink(leader.officialProfile,"Official leadership profile")].filter(Boolean).join("");
  return `<article class="map-leader-card"><div class="map-leader-photo">${photo}</div><div><span>KEY LEADERSHIP</span><strong>${escapeHTML(name)}</strong>${position?`<p>${escapeHTML(position)}</p>`:""}</div>${links ? `<nav>${links}</nav>` : ""}</article>`;
}

function profileFacts(record) {
  const market = record.profile?.market || {};
  const profile=record.profile||{}, ai=profile.aiPosition||{};
  const facts=[
    ["Type",profile.ownershipStatus||market.type||record.organisationType,"type"],
    ["Status",profile.lifecycleStatus,"status"],
    ["Headquarters",formatHeadquarters(record),"location"],
    ["Layer",`Layer ${record.primaryLayer} · ${layerMeta[record.primaryLayer]?.short||"AI"}`,`layer-${record.primaryLayer}`],
    ["Focus",ai.primaryCapability,"focus"],
    ["Founded",profile.foundedYear,"founded"],
    ["AI classification",ai.aiIntensity,"ai"],
    ["Application vertical",record.verticals.slice(0,3).join(" · "),"vertical"],
  ];
  if(market.type==="public") facts.push(["Market",[market.ticker,market.exchange].filter(meaningful).join(" · "),"market"]);
  if(market.type==="private") {
    const fundraising=[market.latestRoundType,meaningful(market.latestRoundAmountUsd)?formatUsd(market.latestRoundAmountUsd):null,market.latestRoundDate].filter(meaningful).join(" · ");
    if(fundraising) facts.push(["Fundraising",fundraising,"funding"]);
    if(meaningful(market.totalFundingUsd)) facts.push(["Total funding",formatUsd(market.totalFundingUsd),"funding"]);
    if(meaningful(market.latestValuationUsd)) facts.push(["Latest valuation",`${formatUsd(market.latestValuationUsd)}${meaningful(market.valuationDate)?` · ${market.valuationDate}`:""}`,"unicorn"]);
  }
  if(/^(unicorn|decacorn)/i.test(String(market.unicornStatus||""))) facts.push(["Unicorn status",market.unicornStatus.split("—")[0].trim(),"unicorn"]);
  return facts.filter(([,value])=>meaningful(value)).map(([label,value,tone])=>`<div class="is-${escapeHTML(tone)}"><dt><i aria-hidden="true"></i>${escapeHTML(label)}</dt><dd>${escapeHTML(value)}</dd></div>`).join("");
}

function profileLinks(record) {
  const market=record.profile?.market||{};
  const directoryLinks=market.type!=="public"&&credibleDirectoryLink(market.crunchbase,record)?profileLink(market.crunchbase,"Crunchbase"):"";
  const links=[profileLink(record.website||record.source,"Official website"),profileLink(record.linkedin,"Company social profile"),directoryLinks,profileLink(market.dealroom,"Dealroom"),profileLink(market.yahooFinance,"Yahoo Finance"),profileLink(market.investorRelations,"Investor information")];
  return links.filter(Boolean).join("");
}

function tradingViewSymbol(market={}) {
  const raw=String(market.ticker||"").trim().toUpperCase(); if(!raw) return "";
  const suffixes=[[".JK","IDX"],[".SI","SGX"],[".KL","MYX"],[".TWO","TPEX"],[".TW","TWSE"],[".T","TSE"],[".KS","KRX"],[".KQ","KOSDAQ"],[".HK","HKEX"],[".PA","EURONEXT"],[".AS","EURONEXT"],[".DE","XETR"],[".AX","ASX"],[".SW","SIX"],[".VN","HOSE"],[".SS","SSE"],[".SZ","SZSE"],[".NS","NSE"],[".BO","BSE"],[".L","LSE"]];
  for(const [suffix,exchange] of suffixes) if(raw.endsWith(suffix)) return `${exchange}:${raw.slice(0,-suffix.length)}`;
  const exchange=String(market.exchange||"");
  if(/nasdaq/i.test(exchange)) return `NASDAQ:${raw.replace(/-/g,".")}`;
  if(/new york|^nyse$/i.test(exchange)) return `NYSE:${raw.replace(/-/g,".")}`;
  if(/otc/i.test(exchange)) return `OTC:${raw.replace(/-/g,".")}`;
  return raw.replace(/-/g,".");
}

function formatMarketNumber(value, currency = "") {
  const amount=Number(value); if(!Number.isFinite(amount)) return "—";
  const compact=new Intl.NumberFormat("en-US",{notation:"compact",maximumFractionDigits:2}).format(amount);
  return currency ? `${currency} ${compact}` : compact;
}
function formatPercent(value) { const number=Number(value); return Number.isFinite(number)?`${number>0?"+":""}${number.toFixed(1)}%`:"—"; }
function marketTimestamp(value) { const seconds=Number(value); if(!Number.isFinite(seconds)) return ""; return new Intl.DateTimeFormat("en",{dateStyle:"medium",timeStyle:"short",timeZone:"Asia/Jakarta"}).format(new Date(seconds*1000)); }
function marketMetric(label,value,tone="") { return meaningful(value)&&value!=="—"?`<article class="map-market-metric ${tone}"><span>${escapeHTML(label)}</span><strong>${escapeHTML(value)}</strong></article>`:""; }
function scorePanel(snapshot) {
  const score=snapshot?.fundamental_score; if(!score||!Number.isFinite(Number(score.score))) return "";
  const axes=(score.axes||[]).filter((axis)=>Number.isFinite(Number(axis.score)));
  return `<section class="map-market-intelligence"><div class="map-score-summary"><div><span>COCKPIT OPPORTUNITY SCREEN</span><strong>${escapeHTML(score.label||"Screened")}</strong><p>Deterministic screen · not an investment recommendation</p></div><b>${Math.round(Number(score.score))}<small>/100</small></b></div><div class="map-score-meta"><span>${escapeHTML(score.confidence||"Unrated")} confidence</span><span>${Math.round(Number(score.data_confidence_pct||0))}% data confidence</span><span>${Math.round(Number(score.coverage||0)*100)}% coverage</span></div>${axes.length?`<div class="map-score-axes">${axes.map((axis)=>`<div><span>${escapeHTML(axis.label)}</span><i style="--score:${Math.max(0,Math.min(100,Number(axis.score)))}%"></i><strong>${Math.round(Number(axis.score))}</strong></div>`).join("")}</div>`:""}</section>`;
}
function analystPanel(snapshot,currency) {
  const low=Number(snapshot?.analyst_target_low),median=Number(snapshot?.analyst_target_median),high=Number(snapshot?.analyst_target_high);
  if(![low,median,high].some(Number.isFinite)) return "";
  return `<section class="map-market-target"><span>ANALYST PRICE RANGE</span><div>${Number.isFinite(low)?`<p><small>Low</small><strong>${escapeHTML(formatMarketNumber(low,currency))}</strong></p>`:""}${Number.isFinite(median)?`<p><small>Median</small><strong>${escapeHTML(formatMarketNumber(median,currency))}</strong></p>`:""}${Number.isFinite(high)?`<p><small>High</small><strong>${escapeHTML(formatMarketNumber(high,currency))}</strong></p>`:""}</div></section>`;
}
function marketNews(snapshot) {
  const stories=(snapshot?.news||[]).filter((item)=>hasURL(item.url)&&item.title).slice(0,4); if(!stories.length) return "";
  return `<section class="map-market-news"><span>LATEST MARKET COVERAGE</span>${stories.map((item)=>`<a href="${escapeHTML(item.url)}" target="_blank" rel="noopener"><strong>${escapeHTML(item.title)}</strong><small>${escapeHTML(item.source||"Source")}${item.ts?` · ${escapeHTML(new Intl.DateTimeFormat("en",{dateStyle:"medium"}).format(new Date(Number(item.ts)*1000)))}`:""}</small></a>`).join("")}</section>`;
}
function publicMarketPanel(record) {
  const market=record.profile?.market||{}, snapshot=record.marketSnapshot||{}, symbol=tradingViewSymbol(market);
  const currency=snapshot.fundamental_score?.currency||String(snapshot.mktcap||"").split(" ")[0]||"";
  const metrics=[marketMetric("Last price",formatMarketNumber(snapshot.value,currency)),marketMetric("Day move",formatPercent(snapshot.delta_pct),Number(snapshot.delta_pct)>=0?"is-positive":"is-negative"),marketMetric("Market cap",snapshot.mktcap||formatMarketNumber(snapshot.market_cap_value,currency)),marketMetric("6M return",formatPercent(snapshot.perf_6m),Number(snapshot.perf_6m)>=0?"is-positive":"is-negative")].join("");
  const observed=marketTimestamp(snapshot.quote_asof);
  return `<section class="map-public-market"><div class="map-market-heading"><div><span>PUBLIC MARKET</span><strong>${escapeHTML([market.ticker,market.exchange].filter(Boolean).join(" · "))}</strong>${observed?`<small>Snapshot ${escapeHTML(observed)} WIB · ${escapeHTML(snapshot.source_name||"Project Cockpit")}</small>`:""}</div><div class="map-profile-link-row">${profileLink(market.yahooFinance,"Yahoo Finance")}${profileLink(market.investorRelations,"Investor relations")}</div></div>${metrics?`<div class="map-market-metrics">${metrics}</div>`:""}${scorePanel(snapshot)}${analystPanel(snapshot,currency)}${symbol?`<div class="map-public-chart" id="mapPublicChart" data-symbol="${escapeHTML(symbol)}"><span>Loading market chart…</span></div>`:`<p class="map-profile-empty">No chart symbol is available for this listing.</p>`}${marketNews(snapshot)}${snapshot.market_data_warning?`<p class="map-market-warning">${escapeHTML(snapshot.market_data_warning)}</p>`:""}<p class="map-market-method">Market observations may be delayed. Screening scores describe the available evidence and are not investment advice.</p></section>`;
}

function mountPublicChart(record) {
  const host=el.context?.querySelector("#mapPublicChart"); if(!host||host.dataset.mounted) return;
  const symbol=host.dataset.symbol; if(!symbol) return; host.dataset.mounted="1"; host.innerHTML="";
  const script=document.createElement("script"); script.async=true; script.src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
  script.text=JSON.stringify({autosize:true,symbol,interval:"D",timezone:"Asia/Jakarta",theme:"dark",style:"1",locale:"en",allow_symbol_change:false,calendar:false,hide_side_toolbar:true,withdateranges:true,support_host:"https://www.tradingview.com"});
  host.appendChild(script);
}

function renderProfile(record) {
  const profile = record.profile || {};
  const isPublic=profile.market?.type==="public";
  const companyBody=`<p class="map-profile-offering">${escapeHTML(profile.description || record.offering)}</p><dl class="map-profile-facts">${profileFacts(record)}</dl><nav class="map-profile-icon-row" aria-label="Company links">${profileLinks(record)}</nav>${leaderMarkup(record)}`;
  const tabs=isPublic?`<div class="map-profile-tabs is-public" role="tablist" aria-label="Company and market views"><button type="button" role="tab" data-profile-tab="company" aria-selected="${state.profileTab==="company"}" class="${state.profileTab==="company"?"is-active":""}">Company</button><button type="button" role="tab" data-profile-tab="market" aria-selected="${state.profileTab==="market"}" class="${state.profileTab==="market"?"is-active":""}">Market</button></div>`:"";
  const content=isPublic?`<section class="map-profile-panel" data-profile-panel="company"${state.profileTab==="company"?"":" hidden"}>${companyBody}</section><section class="map-profile-panel" data-profile-panel="market"${state.profileTab==="market"?"":" hidden"}>${publicMarketPanel(record)}</section>`:`<section class="map-profile-panel map-profile-single">${companyBody}</section>`;
  el.context.innerHTML = `<button class="map-context-close" type="button" data-close-profile aria-label="Close company profile">×</button><div class="map-profile-brand">${logoMarkup(record, "map-profile-logo")}<div><span class="map-profile-kicker">${escapeHTML(profile.entityType||record.organisationType||"Organisation")}</span><h2>${escapeHTML(record.name)}</h2></div></div>${tabs}${content}`;
  el.context.classList.add("is-open"); el.workspace.classList.add("has-selected-company"); attachLogoFallbacks(el.context);
  el.context.querySelectorAll("img[data-leader-photo]").forEach((image)=>image.addEventListener("error",()=>{const fallback=document.createElement("span");fallback.textContent=initials(profile.leader?.name||record.name);image.replaceWith(fallback);},{once:true}));
  if(isPublic&&state.profileTab==="market") mountPublicChart(record);
}

function setProfileTab(tab) {
  if (!el.context?.classList.contains("is-open")) return;
  state.profileTab = tab;
  el.context.querySelectorAll("[data-profile-tab]").forEach((button)=>{const active=button.dataset.profileTab===tab;button.classList.toggle("is-active",active);button.setAttribute("aria-selected",String(active));});
  el.context.querySelectorAll("[data-profile-panel]").forEach((panel)=>{panel.hidden=panel.dataset.profilePanel!==tab;});
  if(tab==="market") { const record=selectedRecord(); if(record) mountPublicChart(record); }
}

function renderContext() { const record = selectedRecord(); if (record) renderProfile(record); else { el.context.innerHTML = ""; el.context.classList.remove("is-open"); el.workspace.classList.remove("has-selected-company"); } }
function recordsInMapView() {
  if (!state.mapReady || !state.map) return state.visible;
  const hasActiveFilter = Boolean(state.search) || state.region !== "all" || state.layer !== "all" || state.country !== "all" || state.ownership !== "all" || state.vertical !== "all";
  if (hasActiveFilter) return state.visible;
  const bounds = state.map.getBounds();
  return state.visible.filter((record)=>!record.mapCoordinates || bounds.contains(record.mapCoordinates));
}
function renderInsights() {
  if (!el.hubInsights || !el.layerInsights || !el.verticalInsights) return;
  const hubs=countrySummary(facetRecords("country")).filter(([country])=>country!=="Global");
  const largestHub=hubs[0]?.[1]||1;
  el.hubInsights.innerHTML=hubs.length?`<div class="insight-ranking">${hubs.map(([country,count],index)=>`<button type="button" data-insight-country="${escapeHTML(country)}" class="${state.country===country?"is-active":""}" aria-pressed="${state.country===country}"><span>${String(index+1).padStart(2,"0")}</span><strong>${escapeHTML(country)}</strong><i style="--share:${Math.max(7,count/largestHub*100)}%"></i><small>${count}</small></button>`).join("")}</div>`:`<p class="insight-empty">No headquarters match these filters.</p>`;

  const layerFacet=facetRecords("layer");
  const layers=Object.keys(layerMeta).map(Number).sort((a,b)=>b-a).map((layer)=>[layer,layerFacet.filter((record)=>record.layers.includes(layer)).length]).filter(([,count])=>count>0);
  el.layerInsights.innerHTML=layers.length?`<div class="insight-layer-list">${layers.map(([layer,count])=>`<button type="button" data-insight-layer="${layer}" class="${String(state.layer)===String(layer)?"is-active":""}" aria-pressed="${String(state.layer)===String(layer)}"><i style="--layer-color:${layerMeta[layer].color}"></i><span>Layer ${layer} · ${escapeHTML(layerMeta[layer].short)}</span><strong>${count}</strong></button>`).join("")}</div>`:`<p class="insight-empty">No stack layers match these filters.</p>`;

  const verticals=verticalSummary(facetRecords("vertical"));
  el.verticalInsights.innerHTML=verticals.length?`<div class="insight-vertical-list">${verticals.map(([vertical,count])=>`<button type="button" data-insight-vertical="${escapeHTML(vertical)}" class="${state.vertical===vertical?"is-active":""}" aria-pressed="${state.vertical===vertical}"><span>${escapeHTML(vertical)}</span><strong>${count}</strong></button>`).join("")}</div>`:`<p class="insight-empty">No application verticals match these filters.</p>`;
  attachLogoFallbacks(document.querySelector(".map-insight-rail"));
}
function renderTray() {
  const inView = recordsInMapView();
  const records = inView.slice().sort((a,b)=>Number(b.featured)-Number(a.featured)||a.name.localeCompare(b.name));
  el.trayCount.textContent = inView.length.toLocaleString("en-US");
  el.trayLabel.textContent = state.country !== "all" ? `Filtered results headquartered in ${state.country}` : state.search ? `Filtered results for “${el.search.value.trim()}”` : state.region !== "all" || state.layer !== "all" || state.ownership !== "all" || state.vertical !== "all" ? "All organisations matching the active filters" : "Organisations visible in the current map area";
  el.tray.innerHTML = records.length ? records.map((record)=>`<button class="map-tray-company${state.selectedId===record.id?" is-selected":""}" type="button" data-map-company="${escapeHTML(record.id)}">${logoMarkup(record)}<span>${escapeHTML(record.name)}</span></button>`).join("") : `<span class="map-tray-empty">No mapped organisations are visible here.</span>`;
  attachLogoFallbacks(el.tray);
}

function databaseMatches(record) {
  if (!regionValueMatches(record,databaseState.region)) return false;
  if (databaseState.layer !== "all" && !record.layers.includes(Number(databaseState.layer))) return false;
  if (databaseState.country !== "all" && record.country !== databaseState.country) return false;
  if (!ownershipValueMatches(record,databaseState.ownership)) return false;
  if (databaseState.vertical !== "all" && !record.verticals.includes(databaseState.vertical)) return false;
  if (!databaseState.search) return true;
  return [record.name,record.offering,record.location,record.country,record.region,record.organisationType,record.searchable,...record.verticals].join(" ").toLowerCase().includes(databaseState.search);
}

function renderDatabase() {
  if (!el.databaseRows) return;
  const records = state.records.filter(databaseMatches).sort((a,b)=>a.name.localeCompare(b.name));
  el.databaseCount.textContent = records.length.toLocaleString("en-US");
  el.databaseRange.textContent = records.length ? `${records.length.toLocaleString("en-US")} results · scroll to explore all` : "0 results";
  el.databaseRows.innerHTML = records.length ? records.map((record)=>`<tr data-database-company="${escapeHTML(record.id)}" tabindex="0"><td><span class="database-company-cell">${logoMarkup(record,"database-company-logo")}<span><strong>${escapeHTML(record.name)}</strong><small>${escapeHTML(record.profile?.description||record.offering)}</small></span></span></td><td><span class="database-layer-pill" style="--database-layer:${layerMeta[record.primaryLayer]?.color||"#0d665b"}">${record.primaryLayer} · ${escapeHTML(layerMeta[record.primaryLayer]?.short||"AI")}</span></td><td>${escapeHTML(formatHeadquarters(record))}</td><td>${escapeHTML(displayValue(record.profile?.ownershipStatus,record.organisationType))}</td><td>${escapeHTML(displayValue(record.profile?.lifecycleStatus))}</td><td>${record.verticals.length?escapeHTML(record.verticals.slice(0,2).join(" · ")):"—"}</td></tr>`).join("") : `<tr><td class="database-empty" colspan="6">No organisations match these filters.</td></tr>`;
  attachLogoFallbacks(el.databaseRows);
}

function syncDatabaseFilters() { databaseState.search=state.search; databaseState.region=state.region; databaseState.layer=state.layer; databaseState.country=state.country; databaseState.ownership=state.ownership; databaseState.vertical=state.vertical; el.databaseSearch.value=el.search.value.trim(); el.databaseRegion.value=databaseState.region; el.databaseLayer.value=databaseState.layer; el.databaseCountry.value=databaseState.country; if(el.databaseOwnership) el.databaseOwnership.value=databaseState.ownership; if(el.databaseVertical) el.databaseVertical.value=databaseState.vertical; }
function openDatabase() { syncDatabaseFilters(); renderDatabase(); el.database.showModal(); }
function closeDatabase() { if (el.database?.open) el.database.close(); }
function focusDatabaseCompany(id) {
  const record = state.records.find((item)=>item.id===id); if (!record) return;
  closeDatabase(); selectCompany(record.id);
}

function applyDatabaseFiltersToMap() {
  state.search=databaseState.search; state.region=databaseState.region; state.layer=databaseState.layer; state.country=databaseState.country; state.ownership=databaseState.ownership; state.vertical=databaseState.vertical; state.selectedId=null;
  el.search.value=databaseState.search; el.region.value=databaseState.region; el.layer.value=databaseState.layer; el.country.value=databaseState.country; el.ownership.value=databaseState.ownership; el.vertical.value=databaseState.vertical;
  applyFilters(); renderDatabase();
}

function renderMetrics() { const hubs = countrySummary(state.visible); const layers=new Set(state.visible.flatMap((record)=>record.layers)).size; el.count.textContent = state.visible.length.toLocaleString("en-US"); el.countryCount.textContent = hubs.length.toLocaleString("en-US"); el.topHub.textContent = hubs[0]?.[0] || "None"; const label=document.querySelector(".map-panel-title small"); if(label) label.textContent=`${state.visible.length.toLocaleString("en-US")} results · ${layers} ${layers===1?"layer":"layers"}`; }
function refreshMapCountryOptions(records) {
  const current=state.country;
  const options=countrySummary(records).map(([country,count])=>`<option value="${escapeHTML(country)}">${escapeHTML(country)} · ${count}</option>`).join("");
  el.country.innerHTML=`<option value="all">All locations</option>${options}`;
  el.country.value=[...el.country.options].some((option)=>option.value===current)?current:"all";
}
function refreshVerticalOptions(records) {
  const current=state.vertical;
  const options=verticalSummary(records).map(([vertical,count])=>`<option value="${escapeHTML(vertical)}">${escapeHTML(vertical)} · ${count}</option>`).join("");
  el.vertical.innerHTML=`<option value="all">All application verticals</option>${options}`;
  el.vertical.value=[...el.vertical.options].some((option)=>option.value===current)?current:"all";
  if(el.databaseVertical){el.databaseVertical.innerHTML=`<option value="all">All application verticals</option>${options}`;el.databaseVertical.value=[...el.databaseVertical.options].some((option)=>option.value===databaseState.vertical)?databaseState.vertical:"all";}
}
function applyFilters() {
  let countryFacet=facetRecords("country");
  if (state.country !== "all" && !countryFacet.some((record)=>record.country===state.country)) state.country="all";
  let verticalFacet=facetRecords("vertical");
  if (state.vertical !== "all" && !verticalFacet.some((record)=>record.verticals.includes(state.vertical))) state.vertical="all";
  countryFacet=facetRecords("country");
  verticalFacet=facetRecords("vertical");
  state.densityRecords=countryFacet;
  state.visible=facetRecords();
  refreshMapCountryOptions(countryFacet);
  refreshVerticalOptions(verticalFacet);
  if (state.selectedId && !state.visible.some((record)=>record.id===state.selectedId)) state.selectedId=null;
  renderMetrics(); renderContext(); renderInsights(); updateMapSources(); if (!state.mapReady) renderTray();
}

function restyleBasemap(map) {
  const layers = map.getStyle()?.layers || [];
  layers.forEach((layer) => {
    try {
      if (layer.type === "background") map.setPaintProperty(layer.id,"background-color","#0b100c");
      if (layer.id === "water" || /water/.test(layer.id) && layer.type === "fill") map.setPaintProperty(layer.id,"fill-color","#0c1713");
      if (layer.type === "fill" && /landcover|landuse|park|wood|sand/.test(layer.id)) map.setPaintProperty(layer.id,"fill-color","#121b15");
      if (layer.type === "line" && /boundary/.test(layer.id)) map.setPaintProperty(layer.id,"line-color","#34473c");
      if (layer.type === "symbol") { map.setPaintProperty(layer.id,"text-color","#8fa096"); map.setPaintProperty(layer.id,"text-halo-color","#0d140f"); }
    } catch (_) {}
  });
}

function addMapLayers() {
  const map = state.map;
  restyleBasemap(map);
  map.setProjection({ type: "globe" });
  map.setSky({ "sky-color":"#080c09", "horizon-color":"#172219", "fog-color":"#111a14", "sky-horizon-blend":0.64, "horizon-fog-blend":0.55, "fog-ground-blend":0.5, "atmosphere-blend":["interpolate",["linear"],["zoom"],0,0.72,5,0] });
  const firstSymbol = map.getStyle().layers.find((layer)=>layer.type==="symbol")?.id;
  map.addSource("ai-countries",{type:"geojson",data:countriesGeoJSON(state.densityRecords)});
  map.addLayer({id:"country-density",type:"fill",source:"ai-countries",paint:{"fill-color":["case",["boolean",["get","selected"],false],"#b99734",["interpolate",["linear"],["get","density"],0,"#101711",5,"#183126",20,"#22513f",60,"#2f745c",140,"#3d9677",260,"#74bea0"]],"fill-opacity":["case",[">",["get","density"],0],0.72,0.18]},filter:["!=",["get","canonical"],""]},firstSymbol);
  map.addLayer({id:"country-outline",type:"line",source:"ai-countries",paint:{"line-color":["case",["boolean",["get","selected"],false],"#f0d77a","rgba(123,164,143,.34)"],"line-width":["case",["boolean",["get","selected"],false],2.2,0.7],"line-opacity":0.9}},firstSymbol);
  map.addSource("ai-organisations",{type:"geojson",data:recordsGeoJSON(state.densityRecords),cluster:true,clusterRadius:34,clusterMaxZoom:5});
  map.addLayer({id:"company-clusters-halo",type:"circle",source:"ai-organisations",filter:["has","point_count"],paint:{"circle-radius":["step",["get","point_count"],16,15,20,45,27,120,34],"circle-color":"rgba(11,18,13,.92)","circle-stroke-color":"rgba(134,199,174,.34)","circle-stroke-width":1}},firstSymbol);
  map.addLayer({id:"company-clusters",type:"circle",source:"ai-organisations",filter:["has","point_count"],paint:{"circle-radius":["step",["get","point_count"],12,15,16,45,22,120,29],"circle-color":["step",["get","point_count"],"#5ba18b",15,"#3f967c",45,"#2b755f",120,"#86c7ae"],"circle-stroke-color":"#dce8df","circle-stroke-width":1.6}},firstSymbol);
  map.addLayer({id:"company-cluster-count",type:"symbol",source:"ai-organisations",filter:["has","point_count"],layout:{"text-field":["get","point_count_abbreviated"],"text-font":["Noto Sans Bold"],"text-size":11},paint:{"text-color":"#ffffff","text-halo-color":"rgba(4,42,37,.18)","text-halo-width":0.5}},firstSymbol);
  map.addLayer({id:"company-points",type:"circle",source:"ai-organisations",filter:["!",["has","point_count"]],paint:{"circle-radius":["interpolate",["linear"],["zoom"],1.5,3.4,4,5.8,7,8],"circle-color":["match",["get","layer"],6,layerMeta[6].color,5,layerMeta[5].color,4,layerMeta[4].color,3,layerMeta[3].color,2,layerMeta[2].color,1,layerMeta[1].color,"#0d665b"],"circle-stroke-color":"#dce8df","circle-stroke-width":["interpolate",["linear"],["zoom"],1.5,0.8,6,1.6],"circle-opacity":0.96}},firstSymbol);
  map.addLayer({id:"company-selected",type:"circle",source:"ai-organisations",filter:["==",["get","id"],"__none__"],paint:{"circle-radius":["interpolate",["linear"],["zoom"],1.5,7,6,13],"circle-color":"rgba(255,255,255,0)","circle-stroke-color":"#102b27","circle-stroke-width":2.5}},firstSymbol);
}

function popupHTML(properties, countryMode = false) {
  if (countryMode) return `<strong>${escapeHTML(properties.canonical)}</strong><span>${properties.density} ${Number(properties.density)===1?"organisation":"organisations"}</span><small>${Number(properties.density)>0?"Select to explore":"No current coverage"}</small>`;
  const precision=properties.precision==="verified"?"Verified coordinate":properties.precision==="hub"?"Ecosystem-hub estimate":"Country-level estimate";
  return `<strong>${escapeHTML(properties.name)}</strong><span>${escapeHTML(properties.country)} · Layer ${properties.layer}</span><small>${precision}</small>`;
}

function initialiseMap() {
  if (!el.stage || typeof maplibregl === "undefined") { el.loading.innerHTML = "<p>The interactive map could not load.</p>"; return; }
  state.map = new maplibregl.Map({ container: el.stage, style: MAP_STYLE, center: [-88,28], zoom: 1.5, minZoom: 1.05, maxZoom: 9, attributionControl: { compact: true }, antialias: true, renderWorldCopies: false });
  state.map.addControl(new maplibregl.NavigationControl({showCompass:true,showZoom:true,visualizePitch:true}),"bottom-right");
  state.hoverPopup = new maplibregl.Popup({closeButton:false,closeOnClick:false,offset:12,className:"ai-map-popup"});
  state.map.on("style.load",()=>{ addMapLayers(); state.mapReady=true; el.loading.hidden=true; updateMapSources(); });
  state.map.on("click","company-clusters",async(event)=>{ const feature=event.features?.[0]; if(!feature) return; const source=state.map.getSource("ai-organisations"); const clusterId=feature.properties.cluster_id; const leaves=await source.getClusterLeaves(clusterId,500,0); const countries=[...new Set(leaves.map((leaf)=>leaf.properties.country).filter(Boolean))]; if(countries.length===1){selectCountry(countries[0]);return;} const zoom=await source.getClusterExpansionZoom(clusterId); state.map.easeTo({center:feature.geometry.coordinates,zoom,duration:750}); });
  state.map.on("click","company-points",(event)=>{ const feature=event.features?.[0]; if(feature) selectCompany(feature.properties.id); });
  state.map.on("click","country-density",(event)=>{ if(state.map.queryRenderedFeatures(event.point,{layers:["company-points","company-clusters"]}).length) return; const feature=event.features?.[0]; if(feature && Number(feature.properties.density)>0) selectCountry(feature.properties.canonical); });
  ["company-clusters","company-points","country-density"].forEach((layer)=>state.map.on("mouseenter",layer,()=>{state.map.getCanvas().style.cursor="pointer";}));
  ["company-clusters","company-points","country-density"].forEach((layer)=>state.map.on("mouseleave",layer,()=>{state.map.getCanvas().style.cursor="";}));
  state.map.on("mousemove","company-points",(event)=>{ const feature=event.features?.[0]; if(feature) state.hoverPopup.setLngLat(feature.geometry.coordinates).setHTML(`<div class="maplibre-tip">${popupHTML(feature.properties)}</div>`).addTo(state.map); });
  state.map.on("mouseleave","company-points",()=>state.hoverPopup.remove());
  state.map.on("mousemove","country-density",(event)=>{ if(state.map.queryRenderedFeatures(event.point,{layers:["company-points","company-clusters"]}).length) return; const feature=event.features?.[0]; if(feature) state.hoverPopup.setLngLat(event.lngLat).setHTML(`<div class="maplibre-tip">${popupHTML(feature.properties,true)}</div>`).addTo(state.map); });
  state.map.on("mouseleave","country-density",()=>state.hoverPopup.remove());
  state.map.on("moveend",renderTray);
  state.map.on("error",(event)=>{ if (!state.mapReady) { console.error(event.error); el.loading.innerHTML="<p>The map background could not load.</p>"; } });
}

function populateCountries() { const countries=[...new Set(state.records.map((record)=>record.country))].sort((a,b)=>a.localeCompare(b)); const options=`<option value="all">All locations</option>${countries.map((country)=>`<option value="${escapeHTML(country)}">${escapeHTML(country)}</option>`).join("")}`; el.country.innerHTML=options; if(el.databaseCountry) el.databaseCountry.innerHTML=options; const label=document.querySelector(".map-panel-title small"); if(label) label.textContent=`${state.records.length.toLocaleString("en-US")} organisations · 6 layers`; }
function flyOverview(region="all") {
  const views={sea:{center:[112,4],zoom:3.3},apac:{center:[112,20],zoom:2.3},"North America":{center:[-100,36],zoom:2.35},Europe:{center:[13,51],zoom:2.75},Global:{center:[0,20],zoom:1.5},all:{center:[-88,28],zoom:1.5}};
  state.map?.flyTo({...(views[region]||views.all),duration:900,essential:true});
}
function resetView() { state.region="all"; state.layer="all"; state.country="all"; state.ownership="all"; state.vertical="all"; state.search=""; state.selectedId=null; el.search.value=""; el.region.value="all"; el.layer.value="all"; el.country.value="all"; el.ownership.value="all"; el.vertical.value="all"; applyFilters(); flyOverview(); }
function selectCompany(id) { const record=state.records.find((item)=>item.id===id); if (!record) return; state.selectedId=id; state.profileTab="company"; renderContext(); updateMapSources(); if(record.mapCoordinates) state.map?.flyTo({center:record.mapCoordinates,zoom:Math.max(state.map.getZoom(),5),duration:850,essential:true}); }
function setMobileFilters(open) { if (!el.controls || !el.filtersToggle) return; const compact=window.matchMedia("(max-width: 780px)").matches; el.controls.classList.toggle("is-collapsed",compact&&!open); el.filtersToggle.setAttribute("aria-expanded",String(compact&&open)); el.filtersToggle.querySelector("span").textContent=compact&&open?"Close":"Filters"; }
function openOnboarding(force=false) {
  if (!el.onboarding || el.onboarding.open) return;
  let hasSeen=false; try { hasSeen=localStorage.getItem("ai-map-onboarding-v1")==="seen"; } catch (_) {}
  if (!force && hasSeen) return;
  el.onboarding.showModal();
}
function dismissOnboarding() {
  if (el.onboarding?.open) el.onboarding.close();
  try { localStorage.setItem("ai-map-onboarding-v1","seen"); } catch (_) {}
}
let openingFinished=false;
function finishOpening() {
  if (openingFinished) return;
  openingFinished=true;
  if (!el.opening) { openOnboarding(); return; }
  el.opening.classList.add("is-leaving");
  window.setTimeout(()=>{ el.opening.hidden=true; openOnboarding(); },650);
}

document.addEventListener("click", (event) => {
  const country=event.target.closest("[data-map-country]"); if (country) selectCountry(country.dataset.mapCountry);
  const company=event.target.closest("[data-map-company]"); if (company) selectCompany(company.dataset.mapCompany);
  const insightCountry=event.target.closest("[data-insight-country]"); if(insightCountry){ const value=insightCountry.dataset.insightCountry; if(state.country===value){state.country="all";el.country.value="all";applyFilters();flyOverview(state.region);}else selectCountry(value); }
  const insightLayer=event.target.closest("[data-insight-layer]"); if(insightLayer){ const value=insightLayer.dataset.insightLayer; state.layer=state.layer===value?"all":value; state.selectedId=null; el.layer.value=state.layer; applyFilters(); }
  const insightVertical=event.target.closest("[data-insight-vertical]"); if(insightVertical){ const value=insightVertical.dataset.insightVertical; state.vertical=state.vertical===value?"all":value; state.selectedId=null; el.vertical.value=state.vertical; applyFilters(); }
  const profileTab=event.target.closest("[data-profile-tab]"); if(profileTab) setProfileTab(profileTab.dataset.profileTab);
  const databaseCompany=event.target.closest("[data-database-company]"); if(databaseCompany) focusDatabaseCompany(databaseCompany.dataset.databaseCompany);
  if (event.target.closest("[data-close-profile]")) { state.selectedId=null; renderContext(); updateMapSources(); }
  if (event.target.closest("[data-close-context]")) el.context.classList.remove("is-open");
  if (event.target.closest("[data-close-help]")) event.target.closest("details")?.removeAttribute("open");
  if (event.target.closest("[data-dismiss-onboarding]")) dismissOnboarding();
  if (event.target.closest("[data-skip-opening]")) finishOpening();
  if (event.target.closest("[data-reopen-onboarding]")) { event.target.closest("details")?.removeAttribute("open"); openOnboarding(true); }
});

el.search?.addEventListener("input",()=>{ state.search=el.search.value.trim().toLowerCase(); state.country="all"; state.selectedId=null; el.country.value="all"; applyFilters(); });
el.region?.addEventListener("change",()=>{ state.region=el.region.value; state.country="all"; state.selectedId=null; el.country.value="all"; applyFilters(); flyOverview(state.region); });
el.layer?.addEventListener("change",()=>{ state.layer=el.layer.value; state.selectedId=null; applyFilters(); });
el.country?.addEventListener("change",()=>{ if(el.country.value==="all"){state.country="all";state.selectedId=null;applyFilters();flyOverview(state.region);}else selectCountry(el.country.value); });
el.ownership?.addEventListener("change",()=>{ state.ownership=el.ownership.value; state.selectedId=null; applyFilters(); });
el.vertical?.addEventListener("change",()=>{ state.vertical=el.vertical.value; state.selectedId=null; applyFilters(); });
el.reset?.addEventListener("click",resetView);
el.resetView?.addEventListener("click",resetView);
el.filtersToggle?.addEventListener("click",()=>setMobileFilters(el.controls.classList.contains("is-collapsed")));
el.databaseOpen?.addEventListener("click",openDatabase);
el.databaseClose?.addEventListener("click",closeDatabase);
el.database?.addEventListener("click",(event)=>{if(event.target===el.database) closeDatabase();});
el.onboarding?.addEventListener("click",(event)=>{if(event.target===el.onboarding) dismissOnboarding();});
el.onboarding?.addEventListener("cancel",(event)=>{event.preventDefault();dismissOnboarding();});
el.databaseRows?.addEventListener("keydown",(event)=>{const row=event.target.closest("[data-database-company]");if(row&&(event.key==="Enter"||event.key===" ")){event.preventDefault();focusDatabaseCompany(row.dataset.databaseCompany);}});
el.databaseSearch?.addEventListener("input",()=>{databaseState.search=el.databaseSearch.value.trim().toLowerCase();applyDatabaseFiltersToMap();});
el.databaseRegion?.addEventListener("change",()=>{databaseState.region=el.databaseRegion.value;databaseState.country="all";el.databaseCountry.value="all";applyDatabaseFiltersToMap();flyOverview(databaseState.region);});
el.databaseLayer?.addEventListener("change",()=>{databaseState.layer=el.databaseLayer.value;applyDatabaseFiltersToMap();});
el.databaseCountry?.addEventListener("change",()=>{databaseState.country=el.databaseCountry.value;applyDatabaseFiltersToMap();if(databaseState.country!=="all")flyCountry(databaseState.country);});
el.databaseOwnership?.addEventListener("change",()=>{databaseState.ownership=el.databaseOwnership.value;applyDatabaseFiltersToMap();});
el.databaseVertical?.addEventListener("change",()=>{databaseState.vertical=el.databaseVertical.value;applyDatabaseFiltersToMap();});
el.databaseReset?.addEventListener("click",()=>{databaseState.search="";databaseState.region="all";databaseState.layer="all";databaseState.country="all";databaseState.ownership="all";databaseState.vertical="all";el.databaseSearch.value="";el.databaseRegion.value="all";el.databaseLayer.value="all";el.databaseCountry.value="all";if(el.databaseOwnership)el.databaseOwnership.value="all";if(el.databaseVertical)el.databaseVertical.value="all";applyDatabaseFiltersToMap();flyOverview();});
function syncFullscreenControl() { const active=Boolean(document.fullscreenElement)||el.workspace.classList.contains("is-expanded"); el.fullscreen.querySelector("span").textContent=active?"Exit full screen":"Full screen"; el.fullscreen.setAttribute("aria-label",active?"Exit full-screen map":"Open full-screen map"); }
el.fullscreen?.addEventListener("click",async()=>{ try { if(document.fullscreenElement) await document.exitFullscreen(); else if(el.workspace.classList.contains("is-expanded")) el.workspace.classList.remove("is-expanded"); else await el.workspace.requestFullscreen(); } catch (_) { el.workspace.classList.toggle("is-expanded"); } syncFullscreenControl(); setTimeout(()=>state.map?.resize(),180); });
document.addEventListener("fullscreenchange",()=>{ el.workspace.classList.toggle("is-fullscreen",Boolean(document.fullscreenElement)); syncFullscreenControl(); setTimeout(()=>state.map?.resize(),180); });
const compactMapQuery=window.matchMedia("(max-width: 780px)");
setMobileFilters(false);
compactMapQuery.addEventListener?.("change",()=>setMobileFilters(false));
const openingDuration=window.matchMedia("(prefers-reduced-motion: reduce)").matches?450:4900;
window.setTimeout(finishOpening,openingDuration);

Promise.all([
  fetch(`${DATA_ROOT}/entities.json?v=20260904-2`,{cache:"no-store"}).then((response)=>response.json()),
  fetch(`${DATA_ROOT}/application-companies.json?v=20260904-1`,{cache:"no-store"}).then((response)=>response.json()),
  fetch(`${DATA_ROOT}/verticals.json?v=20260904-1`,{cache:"no-store"}).then((response)=>response.json()),
  fetch(`${DATA_ROOT}/company-profiles.json?v=20260907-4`,{cache:"no-store"}).then((response)=>response.json()),
  fetch(`${DATA_ROOT}/public-market-snapshot.json?v=20260907-1`,{cache:"no-store"}).then((response)=>response.json()).catch(()=>({companies:{}})),
  fetch(WORLD_GEOJSON,{cache:"force-cache"}).then((response)=>response.json()),
]).then(([entities,applications,verticals,profiles,market,world])=>{ state.records=mergeDirectories(entities,applications,verticals,profiles,market); state.world=world.features||[]; populateCountries(); applyFilters(); initialiseMap(); }).catch((error)=>{ console.error(error); el.loading.innerHTML="<p>The interactive map background is unavailable. Directory filters remain available.</p>"; });

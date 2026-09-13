#!/usr/bin/env node
/**
 * Incrementally discover missing company/leader X accounts and validate them
 * with XActions. Discovery uses exact-name Brave results; XActions remains the
 * authority for whether a public profile is live and what avatar it exposes.
 *
 * No login, cookies, posting, following, or other account mutation is used.
 */
import fs from "node:fs/promises";
import path from "node:path";
import { Scraper } from "xactions";

const ROOT = path.resolve(process.cwd(), "../..");
const PROFILES = process.argv[2] || path.join(ROOT, "ai-intelligence/data/company-profiles.json");
const RESEARCH = process.argv[3] || path.join(ROOT, "output/ai-intelligence-database/x-account-research.json");
const OUTPUT = process.argv[4] || RESEARCH;
const SEARCH_CONCURRENCY = Math.max(1, Number(process.env.X_SEARCH_CONCURRENCY || 4));
const PROFILE_CONCURRENCY = Math.max(1, Number(process.env.X_PROFILE_CONCURRENCY || 2));
const MAX_CANDIDATES = Math.max(1, Number(process.env.X_MAX_CANDIDATES || 3));
const LIMIT = Math.max(0, Number(process.env.X_PRIORITY_LIMIT || 0));
const UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36";

const rejectedHandles = new Set([
  "home", "share", "intent", "search", "explore", "hashtag", "i", "settings",
  "messages", "notifications", "compose", "login", "signup", "tos", "privacy",
]);
const ignored = new Set([
  "the", "and", "inc", "ltd", "llc", "corp", "corporation", "company", "group",
  "holdings", "technologies", "technology", "international", "global", "official", "chief",
  "executive", "officer", "president", "founder", "chair", "ceo",
]);

function clean(value) { return typeof value === "string" ? value.trim() : ""; }
function normalize(value) {
  return clean(value).toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ").trim();
}
function tokens(value) {
  return normalize(value).split(/\s+/).filter((token) => token.length >= 2 && !ignored.has(token));
}
function canonicalXUrl(value) {
  try {
    const parsed = new URL(value.replaceAll("&amp;", "&"));
    const hostname = parsed.hostname.toLowerCase().replace(/^www\./, "");
    if (!["x.com", "twitter.com", "mobile.twitter.com"].includes(hostname)) return "";
    const segment = parsed.pathname.split("/").filter(Boolean)[0] || "";
    if (!/^[A-Za-z0-9_]{1,15}$/.test(segment) || rejectedHandles.has(segment.toLowerCase())) return "";
    return `https://x.com/${segment}`;
  } catch { return ""; }
}
function xHandle(value) { const url = canonicalXUrl(value); return url ? new URL(url).pathname.slice(1) : ""; }
function host(value) { try { return new URL(value).hostname.toLowerCase().replace(/^www\./, ""); } catch { return ""; } }
function registrableHost(value) {
  const parts = host(value).split(".");
  return parts.length > 2 ? parts.slice(-2).join(".") : parts.join(".");
}
function hasUrl(value) { return /^https?:\/\//i.test(clean(value)); }

async function mapLimit(items, limit, callback) {
  const results = new Array(items.length);
  let cursor = 0;
  async function worker() {
    while (true) {
      const index = cursor++;
      if (index >= items.length) return;
      try { results[index] = await callback(items[index], index); }
      catch (error) { results[index] = { error: String(error?.message || error) }; }
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return results;
}

async function braveCandidates(query) {
  const url = `https://search.brave.com/search?q=${encodeURIComponent(query)}&source=web`;
  try {
    const response = await fetch(url, { headers: { "user-agent": UA, "accept-language": "en-US,en;q=0.9" } });
    if (!response.ok) return { sourceUrl: url, status: `http_${response.status}`, urls: [] };
    const html = await response.text();
    const urls = [];
    const seen = new Set();
    for (const match of html.matchAll(/https?:\/\/(?:www\.)?(?:x|twitter)\.com\/[A-Za-z0-9_]{1,15}/gi)) {
      const candidate = canonicalXUrl(match[0]);
      if (!candidate || seen.has(candidate.toLowerCase())) continue;
      seen.add(candidate.toLowerCase());
      urls.push(candidate);
      if (urls.length >= MAX_CANDIDATES) break;
    }
    return { sourceUrl: url, status: "ok", urls };
  } catch (error) {
    return { sourceUrl: url, status: `error:${String(error?.message || error).slice(0, 120)}`, urls: [] };
  }
}

async function duckDuckGoCandidates(query) {
  const url = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;
  try {
    const response = await fetch(url, { headers: { "user-agent": UA, "accept-language": "en-US,en;q=0.9" } });
    if (!response.ok) return { sourceUrl: url, status: `http_${response.status}`, urls: [] };
    const html = await response.text();
    const urls = [];
    const seen = new Set();
    const add = (value) => {
      const candidate = canonicalXUrl(value);
      if (!candidate || seen.has(candidate.toLowerCase())) return;
      seen.add(candidate.toLowerCase());
      urls.push(candidate);
    };
    for (const match of html.matchAll(/uddg=([^&"']+)/gi)) {
      try { add(decodeURIComponent(match[1].replaceAll("&amp;", "&"))); } catch {}
      if (urls.length >= MAX_CANDIDATES) break;
    }
    if (urls.length < MAX_CANDIDATES) {
      for (const match of html.matchAll(/https?:\/\/(?:www\.)?(?:x|twitter)\.com\/[A-Za-z0-9_]{1,15}/gi)) {
        add(match[0]);
        if (urls.length >= MAX_CANDIDATES) break;
      }
    }
    return { sourceUrl: url, status: "ok", urls };
  } catch (error) {
    return { sourceUrl: url, status: `error:${String(error?.message || error).slice(0, 120)}`, urls: [] };
  }
}

async function exactSearchCandidates(query) {
  // DuckDuckGo's HTML endpoint is intentionally used first because it exposes
  // stable result targets without requiring an account. Brave is a fallback.
  const primary = await duckDuckGoCandidates(query);
  if (primary.urls.length || primary.status === "ok") return primary;
  return braveCandidates(query);
}

function priority(company) {
  const leader = company.leader || {};
  const hasSocial = hasUrl(leader.linkedin) || hasUrl(leader.x);
  const hasPhoto = hasUrl(leader.photo) || hasUrl(leader.xAvatar);
  if (!hasSocial && !hasPhoto) return 0;
  if (!hasSocial) return 1;
  if (!hasPhoto) return 2;
  if (!hasUrl(leader.x)) return 3;
  if (!hasUrl(company.x)) return 4;
  return 5;
}

function evidence(profile, company, candidate) {
  const display = normalize(profile?.name);
  const bio = normalize(profile?.bio);
  const personTokens = tokens(company.leader?.name || "");
  const companyTokens = tokens(company.name);
  const personNameMatch = personTokens.length >= 2 && personTokens.every((token) => display.includes(token));
  const companyNameMatch = companyTokens.length > 0 && companyTokens.some((token) => display.includes(token) || bio.includes(token));
  const websiteMatch = Boolean(registrableHost(profile?.website || "") && registrableHost(company.website || "") && registrableHost(profile?.website || "") === registrableHost(company.website || ""));
  const officialClaim = /\bofficial\b/.test(bio);
  const reasons = [];
  let accepted = false;
  let confidence = "Low";
  if (candidate.scope === "leader") {
    if (personNameMatch) reasons.push("leader full name matches X display name");
    if (companyNameMatch) reasons.push("current organisation appears in X name or bio");
    if (websiteMatch) reasons.push("X profile website matches official company domain");
    accepted = Boolean(profile && personNameMatch && (companyNameMatch || websiteMatch));
    confidence = accepted && companyNameMatch && websiteMatch ? "High" : accepted ? "Medium" : "Low";
  } else {
    if (companyNameMatch) reasons.push("company identity appears in X name or bio");
    if (websiteMatch) reasons.push("X profile website matches official company domain");
    if (officialClaim) reasons.push("X bio self-identifies as official");
    accepted = Boolean(profile && companyNameMatch && (websiteMatch || officialClaim));
    confidence = accepted && websiteMatch ? "High" : accepted ? "Medium" : "Low";
  }
  return { accepted, confidence, reasons, personNameMatch, companyNameMatch, websiteMatch };
}

async function validateCandidate(scraper, company, candidate) {
  try {
    const profile = await scraper.getProfile(candidate.handle);
    return { ...candidate, validationStatus: "found", validationError: null, profile, ...evidence(profile, company, candidate) };
  } catch (error) {
    return { ...candidate, validationStatus: "not_found_or_unavailable", validationError: String(error?.message || error), profile: null, accepted: false, confidence: "Low", reasons: [] };
  }
}

async function main() {
  const profileData = JSON.parse(await fs.readFile(PROFILES, "utf8"));
  const research = JSON.parse(await fs.readFile(RESEARCH, "utf8"));
  const all = [...(profileData.companies || [])].sort((a, b) => priority(a) - priority(b) || a.name.localeCompare(b.name));
  const companies = LIMIT ? all.slice(0, LIMIT) : all;
  const recordById = new Map((research.records || []).map((record) => [record.companyId, record]));
  const tasks = [];
  for (const company of companies) {
    const existingRecord = recordById.get(company.id) || { companyId: company.id, companyName: company.name, candidates: [], accepted: { company: null, leader: null } };
    if (!existingRecord.accepted?.leader && company.leader?.name && !/^not publicly/i.test(company.leader.name)) {
      tasks.push({ company, record: existingRecord, scope: "leader", query: `site:x.com "${company.leader.name}" "${company.name}"` });
    }
    if (!existingRecord.accepted?.company) {
      tasks.push({ company, record: existingRecord, scope: "company", query: `site:x.com "${company.name}" official` });
    }
    recordById.set(company.id, existingRecord);
  }

  let discovered = 0;
  const discoveryResults = await mapLimit(tasks, SEARCH_CONCURRENCY, async (task) => {
    const search = await exactSearchCandidates(task.query);
    discovered += 1;
    if (discovered % 25 === 0 || discovered === tasks.length) process.stderr.write(`searched ${discovered}/${tasks.length}\n`);
    return { ...task, search };
  });

  const validationTasks = [];
  for (const result of discoveryResults) {
    if (!result?.search) continue;
    const existingUrls = new Set((result.record.candidates || []).map((item) => clean(item.url).toLowerCase()));
    for (const url of result.search.urls) {
      if (existingUrls.has(url.toLowerCase())) continue;
      validationTasks.push({
        company: result.company,
        record: result.record,
        candidate: {
          scope: result.scope,
          url,
          handle: xHandle(url),
          sourceType: "exact_public_web_search",
          sourceUrl: result.search.sourceUrl,
          discoveryStatus: result.search.status,
        },
      });
    }
  }

  const scraper = new Scraper();
  let validated = 0;
  const validatedResults = await mapLimit(validationTasks, PROFILE_CONCURRENCY, async (task) => {
    const candidate = await validateCandidate(scraper, task.company, task.candidate);
    validated += 1;
    if (validated % 25 === 0 || validated === validationTasks.length) process.stderr.write(`validated ${validated}/${validationTasks.length}\n`);
    return { ...task, candidate };
  });

  for (const result of validatedResults) {
    if (!result?.candidate) continue;
    result.record.candidates ||= [];
    result.record.candidates.push(result.candidate);
  }
  const rank = { High: 3, Medium: 2, Low: 1 };
  for (const company of companies) {
    const record = recordById.get(company.id);
    const best = (scope) => (record.candidates || []).filter((item) => item.scope === scope && item.accepted)
      .sort((a, b) => (rank[b.confidence] - rank[a.confidence]) || (b.reasons?.length || 0) - (a.reasons?.length || 0))[0] || null;
    record.accepted = { company: best("company"), leader: best("leader") };
  }

  research.records = (profileData.companies || []).map((company) => recordById.get(company.id)).filter(Boolean);
  const uniqueCandidates = new Map();
  for (const record of research.records) for (const candidate of record.candidates || []) uniqueCandidates.set(clean(candidate.url).toLowerCase(), candidate);
  research.summary = {
    ...(research.summary || {}),
    generatedAt: new Date().toISOString(),
    companiesProcessed: research.records.length,
    uniqueCandidatesValidated: uniqueCandidates.size,
    companyAccountsAccepted: research.records.filter((record) => record.accepted?.company).length,
    leaderAccountsAccepted: research.records.filter((record) => record.accepted?.leader).length,
    ambiguousOrRejectedCandidates: research.records.reduce((sum, record) => sum + (record.candidates || []).filter((candidate) => !candidate.accepted).length, 0),
    method: "Playwright/first-party baseline + exact public web discovery + Wikidata identity + XActions public-profile validation",
    priorityMethod: "missing leader social+photo, then missing social, missing photo, missing leader X, missing company X",
    prioritySearchesThisRun: tasks.length,
    priorityCandidatesValidatedThisRun: validationTasks.length,
  };
  await fs.mkdir(path.dirname(OUTPUT), { recursive: true });
  await fs.writeFile(OUTPUT, JSON.stringify(research, null, 2) + "\n");
  console.log(JSON.stringify(research.summary, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });

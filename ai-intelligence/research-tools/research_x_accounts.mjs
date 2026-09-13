#!/usr/bin/env node
/**
 * Discover X accounts from first-party pages with Playwright and validate
 * every candidate through XActions' public profile reader.
 *
 * This script is deliberately read-only. It never logs in to X and never
 * posts, follows, likes, or otherwise mutates an account.
 */
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { Scraper } from "xactions";

const ROOT = path.resolve(process.cwd(), "../..");
const INPUT = process.argv[2] || path.join(ROOT, "ai-intelligence/data/company-profiles.json");
const OUTPUT = process.argv[3] || path.join(ROOT, "output/ai-intelligence-database/x-account-research.json");
const LIMIT = Number(process.env.X_RESEARCH_LIMIT || 0);
const SITE_CONCURRENCY = Math.max(1, Number(process.env.X_SITE_CONCURRENCY || 6));
const PROFILE_CONCURRENCY = Math.max(1, Number(process.env.X_PROFILE_CONCURRENCY || 2));
const NAV_TIMEOUT_MS = Math.max(3000, Number(process.env.X_NAV_TIMEOUT_MS || 10000));

const rejectedHandles = new Set([
  "home", "share", "intent", "search", "explore", "hashtag", "i", "settings",
  "messages", "notifications", "compose", "login", "signup", "tos", "privacy",
]);

function clean(value) { return typeof value === "string" ? value.trim() : ""; }
function normalize(value) {
  return clean(value).toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ").trim();
}
function tokens(value) {
  return normalize(value).split(/\s+/).filter((token) => token.length >= 3 && !new Set([
    "the", "and", "inc", "ltd", "llc", "corp", "corporation", "company", "group",
    "holdings", "technologies", "technology", "international", "global", "official",
  ]).has(token));
}
function host(url) {
  try { return new URL(url).hostname.toLowerCase().replace(/^www\./, ""); } catch { return ""; }
}
function registrableHost(url) {
  const hostname = host(url);
  const parts = hostname.split(".");
  return parts.length > 2 ? parts.slice(-2).join(".") : hostname;
}
function canonicalXUrl(value) {
  try {
    const parsed = new URL(value);
    const hostname = parsed.hostname.toLowerCase().replace(/^www\./, "");
    if (!["x.com", "twitter.com", "mobile.twitter.com"].includes(hostname)) return "";
    const segment = parsed.pathname.split("/").filter(Boolean)[0] || "";
    if (!/^[A-Za-z0-9_]{1,15}$/.test(segment) || rejectedHandles.has(segment.toLowerCase())) return "";
    return `https://x.com/${segment}`;
  } catch { return ""; }
}
function xHandle(value) { const url = canonicalXUrl(value); return url ? new URL(url).pathname.slice(1) : ""; }

function existingCandidates(company) {
  const out = [];
  const push = (scope, url, sourceType, sourceUrl) => {
    const canonical = canonicalXUrl(url);
    if (canonical) out.push({ scope, url: canonical, sourceType, sourceUrl: sourceUrl || canonical });
  };
  push("company", company.x, "existing_company_record", company.verification?.companySource);
  push("company", company.xUrl, "existing_company_record", company.verification?.companySource);
  const leader = company.leader || {};
  push("leader", leader.x, "existing_leadership_record", leader.socialSource || leader.roleSource);
  push("leader", leader.xUrl, "existing_leadership_record", leader.socialSource || leader.roleSource);
  push("leader", leader.social, "existing_leadership_record", leader.socialSource || leader.roleSource);
  push("leader", leader.linkedin, "misfiled_leadership_record", leader.socialSource || leader.roleSource);
  return out;
}

async function extractXLinks(page, targetUrl) {
  if (!/^https?:\/\//i.test(clean(targetUrl))) return { finalUrl: "", links: [], status: "no_url" };
  try {
    const response = await page.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: NAV_TIMEOUT_MS });
    const result = await page.evaluate(() => {
      const urls = new Set();
      const add = (value) => { if (typeof value === "string" && /(?:x\.com|twitter\.com)\//i.test(value)) urls.add(value); };
      document.querySelectorAll("a[href]").forEach((link) => add(link.href));
      document.querySelectorAll('script[type="application/ld+json"]').forEach((script) => {
        try {
          const data = JSON.parse(script.textContent || "null");
          const walk = (value) => {
            if (typeof value === "string") add(value);
            else if (Array.isArray(value)) value.forEach(walk);
            else if (value && typeof value === "object") Object.values(value).forEach(walk);
          };
          walk(data);
        } catch {}
      });
      return [...urls];
    });
    const links = [...new Set(result.map(canonicalXUrl).filter(Boolean))];
    return { finalUrl: page.url(), links, status: response ? String(response.status()) : "loaded" };
  } catch (error) {
    return { finalUrl: page.url(), links: [], status: `error:${String(error?.message || error).slice(0, 160)}` };
  }
}

async function discoverOne(browser, company) {
  const context = await browser.newContext({
    userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36",
    locale: "en-US",
    javaScriptEnabled: true,
  });
  const page = await context.newPage();
  await page.route(/\.(?:png|jpe?g|gif|webp|svg|mp4|webm|woff2?|ttf)(?:\?.*)?$/i, (route) => route.abort());
  const candidates = existingCandidates(company);
  const companyScan = await extractXLinks(page, company.website);
  companyScan.links.forEach((url) => candidates.push({
    scope: "company", url, sourceType: "official_company_website", sourceUrl: companyScan.finalUrl || company.website,
  }));

  const leader = company.leader || {};
  const officialProfile = clean(leader.officialProfile);
  let leaderScan = { finalUrl: "", links: [], status: "not_scanned" };
  if (officialProfile && !/(linkedin\.com|wikidata\.org|wikipedia\.org|crunchbase\.com)/i.test(officialProfile)) {
    leaderScan = await extractXLinks(page, officialProfile);
    leaderScan.links.forEach((url) => candidates.push({
      scope: "leader", url, sourceType: "official_leadership_profile", sourceUrl: leaderScan.finalUrl || officialProfile,
    }));
  }
  await context.close();
  const unique = new Map();
  for (const candidate of candidates) {
    const key = `${candidate.scope}:${candidate.url.toLowerCase()}`;
    if (!unique.has(key) || candidate.sourceType.startsWith("official_")) unique.set(key, candidate);
  }
  return { companyId: company.id, companyName: company.name, companyScan, leaderScan, candidates: [...unique.values()] };
}

async function wikidataCandidate(company) {
  const leader = company.leader || {};
  const leaderName = clean(leader.name);
  if (!leaderName || /^not publicly/i.test(leaderName)) return null;
  try {
    let qid = "";
    const profile = clean(leader.officialProfile);
    const match = profile.match(/wikidata\.org\/wiki\/(Q\d+)/i);
    if (match) qid = match[1].toUpperCase();
    if (!qid) {
      const searchUrl = new URL("https://www.wikidata.org/w/api.php");
      Object.entries({ action: "wbsearchentities", format: "json", language: "en", uselang: "en", limit: "5", search: leaderName }).forEach(([key, value]) => searchUrl.searchParams.set(key, value));
      const response = await fetch(searchUrl, { headers: { "user-agent": "AI-map-research/1.0 (public identity verification)" } });
      const data = await response.json();
      const leaderTokens = tokens(leaderName);
      const companyTokens = tokens(company.name);
      const candidates = (data.search || []).filter((item) => {
        const label = normalize(item.label);
        const description = normalize(item.description);
        return leaderTokens.every((token) => label.includes(token)) &&
          (/(business|entrepreneur|executive|chief|founder|engineer|scientist|investor|manager|chair|developer)/.test(description) || companyTokens.some((token) => description.includes(token)));
      });
      if (candidates.length) qid = candidates[0].id;
    }
    if (!/^Q\d+$/.test(qid)) return null;
    const entityResponse = await fetch(`https://www.wikidata.org/wiki/Special:EntityData/${qid}.json`, { headers: { "user-agent": "AI-map-research/1.0 (public identity verification)" } });
    const entity = (await entityResponse.json()).entities?.[qid];
    const claims = entity?.claims || {};
    const isHuman = (claims.P31 || []).some((item) => item?.mainsnak?.datavalue?.value?.id === "Q5");
    const handle = claims.P2002?.[0]?.mainsnak?.datavalue?.value;
    if (!isHuman || !handle) return null;
    const url = canonicalXUrl(`https://x.com/${String(handle).replace(/^@/, "")}`);
    return url ? { scope: "leader", url, sourceType: "wikidata_person_claim", sourceUrl: `https://www.wikidata.org/wiki/${qid}` } : null;
  } catch { return null; }
}

function profileEvidence(profile, company, candidate) {
  const display = normalize(profile?.name);
  const bio = normalize(profile?.bio);
  const profileHost = registrableHost(profile?.website || "");
  const companyHost = registrableHost(company.website || "");
  const personTokens = tokens(company.leader?.name || "");
  const companyTokens = tokens(company.name);
  const personNameMatch = personTokens.length >= 2 && personTokens.every((token) => display.includes(token));
  const companyNameMatch = companyTokens.length > 0 && companyTokens.some((token) => display.includes(token) || bio.includes(token));
  const websiteMatch = Boolean(profileHost && companyHost && profileHost === companyHost);
  const officialClaim = /\bofficial\b/.test(bio);
  const sourceIsFirstParty = candidate.sourceType === "official_company_website" || candidate.sourceType === "official_leadership_profile";
  const officialQid = clean(company.leader?.officialProfile || "").match(/wikidata\.org\/wiki\/(Q\d+)/i)?.[1]?.toUpperCase() || "";
  const candidateQid = clean(candidate.sourceUrl).match(/wikidata\.org\/wiki\/(Q\d+)/i)?.[1]?.toUpperCase() || "";
  const officialQidMatch = Boolean(officialQid && candidateQid && officialQid === candidateQid);
  let accepted = false;
  let confidence = "Low";
  const reasons = [];
  if (candidate.scope === "company") {
    if (sourceIsFirstParty) reasons.push("linked from official company website");
    if (websiteMatch) reasons.push("X profile website matches official domain");
    if (companyNameMatch) reasons.push("company identity matches profile name or bio");
    if (officialClaim) reasons.push("profile self-identifies as official");
    accepted = Boolean(profile && sourceIsFirstParty && (websiteMatch || companyNameMatch || officialClaim));
    confidence = accepted && websiteMatch && companyNameMatch ? "High" : accepted ? "Medium" : "Low";
  } else {
    if (sourceIsFirstParty) reasons.push("linked from official leadership profile");
    if (candidate.sourceType === "wikidata_person_claim") reasons.push("Wikidata X claim for matched human entity");
    if (personNameMatch) reasons.push("leader name matches X display name");
    if (companyNameMatch) reasons.push("company context appears in profile");
    accepted = Boolean(profile && personNameMatch && (sourceIsFirstParty || companyNameMatch || officialQidMatch));
    confidence = accepted && (sourceIsFirstParty || companyNameMatch) ? "High" : accepted ? "Medium" : "Low";
  }
  return { accepted, confidence, reasons, personNameMatch, companyNameMatch, websiteMatch };
}

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

async function main() {
  const data = JSON.parse(await fs.readFile(INPUT, "utf8"));
  const companies = (data.companies || []).slice(0, LIMIT || undefined);
  const browser = await chromium.launch({ headless: true });
  let finished = 0;
  const discoveries = await mapLimit(companies, SITE_CONCURRENCY, async (company) => {
    const result = await discoverOne(browser, company);
    const wikidata = await wikidataCandidate(company);
    if (wikidata && !result.candidates.some((candidate) => candidate.scope === "leader" && candidate.url.toLowerCase() === wikidata.url.toLowerCase())) result.candidates.push(wikidata);
    finished += 1;
    if (finished % 25 === 0 || finished === companies.length) process.stderr.write(`discovered ${finished}/${companies.length}\n`);
    return result;
  });
  await browser.close();

  const companyById = new Map(companies.map((company) => [company.id, company]));
  const candidateMap = new Map();
  for (const discovery of discoveries) {
    for (const candidate of discovery.candidates || []) candidateMap.set(candidate.url.toLowerCase(), candidate.url);
  }
  const urls = [...candidateMap.values()];
  const scraper = new Scraper();
  let validated = 0;
  const profiles = await mapLimit(urls, PROFILE_CONCURRENCY, async (url) => {
    const handle = xHandle(url);
    try {
      const profile = await scraper.getProfile(handle);
      validated += 1;
      if (validated % 25 === 0 || validated === urls.length) process.stderr.write(`validated ${validated}/${urls.length}\n`);
      return [url.toLowerCase(), { status: "found", profile }];
    } catch (error) {
      validated += 1;
      return [url.toLowerCase(), { status: "not_found_or_unavailable", error: String(error?.message || error) }];
    }
  });
  const profileMap = new Map(profiles);

  const records = discoveries.map((discovery) => {
    const company = companyById.get(discovery.companyId);
    const evaluated = (discovery.candidates || []).map((candidate) => {
      const result = profileMap.get(candidate.url.toLowerCase()) || {};
      const evidence = result.profile ? profileEvidence(result.profile, company, candidate) : { accepted: false, confidence: "Low", reasons: [] };
      return { ...candidate, handle: xHandle(candidate.url), validationStatus: result.status || "not_checked", validationError: result.error || null, profile: result.profile || null, ...evidence };
    });
    const best = (scope) => evaluated.filter((item) => item.scope === scope && item.accepted).sort((a, b) => {
      const rank = { High: 3, Medium: 2, Low: 1 };
      return (rank[b.confidence] - rank[a.confidence]) || b.reasons.length - a.reasons.length;
    })[0] || null;
    return { ...discovery, candidates: evaluated, accepted: { company: best("company"), leader: best("leader") } };
  });

  const summary = {
    generatedAt: new Date().toISOString(),
    companiesProcessed: records.length,
    uniqueCandidatesValidated: urls.length,
    companyAccountsAccepted: records.filter((record) => record.accepted.company).length,
    leaderAccountsAccepted: records.filter((record) => record.accepted.leader).length,
    ambiguousOrRejectedCandidates: records.reduce((sum, record) => sum + record.candidates.filter((candidate) => !candidate.accepted).length, 0),
    method: "Playwright first-party link discovery + Wikidata person claims + XActions public-profile validation",
  };
  await fs.mkdir(path.dirname(OUTPUT), { recursive: true });
  await fs.writeFile(OUTPUT, JSON.stringify({ summary, records }, null, 2) + "\n");
  console.log(JSON.stringify(summary, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });

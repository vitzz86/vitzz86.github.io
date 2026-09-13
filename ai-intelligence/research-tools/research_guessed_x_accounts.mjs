#!/usr/bin/env node
/** Validate conservative name-derived X handles for unresolved leaders. */
import fs from "node:fs/promises";
import path from "node:path";
import { Scraper } from "xactions";

const ROOT = path.resolve(process.cwd(), "../..");
const PROFILES = process.argv[2] || path.join(ROOT, "ai-intelligence/data/company-profiles.json");
const RESEARCH = process.argv[3] || path.join(ROOT, "output/ai-intelligence-database/x-account-research.json");
const OUTPUT = process.argv[4] || RESEARCH;
const CONCURRENCY = Math.max(1, Number(process.env.X_GUESS_CONCURRENCY || 3));
const LIMIT = Math.max(0, Number(process.env.X_GUESS_LIMIT || 0));
const ignored = new Set(["the", "and", "inc", "ltd", "llc", "corp", "company", "group", "holdings", "technologies", "technology", "international", "global", "chief", "executive", "officer", "president", "founder", "chair", "ceo"]);

const clean = (value) => typeof value === "string" ? value.trim() : "";
const normalize = (value) => clean(value).toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
const tokens = (value) => normalize(value).split(/\s+/).filter((token) => token.length >= 2 && !ignored.has(token));
const hasUrl = (value) => /^https?:\/\//i.test(clean(value));
function host(value) { try { return new URL(value).hostname.toLowerCase().replace(/^www\./, ""); } catch { return ""; } }
function registrableHost(value) { const parts = host(value).split("."); return parts.length > 2 ? parts.slice(-2).join(".") : parts.join("."); }
function linkedinSlug(value) { try { return new URL(value).pathname.split("/in/")[1]?.split("/")[0] || ""; } catch { return ""; } }

function handlesFor(company) {
  const leader = company.leader || {};
  const parts = tokens(leader.name || "");
  if (parts.length < 2) return [];
  const first = parts[0], last = parts.at(-1), middle = parts.slice(1, -1).join("");
  const candidates = [
    linkedinSlug(leader.linkedin),
    `${first}${middle}${last}`,
    `${first}${last}`,
    `${first[0]}${last}`,
    `${first}${last[0]}`,
    `${last}${first}`,
  ].map((value) => normalize(value).replaceAll(" ", "")).filter((value) => /^[a-z0-9_]{1,15}$/.test(value));
  return [...new Set(candidates)].slice(0, 5);
}

function priority(company) {
  const leader = company.leader || {};
  const social = hasUrl(leader.linkedin) || hasUrl(leader.x);
  const photo = hasUrl(leader.photo) || hasUrl(leader.xAvatar);
  return !social && !photo ? 0 : !social ? 1 : !photo ? 2 : 3;
}

function evidence(profile, company) {
  const display = normalize(profile?.name);
  const bio = normalize(profile?.bio);
  const personTokens = tokens(company.leader?.name || "");
  const companyTokens = tokens(company.name);
  const personNameMatch = personTokens.length >= 2 && personTokens.every((token) => display.includes(token));
  const companyNameMatch = companyTokens.length > 0 && companyTokens.some((token) => display.includes(token) || bio.includes(token));
  const websiteMatch = Boolean(registrableHost(profile?.website || "") && registrableHost(company.website || "") && registrableHost(profile?.website || "") === registrableHost(company.website || ""));
  const accepted = Boolean(profile && personNameMatch && (companyNameMatch || websiteMatch));
  return {
    accepted,
    confidence: accepted && companyNameMatch && websiteMatch ? "High" : accepted ? "Medium" : "Low",
    reasons: [personNameMatch ? "leader full name matches X display name" : "", companyNameMatch ? "current organisation appears in X name or bio" : "", websiteMatch ? "X profile website matches official company domain" : ""].filter(Boolean),
    personNameMatch,
    companyNameMatch,
    websiteMatch,
  };
}

async function mapLimit(items, limit, callback) {
  let cursor = 0;
  async function worker() {
    while (true) {
      const index = cursor++;
      if (index >= items.length) return;
      await callback(items[index], index);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
}

const profiles = JSON.parse(await fs.readFile(PROFILES, "utf8"));
const research = JSON.parse(await fs.readFile(RESEARCH, "utf8"));
const recordById = new Map((research.records || []).map((record) => [record.companyId, record]));
let companies = (profiles.companies || []).filter((company) => !hasUrl(company.leader?.x) && !recordById.get(company.id)?.accepted?.leader && handlesFor(company).length);
companies.sort((a, b) => priority(a) - priority(b) || a.name.localeCompare(b.name));
if (LIMIT) companies = companies.slice(0, LIMIT);
const scraper = new Scraper();
let finished = 0, accepted = 0, attempted = 0;

await mapLimit(companies, CONCURRENCY, async (company) => {
  const record = recordById.get(company.id) || { companyId: company.id, companyName: company.name, candidates: [], accepted: { company: null, leader: null } };
  const known = new Set((record.candidates || []).map((candidate) => clean(candidate.url).toLowerCase()));
  for (const handle of handlesFor(company)) {
    const url = `https://x.com/${handle}`;
    if (known.has(url.toLowerCase())) continue;
    attempted += 1;
    let candidate;
    try {
      const profile = await scraper.getProfile(handle);
      candidate = { scope: "leader", url, handle: profile.username || handle, sourceType: "name_derived_candidate", sourceUrl: clean(company.leader?.roleSource) || clean(company.leader?.officialProfile), validationStatus: "found", validationError: null, profile, ...evidence(profile, company) };
    } catch (error) {
      candidate = { scope: "leader", url, handle, sourceType: "name_derived_candidate", sourceUrl: clean(company.leader?.roleSource) || clean(company.leader?.officialProfile), validationStatus: "not_found_or_unavailable", validationError: String(error?.message || error), profile: null, accepted: false, confidence: "Low", reasons: [] };
    }
    record.candidates ||= [];
    record.candidates.push(candidate);
    known.add(url.toLowerCase());
    if (candidate.accepted) {
      record.accepted ||= {};
      record.accepted.leader = candidate;
      accepted += 1;
      break;
    }
  }
  recordById.set(company.id, record);
  finished += 1;
  if (finished % 20 === 0 || finished === companies.length) {
    process.stderr.write(`leaders ${finished}/${companies.length}; accepted ${accepted}; profile attempts ${attempted}\n`);
    research.records = (profiles.companies || []).map((item) => recordById.get(item.id)).filter(Boolean);
    await fs.writeFile(OUTPUT, JSON.stringify(research, null, 2) + "\n");
  }
});

research.records = (profiles.companies || []).map((company) => recordById.get(company.id)).filter(Boolean);
research.summary = {
  ...(research.summary || {}),
  generatedAt: new Date().toISOString(),
  companiesProcessed: research.records.length,
  companyAccountsAccepted: research.records.filter((record) => record.accepted?.company).length,
  leaderAccountsAccepted: research.records.filter((record) => record.accepted?.leader).length,
  guessedLeaderProfilesProcessed: companies.length,
  guessedLeaderProfileAttempts: attempted,
  guessedLeaderProfilesAccepted: accepted,
  method: "First-party/Wikidata/exact public discovery plus XActions public-profile validation; conservative name-derived XActions fallback",
};
await fs.writeFile(OUTPUT, JSON.stringify(research, null, 2) + "\n");
console.log(JSON.stringify(research.summary, null, 2));

#!/usr/bin/env node
/** Retry throttled XActions profile reads using isolated guest sessions. */
import fs from "node:fs/promises";
import path from "node:path";
import { Scraper } from "xactions";

const ROOT = path.resolve(process.cwd(), "../..");
const PROFILES = process.argv[2] || path.join(ROOT, "ai-intelligence/data/company-profiles.json");
const RESEARCH = process.argv[3] || path.join(ROOT, "output/ai-intelligence-database/x-account-research.json");
const CONCURRENCY = Math.max(1, Number(process.env.X_RETRY_CONCURRENCY || 4));

const clean = (value) => typeof value === "string" ? value.trim() : "";
const normalize = (value) => clean(value).toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
const ignored = new Set(["the", "and", "inc", "ltd", "llc", "corp", "corporation", "company", "group", "holdings", "technologies", "technology", "international", "global", "official"]);
const tokens = (value) => normalize(value).split(/\s+/).filter((token) => token.length >= 3 && !ignored.has(token));
function registrableHost(value) {
  try {
    const parts = new URL(value).hostname.toLowerCase().replace(/^www\./, "").split(".");
    return parts.length > 2 ? parts.slice(-2).join(".") : parts.join(".");
  } catch { return ""; }
}
function evidence(profile, company, candidate) {
  const display = normalize(profile?.name), bio = normalize(profile?.bio);
  const profileHost = registrableHost(profile?.website || ""), companyHost = registrableHost(company.website || "");
  const personTokens = tokens(company.leader?.name || ""), companyTokens = tokens(company.name);
  const personNameMatch = personTokens.length >= 2 && personTokens.every((token) => display.includes(token));
  const companyNameMatch = companyTokens.length > 0 && companyTokens.some((token) => display.includes(token) || bio.includes(token));
  const websiteMatch = Boolean(profileHost && companyHost && profileHost === companyHost);
  const officialClaim = /\bofficial\b/.test(bio);
  const sourceIsFirstParty = candidate.sourceType === "official_company_website" || candidate.sourceType === "official_leadership_profile";
  const officialQid = clean(company.leader?.officialProfile || "").match(/wikidata\.org\/wiki\/(Q\d+)/i)?.[1]?.toUpperCase() || "";
  const candidateQid = clean(candidate.sourceUrl).match(/wikidata\.org\/wiki\/(Q\d+)/i)?.[1]?.toUpperCase() || "";
  const officialQidMatch = Boolean(officialQid && candidateQid && officialQid === candidateQid);
  const reasons = [];
  let accepted = false, confidence = "Low";
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

const profilesData = JSON.parse(await fs.readFile(PROFILES, "utf8"));
const research = JSON.parse(await fs.readFile(RESEARCH, "utf8"));
const companyById = new Map((profilesData.companies || []).map((company) => [company.id, company]));
const candidates = [...new Map(research.records.flatMap((record) => record.candidates || []).filter((candidate) => candidate.validationStatus !== "found").map((candidate) => [candidate.url.toLowerCase(), candidate])).values()];
let finished = 0;
const resultByUrl = new Map();
await mapLimit(candidates, CONCURRENCY, async (candidate) => {
  try {
    const profile = await new Scraper().getProfile(candidate.handle);
    resultByUrl.set(candidate.url.toLowerCase(), { status: "found", profile });
  } catch (error) {
    resultByUrl.set(candidate.url.toLowerCase(), { status: "not_found_or_unavailable", error: String(error?.message || error) });
  }
  finished += 1;
  if (finished % 25 === 0 || finished === candidates.length) process.stderr.write(`retried ${finished}/${candidates.length}\n`);
});

for (const record of research.records) {
  const company = companyById.get(record.companyId);
  for (const candidate of record.candidates || []) {
    const result = resultByUrl.get(candidate.url.toLowerCase());
    if (result) {
      candidate.validationStatus = result.status;
      candidate.validationError = result.error || null;
      candidate.profile = result.profile || null;
    }
    Object.assign(candidate, candidate.profile ? evidence(candidate.profile, company, candidate) : { accepted: false, confidence: "Low", reasons: [], personNameMatch: false, companyNameMatch: false, websiteMatch: false });
  }
  const rank = { High: 3, Medium: 2, Low: 1 };
  const best = (scope) => (record.candidates || []).filter((candidate) => candidate.scope === scope && candidate.accepted).sort((a, b) => (rank[b.confidence] - rank[a.confidence]) || b.reasons.length - a.reasons.length)[0] || null;
  record.accepted = { company: best("company"), leader: best("leader") };
}
research.summary.generatedAt = new Date().toISOString();
research.summary.companyAccountsAccepted = research.records.filter((record) => record.accepted.company).length;
research.summary.leaderAccountsAccepted = research.records.filter((record) => record.accepted.leader).length;
research.summary.ambiguousOrRejectedCandidates = research.records.reduce((sum, record) => sum + record.candidates.filter((candidate) => !candidate.accepted).length, 0);
research.summary.validatedProfilesFound = new Set(research.records.flatMap((record) => record.candidates).filter((candidate) => candidate.validationStatus === "found").map((candidate) => candidate.url.toLowerCase())).size;
research.summary.validationFailuresRemaining = new Set(research.records.flatMap((record) => record.candidates).filter((candidate) => candidate.validationStatus !== "found").map((candidate) => candidate.url.toLowerCase())).size;
await fs.writeFile(RESEARCH, JSON.stringify(research, null, 2) + "\n");
console.log(JSON.stringify(research.summary, null, 2));

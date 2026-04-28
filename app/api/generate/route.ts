import Anthropic from "@anthropic-ai/sdk";
import { NextRequest, NextResponse } from "next/server";
import { DispensaryData } from "@/app/types";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const SYSTEM_PROMPT = `You are a business investigator first, revenue strategist second, copywriter third. Before you write a single word, you study the dispensary like a consultant about to walk into their store. You look for TWO things: (1) the REAL problem — the specific, concrete vulnerability in their payment setup, and (2) the REVENUE ANGLE — how much money they're leaving on the table by not having optimized ATM + payment infrastructure.
Your ONLY goal is to get a reply. Not a sale. Not a meeting. A reply.
You will output THREE things for each dispensary:
A personalized cold email (Email 1)
Two follow-up emails (Email 2 at Day 3, Email 3 at Day 7)
A 3-message SMS sequence

CONTEXT ABOUT US:
We are Paytree, an ISO-certified payment processor with 20 years of experience. We provide fully managed ATM placements for cannabis dispensaries — zero upfront cost, full maintenance, cash loading handled, and the dispensary owner earns 70–75% of all surcharge revenue as passive monthly income. Our ATMs also support NFC (Apple Pay, Google Pay, tap-to-pay). We are not a bank. We are infrastructure. We've already helped dispensaries in Oakland and San Francisco stabilize their payment operations and add new revenue streams.
The irresistible offer: We install and fully manage an ATM inside your dispensary at no cost. You receive 70–75% of all surcharge revenue, paid monthly. We handle installation, cash loading, maintenance, and uptime monitoring. You simply earn passive income from foot traffic you already have.

PHASE 1: INVESTIGATE (do this BEFORE writing)
Analyze every field to find the most specific business problem AND the strongest revenue angle. Think like a consultant doing a 60-second audit.

Problem signals (pick ONE):
License signals:
- License expiring within 6 months → they may be distracted by renewal, not watching infrastructure
- Recently issued license → new operation, probably still figuring out payment setup
- Provisional license → not fully established, higher risk of processor instability
- Expired/Revoked → may have rebranded, moved, or know other operators
Business structure signals:
- Multiple owners (4+) → decision-making is slow, payment issues probably get ignored longer
- Equity retailer tag → often underfunded, may be using cheap or unreliable ATM providers
- Microbusiness with retail + distribution → complex cash flow, more payment touchpoints that can break
- DBA name differs significantly from legal name → rebranded, possibly after a disruption
Location signals:
- High foot traffic areas (Mission District, Fruitvale, Downtown Oakland, Hollywood, etc.) → ATMs get hammered
- Multiple dispensaries at the same address → shared space, possibly shared (and overloaded) infrastructure
- Lower foot traffic areas → high cash dependency, ATM downtime hits harder
Timing signals:
- Licensed in 2019–2021 → original wave, equipment is now 5–7 years old, hardware failures incoming
- Licensed in 2023–2026 → newer operator, may not have payment infrastructure dialed in yet
Revenue signals (pick ONE):
- High foot traffic area → 500–800 ATM transactions/month potential = $1,500–$3,600/month owner revenue
- Adult-Use designation → higher average ticket, more impulse buys, ATM critical for cash customers
- Microbusiness with retail → multiple revenue streams but likely not capturing ATM income
- Multiple owners → likely tracking every dollar, would notice a new $1,000+/month passive income stream
- Newer operation → hasn't set up revenue-generating ATM yet, leaving money on the table from day one
- Aging ATM (2019–2021 setup) → current ATM may be revenue-losing (downtime = lost transactions)

LOGIC BASED ON LICENSE STATUS:
IF ACTIVE: Use the full structure below for Email 1 (5-part). Generate Email 2 (social proof follow-up) and Email 3 (soft close). Generate 3-message SMS sequence. Anchor everything in the specific problem AND revenue opportunity identified.
IF NOT ACTIVE (Expired, Revoked, Canceled, Surrendered): Use abbreviated Email 1: greeting → 1 short paragraph → soft ask → sign-off. Skip Email 2, Email 3, and SMS sequence. Do NOT assume they're still operating. Ask if they've relaunched under a new name, or if they know someone active who could use help. Keep it under 60 words body.

EMAIL 1 STRUCTURE (ACTIVE licenses — 5 parts):
1. GREETING (own line) - Names available: Hi [FIRST_NAMES], / No names: Hi [BUSINESS_DBA] team,
2. PROBLEM-AWARE OPENING (1–2 sentences) - Must reference their city and a detail that signals you actually looked at their business
3. CURIOSITY LINE (1 sentence) - The hook — specific enough to feel like insider knowledge, vague enough they HAVE to reply
4. BRIDGE (2–3 sentences) - Connect to Paytree without explaining how anything works. Hint at revenue. Include "NFC (Apple Pay, Google Pay, tap-to-pay)". Mention "20 years". Include "We've already helped a few dispensaries in your area".
5. CTA (1 question) - Combines problem-awareness WITH revenue curiosity

SIGN-OFF (exact format, never change):
Your Friend,
Lauren Coleman
Paytree

SUBJECT LINE (Email 1): Under 6 words. Must reference the SPECIFIC problem or signal identified. Include the business name OR city.

EMAIL 2 — Social Proof Follow-Up (Day 3):
Subject: Re: [Email 1 subject line]
Structure: Greeting → Quick reference (1 sentence referencing day) → Revenue hook with data point → Soft CTA → Sign-off
Under 60 words body. Do NOT repeat the curiosity line from Email 1. Tone: lighter, shorter, more casual.

EMAIL 3 — Soft Close (Day 7):
Subject: Should I close your file?
Structure: Greeting → Acknowledgment → Loss aversion hook → Easy reply CTA ("reply 'ATM'") → Sign-off
Under 70 words body. No pressure, no guilt — clean and human.

SMS SEQUENCE (3 messages):
SMS 1 (Day 1): Customize revenue range based on location/foot traffic. Under 160 chars if possible.
SMS 2 (Day 4): Ask if they're the right person for ATM/payment decisions.
SMS 3 (Day 8): Last try — ask to close out or want an estimate.

STYLE CONSTRAINTS (apply to ALL outputs):
- Email 1: 75–110 words body (excluding greeting and sign-off)
- Email 2: under 60 words body
- Email 3: under 70 words body
- F-pattern scannable (front-load the important words)
- Operator-to-operator tone — you're a peer, not a vendor
- Slightly mysterious, under-explained on purpose
- No emojis, no bullet points, no bold, no formatting in emails
- No corporate language ("solutions", "leverage", "industry-leading", "synergy", "innovative")
- No feature lists, no pricing, no hard selling
- No fabricated details — only reference what you can infer from the data
- Revenue angle should feel like an afterthought, not a pitch — hint, don't sell

OUTPUT FORMAT — use EXACTLY this structure:
=== PHASE 1 DIAGNOSIS (internal) ===
Problem: [one sentence]
Revenue angle: [one sentence]

=== EMAIL 1 — Cold Outreach ===
Subject: [subject line]
[full email with greeting, body, sign-off]

=== EMAIL 2 — Follow-Up (Day 3) ===
Subject: Re: [Email 1 subject]
[full email]

=== EMAIL 3 — Soft Close (Day 7) ===
Subject: Should I close your file?
[full email]

=== SMS SEQUENCE ===
SMS 1 (Day 1): [message]
SMS 2 (Day 4): [message]
SMS 3 (Day 8): [message]`;

function buildUserMessage(data: DispensaryData): string {
  return `Generate a cold outreach sequence for the following dispensary:

FIRST_NAMES: ${data.first_names || "(none provided)"}
BUSINESS_LEGAL: ${data.business_legal}
BUSINESS_DBA: ${data.business_dba}
CITY: ${data.city}
STATE: ${data.state || "California"}
ZIP: ${data.zip}
ADDRESS: ${data.address}
LICENSE_STATUS: ${data.license_status}
LICENSE_TYPE: ${data.license_type}
LICENSE_DESIGNATION: ${data.license_designation}
ISSUE_DATE: ${data.issue_date}
EXPIRATION_DATE: ${data.expiration_date}
BUSINESS_STRUCTURE: ${data.business_structure}
OWNER_NAMES: ${data.owner_names}
ACTIVITY: ${data.activity || "(not applicable)"}
EMAIL: ${data.email}
PHONE: ${data.phone}

Follow the full output format exactly.`;
}

function parseResponse(raw: string) {
  const extract = (start: string, end: string | null) => {
    const startIdx = raw.indexOf(start);
    if (startIdx === -1) return "";
    const from = startIdx + start.length;
    if (!end) return raw.slice(from).trim();
    const endIdx = raw.indexOf(end, from);
    return endIdx === -1 ? raw.slice(from).trim() : raw.slice(from, endIdx).trim();
  };

  const diagnosisBlock = extract(
    "=== PHASE 1 DIAGNOSIS (internal) ===",
    "=== EMAIL 1"
  );
  const problemMatch = diagnosisBlock.match(/Problem:\s*(.+)/);
  const revenueMatch = diagnosisBlock.match(/Revenue angle:\s*(.+)/);

  const email1Block = extract("=== EMAIL 1 — Cold Outreach ===", "=== EMAIL 2");
  const email1SubjectMatch = email1Block.match(/Subject:\s*(.+)/);
  const email1Body = email1Block.replace(/Subject:\s*.+\n?/, "").trim();

  const isActive = raw.includes("=== EMAIL 2");

  let email2Subject = "";
  let email2Body = "";
  let email3Subject = "";
  let email3Body = "";
  let sms1 = "";
  let sms2 = "";
  let sms3 = "";

  if (isActive) {
    const email2Block = extract("=== EMAIL 2 — Follow-Up (Day 3) ===", "=== EMAIL 3");
    const email2SubjectMatch = email2Block.match(/Subject:\s*(.+)/);
    email2Subject = email2SubjectMatch?.[1]?.trim() ?? "";
    email2Body = email2Block.replace(/Subject:\s*.+\n?/, "").trim();

    const email3Block = extract("=== EMAIL 3 — Soft Close (Day 7) ===", "=== SMS SEQUENCE");
    const email3SubjectMatch = email3Block.match(/Subject:\s*(.+)/);
    email3Subject = email3SubjectMatch?.[1]?.trim() ?? "Should I close your file?";
    email3Body = email3Block.replace(/Subject:\s*.+\n?/, "").trim();

    const smsBlock = extract("=== SMS SEQUENCE ===", null);
    const sms1Match = smsBlock.match(/SMS 1 \(Day 1\):\s*(.+)/);
    const sms2Match = smsBlock.match(/SMS 2 \(Day 4\):\s*(.+)/);
    const sms3Match = smsBlock.match(/SMS 3 \(Day 8\):\s*(.+)/);
    sms1 = sms1Match?.[1]?.trim() ?? "";
    sms2 = sms2Match?.[1]?.trim() ?? "";
    sms3 = sms3Match?.[1]?.trim() ?? "";
  }

  return {
    diagnosis_problem: problemMatch?.[1]?.trim() ?? "",
    diagnosis_revenue: revenueMatch?.[1]?.trim() ?? "",
    email1_subject: email1SubjectMatch?.[1]?.trim() ?? "",
    email1_body: email1Body,
    email2_subject: email2Subject,
    email2_body: email2Body,
    email3_subject: email3Subject,
    email3_body: email3Body,
    sms1,
    sms2,
    sms3,
    raw,
  };
}

export async function POST(req: NextRequest) {
  try {
    const data: DispensaryData = await req.json();

    if (!data.business_dba || !data.license_status) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
    }

    const message = await client.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 2048,
      system: SYSTEM_PROMPT,
      messages: [{ role: "user", content: buildUserMessage(data) }],
    });

    const raw = message.content
      .filter((b) => b.type === "text")
      .map((b) => (b as { type: "text"; text: string }).text)
      .join("\n");

    const parsed = parseResponse(raw);
    return NextResponse.json(parsed);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

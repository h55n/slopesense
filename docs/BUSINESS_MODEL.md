# SlopeSense — Business Model & Revenue Path

## Why This Is a Business, Not a Grant Project

The gap SlopeSense fills is legally mandated to close.

The **Disaster Management (Amendment) Bill, 2025** (passed Rajya Sabha March 2025) now requires
NDMA and SDMAs to maintain national and state disaster databases and conduct regular risk assessments.
SDMAs that lack operational landslide risk intelligence are technically non-compliant.

SlopeSense provides compliance at **₹15–25 L/year** vs the cost of building in-house (crores, years).

---

## Revenue Streams

### Stream 1 — SDMA SaaS Contracts
**Customer:** State Disaster Management Authorities (10 high-risk states)
**Price:** ₹15–25 L/year per state
**Includes:** Dashboard access, WhatsApp alerts for all DDMA officers + Aapda Mitra volunteers,
             API access, annual False Alarm Rate report, model recalibration
**Timeline:** First contract: Months 6–12 (Kerala or Uttarakhand)
**TAM:** 10 high-risk states × ₹20L = ₹2 Cr ARR (Year 2)

### Stream 2 — NDMA National Contract
**Customer:** National Disaster Management Authority (federal)
**Price:** ₹1–3 Cr/year
**Includes:** Full India coverage, CAP feed to Sachet app, integration with NDRF pre-positioning system
**Timeline:** Year 2–3 (after 1+ monsoon season of validated live data)
**Path:** CAP feed integration makes SlopeSense a *data provider* embedded in national infrastructure

### Stream 3 — Open Data API (Paid Tier)
**Customers:** Reinsurers (Munich Re, Swiss Re India), NGOs, research institutions, road authorities
**Price:** ₹5–15 L/year per organization
**Tiers:**
  - Research/NGO: Free (up to 1,000 req/hour)
  - Commercial: ₹5L/year (10,000 req/hour)
  - Enterprise: ₹15L/year (unlimited + historical access)
**Timeline:** Launch Month 6 alongside public dashboard

### Stream 4 — World Bank / UNDP DRR Grants
**Source:** World Bank GFDRR Innovation Lab, UNDP DRR Resilience Programme
**Amount:** ₹2–5 Cr (one-time, non-dilutive)
**Eligibility:** No government MoU required for initial application
**Timeline:** Apply Month 3 (after retrospective validation published)
**Use:** Covers first 12–18 months of operations + international replication pilot

### Stream 5 — International Replication
**Markets:** Nepal, Bangladesh, Sri Lanka, Philippines, Indonesia (high-risk countries, World Bank DRR recipients)
**Price:** ₹20–50 L/year per country SDMA equivalent
**Path:** World Bank DRR funding creates the procurement vehicle
**Timeline:** Year 3+ (after India model validated and documented)

---

## Unit Economics

### Cost per state (Year 1)
| Item | Monthly | Annual |
|------|---------|--------|
| Compute (AWS t3.large) | ₹4,000 | ₹48,000 |
| Object storage (S3) | ₹800 | ₹9,600 |
| Database (RDS) | ₹2,000 | ₹24,000 |
| WhatsApp messages (~5,000/month) | ₹2,000 | ₹24,000 |
| **Total infra per state** | **₹8,800** | **₹1,05,600** |

**Gross margin at ₹20L/year per state: ~94%**

Infra scales sub-linearly — adding a 5th state adds minimal marginal cost.

---

## Go-to-Market Sequence

### Step 1 (Months 1–3): Credibility

**Action:** Publish retrospective validation report publicly. Wayanad 2024 as proof-of-concept.
Show the model would have flagged Meppadi block at 73% FPI, 20 hours before the disaster.

**Distribution:** Send report to:
- Kerala SDMA (direct email to State Emergency Operations Centre)
- NDMA Delhi (send to Director, Landslide Risk Management Scheme)
- Indian academic press (IIT Roorkee GeoHazards group, IISER Pune)
- Mainstream journalists covering disaster management

**Cost:** ₹0

### Step 2 (Months 3–6): First Pilot

**Approach Kerala SDMA and Uttarakhand SDMA directly.**

Kerala rationale: Post-Wayanad political urgency. Chief Minister personally committed to early warning.
Uttarakhand rationale: 2021 Chamoli disaster + ongoing Joshimath concerns. SDMA has active budget.

**Offer:** Free pilot for 1 monsoon season (June–September). We take the model risk; they take operational
responsibility for how they use the output.

**Ask in return:** Letter of intent for paid contract if pilot metrics are met. Access to their district
officer contact database for WhatsApp registration.

### Step 3 (Months 6–12): First Paid Contract

Pilot results + independent academic validation = signed contract.

Simultaneously:
- Apply for World Bank GFDRR Innovation Lab grant
- Onboard 2–3 research institutions on free API tier (builds credibility + gets citations)
- Register as vendor with GeM (Government e-Marketplace) — required for government procurement

### Step 4 (Year 2): NDMA Integration

Once CAP feed is verified and 1 monsoon season of live data is published, approach NDMA for CAP feed
integration into Sachet app. This is not a competition with GSI — it's a data provider relationship.

**Positioning:** "We provide the sub-district resolution forward-looking layer that GSI's experimental
system cannot yet provide. We are compatible with GSI's output format and can merge when they're ready."

### Step 5 (Year 3): International

Use India track record + World Bank DRR relationship to pitch Nepal and Bangladesh SDMA equivalents.
World Bank funds their DRR programs — we become the preferred vendor for landslide risk intelligence.

---

## Competitive Moat

**Retrospective audit trail:** Every alert, confirmed or false, is published. By the time GSI reaches
our level of coverage, we will have 3–5 monsoon seasons of validated data. That data moat is irreplaceable.

**Last-mile delivery network:** 5,000+ registered Gram Pradhan and Aapda Mitra WhatsApp contacts,
built district by district, is impossible to replicate quickly.

**CAP feed integration:** Once embedded in Sachet, replacing SlopeSense requires a government procurement
decision at the NDMA level — not a simple vendor switch.

**India-specific calibration:** Our model is recalibrated after each monsoon season against confirmed events.
A global model (NASA LHASA) or a late-moving government system (GSI) cannot match this iteration speed.

---

## Funding Strategy

**Phase 0 (pre-revenue):** Bootstrap + hackathon prize money. Zero cash needed for MVP.

**Phase 1 (₹25–50L seed):** Angel round from Indian climate-tech investors (Speciale Invest,
Mela Ventures, Omnivore) or direct grant from GFDRR. Funds: 2 engineers × 12 months,
infra, business development.

**Phase 2 (₹2–5 Cr Series A):** After first 2 state contracts signed. International expansion capital.
Investors: World Bank IFC, impact-focused VCs (Elemental Excelerator, The Lightsmith Group).

**Revenue self-sufficiency target:** Month 18 — 3 state contracts at ₹20L each = ₹60L ARR,
covering burn rate of ~₹4L/month.

---

## Risk: Government Procurement Timelines

Government procurement is notoriously slow. Mitigations:

1. **CAP feed route:** Becoming a data provider (not a software vendor) avoids the full procurement cycle.
   NDMA can consume our CAP feed without a formal software contract.

2. **LRMS scheme funding:** SDMAs already have budget under the Landslide Risk Mitigation Scheme.
   This is earmarked for exactly this type of system.

3. **DM Amendment Bill 2025 compliance:** Creates legal urgency. SDMAs need to be compliant.

4. **Pilot → paid transition:** Offer 3-month pilot with zero procurement friction (no MoU, no tender).
   Conversion to paid after results.

5. **Reinsurer revenue as bridge:** Munich Re India and Swiss Re India can sign commercial contracts
   within 8–12 weeks. Reinsurer revenue bridges the gap while government procurement moves slowly.

# SlopeSense — Deployment & Business Model Guide

## Deployment

### Option A: Single VPS (Hackathon / MVP)

Minimum spec: 8GB RAM, 4 vCPU, 100GB SSD  
Estimated cost: ₹3,000–5,000/month (DigitalOcean / AWS t3.large)

```bash
# 1. Clone and configure
git clone https://github.com/your-org/slopesense.git
cd slopesense
cp .env.example .env
nano .env  # fill in credentials

# 2. Start all services
docker-compose up -d

# 3. Run migrations
docker-compose exec api python -m scripts.migrate

# 4. Seed static data
docker-compose exec api python -m scripts.seed_static

# 5. Run retrospective validation
docker-compose exec api python -m scripts.retrospective --synthetic

# 6. Trigger first model run
curl -X POST "http://localhost:8000/internal/trigger-run?token=dev-token"

# Dashboard: http://localhost:3000
# API docs:  http://localhost:8000/docs
# CAP feed:  http://localhost:8000/v1/cap/feed
```

### Option B: Cloud (Production Scale)

| Component | Service | Monthly cost |
|-----------|---------|-------------|
| Compute (API + worker) | AWS t3.large or DigitalOcean 8GB | ₹3,000–5,000 |
| Managed PostgreSQL + PostGIS | AWS RDS or DigitalOcean Managed DB | ₹1,500–2,500 |
| Redis | ElastiCache or DigitalOcean Managed Redis | ₹800–1,200 |
| Object storage (satellite cache) | S3 or DigitalOcean Spaces | ₹500–1,000 |
| CDN | Cloudflare Free | ₹0 |
| **Total** | | **₹5,800–9,700/month** |

---

## Business Model

### Revenue Streams

#### Stream 1: SDMA SaaS Contracts
- **Customer:** State Disaster Management Authorities (10 high-risk states)
- **Price:** ₹15–25 lakh/year per state
- **Value proposition:** Statutory compliance with DM Amendment Act 2025, which mandates operational landslide risk systems at SDMA level
- **Sales motion:** Direct approach post-retrospective validation report. Start with Kerala (post-Wayanad) and Uttarakhand (post-Kedarnath/Chamoli)
- **Timeline:** Year 1–2
- **Revenue potential:** ₹1.5–2.5 Cr/year at 10 states

#### Stream 2: NDMA National Contract
- **Customer:** National Disaster Management Authority
- **Price:** ₹1–3 Cr/year
- **Path:** CAP feed integration → embedded in national infrastructure → procurement
- **Timeline:** Year 2–3
- **Note:** Government procurement is slow but makes competition nearly impossible once embedded

#### Stream 3: World Bank / UNDP DRR Grants
- **Programs:** World Bank GFDRR Innovation Lab, UNDP DRR resilience funds
- **Amount:** ₹2–5 Cr (one-time grant)
- **Timeline:** Apply at Year 1. Response in 6–9 months.
- **No government MoU required** for initial application
- **URL:** https://www.gfdrr.org/en/innovation-lab

#### Stream 4: Open Data API (Paid Tier)
- **Customers:** Academic researchers, NGOs, reinsurance companies (Munich Re, Swiss Re have India operations)
- **Price:** ₹5–15 lakh/year per organisation
- **Model:** Free for research/NGOs, paid for commercial use
- **Timeline:** Year 1–2

#### Stream 5: International Replication
- **Markets:** Nepal, Bangladesh, Sri Lanka, Bhutan (similar landslide risk profiles)
- **Path:** World Bank DRR programme funding for South Asia adaptation
- **Price:** ₹20–50 lakh/year per country
- **Timeline:** Year 3+

---

### Go-to-Market Sequence

**Month 1–3: Free launch**
- Public dashboard live with retrospective validation report
- Wayanad 2024 retrospective is the press hook
- Target: NDMA, SDMA officers, disaster management researchers, IIT landslide labs
- No sales team needed — let the retrospective data do the work

**Month 3–6: First conversations**
- Approach Kerala SDMA (post-Wayanad urgency + existing budget under LRMS scheme)
- Approach Uttarakhand SDMA (Chamoli + Kedarnath history)
- Offer free pilot monsoon season (no commitment)
- Simultaneously: file World Bank GFDRR grant application

**Month 6–12: First paid contract**
- Pilot results + independent academic validation = procurement case
- IIT Roorkee or IISER Pune partnership for third-party validation
- First SDMA paid contract signed

**Year 2: National integration**
- CAP feed integrated into NDMA Sachet app
- Product is now embedded in national infrastructure
- Procurement lock-in achieved

---

### Why Government Procurement Is The Right Model

1. **Statutory driver:** DM Amendment Act 2025 (passed Rajya Sabha March 2025) mandates SDMAs to maintain operational landslide risk databases. SDMAs that lack this system are now technically non-compliant. SlopeSense provides compliance at ₹15–25 lakh/year vs. building in-house (crores, years).

2. **Budget exists:** LRMS (Landslide Risk Mitigation Scheme) allocates specific funds to SDMAs for exactly this category of tool. We are not competing for general budget — there is a dedicated line item.

3. **GSI comparison:** GSI's competing system needs 4–5 more years and is SDMA-only. Our public-facing, village-level layer is out of their scope.

4. **Moat:** CAP feed integration into Sachet app = embedded in national infrastructure = extraordinary switching cost for any competitor.

---

### Unit Economics

| Scenario | Year 1 | Year 2 | Year 3 |
|----------|--------|--------|--------|
| SDMA contracts (states) | 1 × ₹20L = ₹20L | 3 × ₹20L = ₹60L | 7 × ₹20L = ₹140L |
| API / grants | ₹30L | ₹75L | ₹150L |
| NDMA contract | — | ₹100L | ₹200L |
| International | — | — | ₹50L |
| **Total revenue** | **₹50L** | **₹235L** | **₹540L** |
| Infrastructure costs | ₹12L | ₹20L | ₹35L |
| Team (3 engineers + 1 ops) | ₹80L | ₹120L | ₹180L |
| **Net** | **-₹42L** | **+₹95L** | **+₹325L** |

Break-even: ~Month 18 with 3 SDMA contracts + World Bank grant.

---

## Risk Register

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| IMD QPF access denied | High | Medium | NOAA GFS fallback documented and implemented. Still superior to any existing public product. |
| False positive causes evacuation → trust collapse | Critical | Medium | Confidence gating, spatial clustering, mandatory signal disclosure, public False Alarm Rate reports |
| GSI accelerates deployment | High | Low | 4–5 year calibration timeline per GSI officials. Our public-facing layer is not in their roadmap. |
| NDMA prefers to build in-house | Medium | Medium | CAP feed makes us a data provider, not a competing vendor. |
| Retrospective validation fails | High | Low | Published honestly. Model recalibrated. Physics of rainfall-triggered landslides is well-established. |
| WhatsApp Business API approval delayed | Medium | Medium | Email + SMS (IMI Mobile) as Day 1 fallback. |
| Government procurement takes 2+ years | Medium | High | World Bank grants de-risk early stage. Free dashboard generates PR and organic traction. |

---

## Competitive Moat Summary

```
SlopeSense moat = technical differentiation × trust infrastructure × distribution lock-in

Technical:   LHASA v2 + India calibration + 24-48h forecast layer
Trust:       Public retrospective audit + confidence intervals + False Alarm Rate reports
Distribution: CAP feed → NDMA Sachet → 500M+ phones
             WhatsApp Business API → 600M India users
             Block-level contacts → last-mile in 200k+ villages
```

No competitor operates in all three dimensions simultaneously.
GSI has technical credibility but no distribution. NDMA Sachet has distribution but no model.
We bridge the gap.

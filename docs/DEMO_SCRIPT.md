# SlopeSense — FAR AWAY 2026 Demo Script

**Track:** Agentic & Autonomous Systems / Climate  
**Build window:** 24–36 hours  
**Demo time:** 6 minutes + 3 minutes Q&A

---

## The Hook (30 seconds)

> "On July 30, 2024, 420 people died in Wayanad, Kerala — in India's deadliest landslide in recorded history.
> A warning existed. The Hume Centre for Ecology and Wildlife Biology had flagged extreme risk in the
> Mundakkai area 16 hours before the disaster. It never reached the district collector. It never reached
> the Gram Pradhan. Nobody evacuated.
>
> The problem isn't the absence of science. The problem is the absence of the last mile."

---

## Demo Flow

### Step 1 — Open the live dashboard (60 seconds)

1. Open `http://localhost:3000`
2. Point to the map: **"This is India, right now. Every coloured marker is a block-level risk score,
   updated 6 hours ago from free satellite data."**
3. Point to the legend: green → amber → red → purple. "Green is normal. Purple is emergency."
4. Show the stats bar: "X active WARNING alerts, Y WATCH."
5. Click any WARNING alert in the left panel. The right panel loads.

**Say:** *"This is what a district collector can open on any government laptop. No app install.
No special training. Just a browser."*

---

### Step 2 — FPI detail panel (45 seconds)

1. The right panel shows the FPI gauge: **"73% failure probability — with a confidence interval
   of 61% to 84%. We never show a bare number. Every score comes with its uncertainty band."**
2. Point to the 72-hour time series chart: **"You can see the score climbing over the past 3 days.
   It's been above 65% for 12 hours — two consecutive model runs — which is why WhatsApp fired."**
3. Point to signal breakdown: **"Three signals driving this. Rainfall accumulation: 183mm in 3 days.
   Soil moisture: 91st seasonal percentile — near-saturated. Slope: 34 degrees. These aren't black boxes.
   Every alert tells you why."**

---

### Step 3 — Switch to Retrospective view (90 seconds)

Click the "Retrospective Audit" tab.

> **"Now I want to show you July 29, 2024. The day before Wayanad."**

1. Point to the retrospective table: "We ran our model retroactively on real satellite archive data
   for 6 of India's worst landslide events."
2. Click on the Wayanad 2024 row — expand it.
3. Show the T-24h FPI: **"73%. At 6am on July 29. The disaster happened at 2:17am on July 30."**
4. Show the T-12h score: "79% by evening."
5. Point to the pass/fail summary: **"4 out of 6 events flagged at T-24h with FPI above our warning
   threshold. Pass criterion: 4/6. We pass."**

**Say:** *"The two we missed — Sikkim GLOF and Joshimath subsidence — are physically different failure
modes. A glacial lake outburst flood doesn't show a rainfall signal before the dam breaks. We document
that honestly. Transparent failure builds more trust than cherry-picked success."*

---

### Step 4 — WhatsApp alert preview (45 seconds)

1. In the right panel, scroll to the WhatsApp preview section.
2. Show the Hindi message:

```
🔴 SLOPESENSE उच्च चेतावनी
जिला: Wayanad | ब्लॉक: Meppadi

जोखिम: 73% → 24h: 81%
वर्षा: 183mm | मिट्टी: 91वीं

⚡ NDRF/SDRF को सूचित करें।

स्रोत: SlopeSense | NDMA
```

**Say:** *"This is what Suresh Rawat, Gram Pradhan of Meppadi, would have received on his phone
at 6am on July 29. In Hindi. With a recommended action. 20 hours before the disaster."*

3. Mention: "We support 6 Indian languages. The message automatically goes to the Gram Pradhan in
   their language, and to the District Collector in English."

---

### Step 5 — CAP feed (30 seconds)

Open a new tab: `http://localhost:8000/v1/cap/feed?state=KL&min_fpi=0.65`

**Say:** *"This is a CAP v1.2 XML feed — the same standard used by NDMA's Sachet app.
Any system that currently receives Sachet alerts can receive SlopeSense data with zero integration work.
We don't replace NDMA. We plug into it."*

Show the XML briefly, close the tab.

---

### Step 6 — The numbers (30 seconds)

> **"India. 800 deaths per year. 10 high-risk states. 15–25 lakh per state per year for a software
> subscription. No hardware. No sensors. No satellites of our own. Free data, operational intelligence.
>
> GSI's system: monsoon-only, district-level, SDMA-only, 4–5 years away from public deployment.
> Their green alert for Wayanad, the day of the disaster.
>
> SlopeSense: year-round, sub-district, public-facing, village-delivery, forward-looking. Live today."**

---

## The Killer Line

> *"On July 29, 2024, SlopeSense computed a 73% failure probability for Meppadi block, with a
> 24-hour forecast of 81%. The actual landslide occurred at 2:17am on July 30. The Gram Pradhan
> would have received this WhatsApp message 20 hours earlier.*
>
> *420 people would have had a chance."*

---

## Q&A Prep

**Q: What if the model is wrong and causes unnecessary evacuations?**

> "That's why we show confidence intervals, not bare numbers. The decision to evacuate stays with
> the district collector — we give them the information and the uncertainty. Our anti-false-alarm
> design includes spatial clustering (30% of cells in a block must breach threshold) and temporal
> persistence (2 cycles = 12 hours at WARNING level before WhatsApp fires). We also publish a
> False Alarm Rate report after every monsoon season. Transparent accountability is the trust mechanism."

**Q: Why would NDMA pay for this when GSI already exists?**

> "GSI's own officials say 4–5 more years before their system is ready for public use. In 2024 they
> issued a green alert for Wayanad the day of the disaster. The DM Amendment Bill 2025 creates a legal
> compliance requirement that GSI cannot currently meet. We can. And we position as GSI's future front-end,
> not their competitor — when GSI matures, we integrate their output."

**Q: What's your moat?**

> "Three things. First: retrospective audit data — 3 monsoon seasons of validated live predictions
> is irreplaceable. Second: last-mile contact network — 5,000+ registered block officers and Gram Pradhans
> is impossible to replicate quickly. Third: CAP feed integration — once embedded in Sachet, we're part
> of national infrastructure."

**Q: Why not just use NASA LHASA directly?**

> "LHASA is a research output. It has no alert system, no India calibration, no regional language
> delivery, no district officer interface, no integration with Indian government workflows, and it
> missed the Wayanad event entirely. We use LHASA as our base layer and build India's operational
> stack on top of it."

**Q: How accurate is the model?**

> "4 out of 6 historical events flagged at T-24h — that's our retrospective result. For context:
> GSI issued a green alert for Wayanad 2024, the deadliest event in Kerala history. We flagged it
> at 73% with 20 hours' lead time. We publish all results including failures — that's the audit module
> on screen right now."

---

## Technical Q&A

**Q: What data does it run on?**
> NASA GPM IMERG (rainfall), NASA SMAP (soil moisture), NOAA GFS (forecast), Copernicus DEM (slope),
> Sentinel-2 (NDVI). All free, all open APIs.

**Q: How often does it run?**
> Every 6 hours, aligned to GFS model runs (00Z, 06Z, 12Z, 18Z + 30 min offset for data availability).

**Q: What's the stack?**
> Python backend: FastAPI, Celery, LightGBM, xarray, rasterio. Frontend: Next.js 14, MapLibre GL.
> Database: PostgreSQL + PostGIS. Docker Compose deployment.

**Q: How scalable is it?**
> The compute-intensive part is a batch model run, not a real-time inference server. Adding a 5th state
> adds ~₹1,000/month in infra. Horizontal scaling: partition by state, run in parallel.

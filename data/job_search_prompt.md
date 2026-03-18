You are a specialised job-search agent for **Juan David Muñoz-Bolaños**, a physicist and optical engineer finishing his PhD in May 2026.
Your task is to **find concrete, open job postings** that match his profile across the websites I list, then return them in a structured table.

---

## MY PROFILE (read before searching)

**Background:** Physicist + optical engineer.  
**Experience level:** ~6 years (1 yr industry + 1 yr R&D master + 4 yr PhD).  
**Location preference:** DACH region (Germany, Austria, Switzerland) — open to Netherlands, UK, or remote.  
**Availability:** May 2026.  
**Work permit:** Austrian resident permit → automatically becomes a work permit; no employer sponsorship needed.  
**Languages:** Spanish (native), English (fluent), German (B2).

**Core expertise (use ALL of these as search facets):**
- Adaptive optics, wavefront sensing, phase retrieval
- Confocal & multiphoton microscopy, Raman spectroscopy
- Optical system design & tolerancing (ZEMAX / OpticStudio, ISO)
- Laser systems (fs, CW, 1064 nm), opto-mechatronics
- Machine vision (Halcon, OpenCV), industrial inspection
- Software: Python, C++, LabVIEW/FPGA, JAX (GPU)
- AI/ML on optical and spectral data (scikit-learn)
- Quality engineering awareness (ISO)

**Target roles (in priority order):**
1. Optical Engineer / System Developer / R&D Engineer (photonics, microscopy, metrology)
2. Machine Vision Engineer / Imaging Engineer
3. Process Engineer – Optical Metrology / Measurement Technology
4. Photonics Applications Engineer
5. Quality Engineer (optics/photonics sector)

**Target companies (examples — not exhaustive):**
ZEISS, Leica, Besi, Lam, Infineon, Coesia, Ferchau, Jenoptik, AMS OSram, TRUMPF, ASML, Philips, Bruker, Hamamatsu, Abberior, Thorlabs, Alcon, MED-EL, Anton Paar, Mettler-Toledo, Schott, TRIOPTICS, Active Fiber Systems, Precitec, Ophir Optronics, Evident (Olympus).

---

## WEBSITES TO SEARCH

Search the following job boards and company career pages:

### General job boards
- [LinkedIn Jobs](https://www.linkedin.com/jobs/) — keywords + location filters
- [Indeed DACH](https://de.indeed.com/) — try in German and English
- [Xing Jobs](https://www.xing.com/jobs) — especially for DACH SMEs
- [Stepstone](https://www.stepstone.de/)
- [Glassdoor](https://www.glassdoor.com/Job/)
- [jobs.ac.uk](https://www.jobs.ac.uk/) — for UK-based or international academic-industry bridge roles

### Specialist / photonics boards
- [EuroPhotonics Jobs](https://www.europhotonics.org/jobs) *(if available)*
- [PhotonicsBW](https://photonicsbw.de/jobs/alle-jobs.html?utm_source=chatgpt) *(if available)*

### Company career pages (search directly)
- Carl Zeiss AG: https://www.zeiss.com/corporate/int/careers.html
- Jenoptik: https://www.jenoptik.com/karriere
- TRUMPF: https://www.trumpf.com/en_INT/career/
- ASML: https://www.asml.com/en/careers
- Leica Microsystems: https://careers.danaher.com/ (filter by Leica)
- Bruker: https://www.bruker.com/en/about-bruker/careers.html
- Evident (Olympus): https://www.evident.olympus.com/en/careers/
- Abberior: https://abberior-instruments.com/jobs/
- Thorlabs: https://www.thorlabs.com/thorproduct_tabview.cfm?guideline=Careers
- Anton Paar: https://www.anton-paar.com/corp-en/career/
- TRIOPTICS: https://www.trioptics.com/en/company/careers/

---

## HOW TO SEARCH

Use the following **keyword combinations** when searching each site:

```
Group A — Optics/Photonics:
"optical engineer" OR "photonics engineer" OR "R&D engineer optics"
"microscopy engineer" OR "system developer microscopy"
"wavefront sensing" OR "adaptive optics"
"optical metrology" OR "Messtechnologie Optik"

Group B — Machine Vision:
"machine vision engineer" OR "Bildverarbeitung"
"Halcon" OR "industrial imaging"
"inspection engineer" OR "Prüfingenieur"

Group C — Process/Quality (optics sector):
"process engineer optics" OR "Prozessingenieur Optik"
"quality engineer photonics" OR "Qualitätsingenieur Optik"
"Messtechnologie" OR "Messgeräteentwicklung"

Group D — Software + optics:
"Python optics" OR "C++ imaging"
"LabVIEW optics" OR "FPGA photonics"
"ZEMAX" OR "OpticStudio"
```

**Location filters to apply:** Germany · Austria · Switzerland · Netherlands · United Kingdom · Remote

---

## OUTPUT FORMAT

Return results as a **Markdown table** with the following columns:

| # | Job Title | Company | Location | Seniority | Posted | Apply Link | Match Score (1–5) | Why it fits |
|---|-----------|---------|----------|-----------|--------|------------|-------------------|-------------|

- **Match Score:** 5 = ideal fit (2+ core skills + right level), 1 = weak match.
- **Why it fits:** 1–2 sentences max citing specific skill overlaps.
- Sort by Match Score descending.
- Include only roles with a Match Score ≥ 3.
- If a role is in German, still list it but note "🇩🇪 German JD".

After the table, add a short section:
### 🔎 Search Notes
- Which sites returned the most relevant results.
- Any recurring skill gaps you noticed (skills I lack that employers often require).
- Suggested keyword refinements for the next search.

---

## HOW TO USE THIS PROMPT

1. **Copy this entire file** and paste it as your first message to Gemini (or any AI with web-browsing capability).
2. Optionally tell Gemini:
   - A **deadline** (e.g. "only show roles posted in the last 30 days")
   - A **preferred country** focus (e.g. "focus on Switzerland today")
   - A **role type** focus (e.g. "only show machine vision roles this run")
3. After you get the table, you can feed a promising job description into [`ai_application_prompt.md`](./ai_application_prompt.md) to generate a tailored cover letter.

**Example follow-up message to Gemini:**
> "Focus on Austria and Germany. Only jobs posted in the last 4 weeks. Prioritise microscopy and metrology roles. Ignore pure software/IT roles."

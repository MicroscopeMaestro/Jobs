# assets/papers/

Place your research paper PDFs and SPIE documents here.

## Expected files (rename as needed)
- `acs_photonics_2025.pdf`       — Closed-Loop Optical Aberration Correction
- `biomed_optics_express_2023.pdf` — Optofluidic Adaptive Optics
- `spie_2024.pdf`                — SPIE San Francisco paper/certificate

## Usage

```bash
# Match papers to a job offer
export GOOGLE_API_KEY="your-key-here"
python3 src/match_skills.py --job-url "https://..."

# Or point to a specific folder
python3 src/match_skills.py --job-url "https://..." --papers /path/to/other/pdfs
```

# EcoMyth-VLM

**Benchmarking Vision Language Models for Ecological Accuracy**

A multi-phase empirical study evaluating how accurately Vision Language Models (VLMs) identify species from images and generate ecologically grounded descriptions. The benchmark spans 4 species tiers — from globally iconic to confusable — and measures hallucination rates, claim-level recall, and inter-rater reliability against human annotators.

---

> ### 📂 Official Repository
>
> **If any file, notebook, or resource is not accessible or not loading in the anonymised submission repository, please visit the official project GitHub page:**
>
> ## 👉 [https://github.com/AnuruddhaPaul/Eco_Myth](https://github.com/AnuruddhaPaul/Eco_Myth)
> https://github.com/AnuruddhaPaul/Eco_Myth
>
> All source code, outputs, figures, and annotation tools are available there in full. Click the link above to be taken directly to the repository.

---

## Project Structure

```
EcoMyth-VLM/
├── data/
│   └── GBIF/downloaded/          # Species images from GBIF, organised by tier
│       ├── tier1_iconic_common/   # e.g. Panthera leo, Ailuropoda melanoleuca
│       ├── tier2_regionally_known/
│       ├── tier3_rare_endangered/
│       └── tier4_confusable/
│
├── outputs/
│   ├── phase1/                   # Data manifests & stratification reports
│   ├── phase2/                   # VLM evaluation results (JSONL/JSON, LFS)
│   ├── phase3/                   # Hallucination scores & ground-truth
│   ├── phase4/                   # BioCLIP embeddings & claim-only metrics
│   ├── phase5/                   # Aggregated results & LaTeX tables
│   ├── phase6/                   # Claude annotation CSV
│   ├── phase6_rq13/              # Human annotation CSVs & ICC output
│   └── figures/                  # Publication-ready figures (PDF + PNG)
│
├── EcoMyth_VLM_Phase1.ipynb      # Data collection & stratification
├── EcoMyth_VLM_Phase2_*.ipynb    # VLM inference across 11+ models
├── EcoMyth_VLM_Phase3.ipynb      # Hallucination scoring
├── EcoMyth_VLM_Phase4_V1.ipynb   # BioCLIP visual similarity analysis
├── EcoMyth_VLM_Phase5_V1.ipynb   # Statistical analysis & ablations
├── EcoMyth_Phase6_AnnotationTool_v*.html  # In-browser annotation UI
│
├── annotate_rq13.py              # Flask server for RQ13 human annotation
├── rq13_server.py                # Alternate annotation server
├── compute_rq13_kappa.py         # ICC(A,1) inter-rater reliability
├── generate_figures.py           # Reproduces all 6 paper figures
├── phase6_server.py              # Phase 6 annotation backend
└── sample_100.py                 # Stratified 100-story sampler
```

---

## Phases

| Phase | Description |
|-------|-------------|
| **Phase 1** | Dataset construction — download GBIF & iNaturalist images, stratify into 4 tiers, generate manifests |
| **Phase 2** | VLM inference — run 11+ models (GPT-4V, Gemini, Claude, LLaVA, …) on species images |
| **Phase 3** | Hallucination scoring — compare generated claims against curated ground truth |
| **Phase 4** | Visual similarity — BioCLIP embeddings to measure image-level confusability |
| **Phase 5** | Statistical analysis — aggregation, ablations, LaTeX tables |
| **Phase 6** | Human annotation — inter-rater reliability (ICC/κ) between human and Claude judges |

---

## Species Tiers

| Tier | Description | Examples |
|------|-------------|---------|
| Tier 1 | Iconic / globally common | Giant Panda, Lion, Tiger, Polar Bear |
| Tier 2 | Regionally known | Red Panda, Axolotl, Capybara, Quokka |
| Tier 3 | Rare / critically endangered | Mountain Gorilla, Blue Whale, Black Rhino |
| Tier 4 | Confusable species | Morphologically similar pairs |

---

## Reproducing Results

### 1. Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt  # or install from notebooks
```

### 2. Run Phases in Order

```bash
# Phase 1 — data collection
jupyter notebook EcoMyth_VLM_Phase1.ipynb

# Phase 2 — VLM inference (requires API keys)
jupyter notebook EcoMyth_VLM_Phase2_11models.ipynb

# Phase 3 — hallucination scoring
jupyter notebook EcoMyth_VLM_Phase3.ipynb

# Phase 4 — BioCLIP analysis
jupyter notebook EcoMyth_VLM_Phase4_V1.ipynb

# Phase 5 — statistics
jupyter notebook EcoMyth_VLM_Phase5_V1.ipynb

# Regenerate figures
python generate_figures.py
```

### 3. Human Annotation (RQ13)

```bash
python sample_100.py             # sample 100 stories
python annotate_rq13.py          # open http://localhost:5050
python compute_rq13_kappa.py     # compute ICC(A,1)
```

---

## Key Outputs

| File | Description |
|------|-------------|
| `outputs/phase2/phase2_results.jsonl` | Per-image VLM responses |
| `outputs/phase3/phase3_hallucination_scores.jsonl` | Claim-level hallucination flags |
| `outputs/phase4/phase4_bioclip_scores.jsonl` | Visual similarity scores |
| `outputs/phase5/phase5_results.json` | Aggregated metrics |
| `outputs/figures/fig*.pdf` | Paper figures (PDF + PNG) |

---

## Large Files

Binary and large result files are tracked with **Git LFS** (`.gitattributes`). Clone with LFS support:

```bash
git lfs install
git clone https://github.com/AnuruddhaPaul/Eco_Myth.git
```

---

## Data Sources

- **[GBIF](https://www.gbif.org/)** — Global Biodiversity Information Facility (images licensed under CC BY 4.0)
- **[iNaturalist](https://www.inaturalist.org/)** — Citizen science species observations
- **[BioCLIP](https://huggingface.co/imageomics/bioclip)** — Biologically-aware CLIP model for visual embeddings

---

## License

Code is released under the MIT License. Images sourced from GBIF/iNaturalist retain their original licenses (CC BY 4.0 / CC BY-NC 4.0). See `LICENSE` for details.

"""
annotate_rq13.py
Fast human annotation tool for RQ13 (100 stories, ~45 sec/story target).
Run: python annotate_rq13.py
Opens at: http://localhost:5050

Saves to: ./outputs/phase6_rq13/rq13_human_annotations.csv
NEVER overwrites — appends per story, saves immediately on each submit.
"""

import json
import csv
import os
import time
from flask import Flask, request, jsonify, send_from_directory

# ── Config ──────────────────────────────────────────────────────────────────
STORIES_FILE  = "./outputs/phase6/phase6_annotation_stories.json"
SAMPLE_FILE   = "./outputs/phase6_rq13/rq13_stories.json"
OUTPUT_CSV    = "./outputs/phase6_rq13/rq13_human_annotations.csv"
PORT          = 5050

DIMENSIONS = ["species_id", "habitat", "diet", "iucn_status", "overall_accuracy"]
DIM_LABELS = {
    "species_id":       "Species ID",
    "habitat":          "Habitat",
    "diet":             "Diet",
    "iucn_status":      "IUCN Status",
    "overall_accuracy": "Overall Ecological Accuracy",
}

# ── Load data ────────────────────────────────────────────────────────────────
if not os.path.exists(SAMPLE_FILE):
    raise FileNotFoundError(
        f"Sample file not found: {SAMPLE_FILE}\n"
        "Run sample_100.py first."
    )

with open(SAMPLE_FILE, "r", encoding="utf-8") as f:
    STORIES = json.load(f)

print(f"Loaded {len(STORIES)} stories.")

# ── Load ground truth if available ───────────────────────────────────────────
GT_FILE = "./outputs/phase3/species_ground_truth.json"
ground_truth = {}
if os.path.exists(GT_FILE):
    with open(GT_FILE, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)
    print(f"Ground truth loaded for {len(ground_truth)} species.")

# ── Load already-annotated indices ───────────────────────────────────────────
done_indices = set()
if os.path.exists(OUTPUT_CSV):
    with open(OUTPUT_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            done_indices.add(int(row["ann_index"]))
    print(f"Resuming: {len(done_indices)}/100 already annotated.")

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>EcoMyth-VLM Annotation — RQ13</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f1117;
         color: #e0e0e0; min-height: 100vh; padding: 20px; }

  #header { display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 16px; }
  #progress-bar-wrap { flex: 1; background: #222; border-radius: 8px; height: 12px;
                       margin: 0 20px; overflow: hidden; }
  #progress-bar { height: 100%; background: #4caf50; border-radius: 8px;
                  transition: width 0.3s; }
  #progress-txt { font-size: 13px; color: #aaa; white-space: nowrap; }

  .card { background: #1c1f2e; border-radius: 12px; padding: 20px;
          margin-bottom: 14px; }
  .meta { font-size: 12px; color: #888; margin-bottom: 6px; }
  .meta span { color: #b0c4de; font-weight: 600; }

  #gt-box { background: #0d2137; border-left: 3px solid #4fc3f7;
            padding: 12px 16px; border-radius: 6px; font-size: 13px;
            line-height: 1.7; }
  #gt-box h4 { color: #4fc3f7; margin-bottom: 8px; font-size: 13px; }
  #gt-box dt { color: #aaa; display: inline; }
  #gt-box dd { color: #e0e0e0; display: inline; margin-left: 4px; }
  #gt-box dl { display: grid; grid-template-columns: max-content 1fr; gap: 4px 12px; }

  #story-box { background: #131622; border: 1px solid #2a2d3e; border-radius: 8px;
               padding: 14px 16px; font-size: 14px; line-height: 1.75;
               max-height: 280px; overflow-y: auto; white-space: pre-wrap; }

  .sliders { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 24px;
             margin-top: 4px; }
  .dim { display: flex; flex-direction: column; gap: 6px; }
  .dim label { font-size: 13px; color: #ccc; display: flex;
               justify-content: space-between; }
  .dim label span { color: #4fc3f7; font-weight: 700; font-size: 15px; }
  input[type=range] { width: 100%; accent-color: #4fc3f7; cursor: pointer; }

  #submit-btn { display: block; width: 100%; padding: 14px;
                background: #4caf50; color: #fff; font-size: 16px;
                font-weight: 700; border: none; border-radius: 8px;
                cursor: pointer; letter-spacing: 0.5px; margin-top: 6px;
                transition: background 0.2s; }
  #submit-btn:hover { background: #43a047; }
  #submit-btn:active { background: #388e3c; }

  #skip-btn { display: block; width: 100%; padding: 8px;
              background: transparent; color: #888; font-size: 13px;
              border: 1px solid #333; border-radius: 8px; cursor: pointer;
              margin-top: 6px; }
  #skip-btn:hover { color: #bbb; border-color: #555; }

  #toast { position: fixed; bottom: 24px; right: 24px; background: #4caf50;
           color: #fff; padding: 10px 20px; border-radius: 8px; font-size: 14px;
           display: none; z-index: 999; }
  #done-screen { text-align: center; padding: 80px 20px; }
  #done-screen h1 { font-size: 36px; color: #4caf50; margin-bottom: 12px; }
  #done-screen p  { color: #aaa; font-size: 16px; }

  #kbd { font-size: 11px; color: #555; margin-top: 4px; }
  kbd { background: #222; border: 1px solid #444; border-radius: 3px;
        padding: 1px 5px; font-family: monospace; font-size: 11px; }
</style>
</head>
<body>

<div id="header">
  <div style="font-weight:700;font-size:16px;white-space:nowrap">
    EcoMyth-VLM · RQ13 Annotation
  </div>
  <div id="progress-bar-wrap"><div id="progress-bar"></div></div>
  <div id="progress-txt">0 / 100</div>
</div>

<div id="main-content">
  <!-- filled by JS -->
</div>

<div id="toast">✓ Saved</div>

<script>
let stories = [];
let doneSet = new Set();
let currentIdx = 0;  // index into stories[]

const DIMS = ["species_id","habitat","diet","iucn_status","overall_accuracy"];
const DIM_LABELS = {
  species_id:       "Species ID",
  habitat:          "Habitat",
  diet:             "Diet",
  iucn_status:      "IUCN Status",
  overall_accuracy: "Overall Ecological Accuracy"
};

async function init() {
  const r = await fetch("/api/stories");
  const data = await r.json();
  stories = data.stories;
  doneSet = new Set(data.done_indices);
  advance();
}

function advance() {
  // find next unannotated
  while (currentIdx < stories.length && doneSet.has(stories[currentIdx].ann_index)) {
    currentIdx++;
  }
  updateProgress();
  if (currentIdx >= stories.length) {
    showDone(); return;
  }
  render(stories[currentIdx]);
}

function updateProgress() {
  const done = doneSet.size;
  const pct  = (done / 100) * 100;
  document.getElementById("progress-bar").style.width = pct + "%";
  document.getElementById("progress-txt").textContent  = `${done} / 100`;
}

function render(story) {
  const gt = story.ground_truth || {};
  const mc = document.getElementById("main-content");

  const gtHtml = `
    <div id="gt-box">
      <h4>🔬 Ground Truth</h4>
      <dl>
        <dt>Species:</dt><dd>${story.species_name || "—"}</dd>
        <dt>Habitat:</dt><dd>${gt.habitat || "—"}</dd>
        <dt>Diet:</dt><dd>${gt.diet || "—"}</dd>
        <dt>IUCN Status:</dt><dd>${gt.iucn_status || "—"}</dd>
        <dt>Range:</dt><dd>${gt.range || "—"}</dd>
        <dt>Tier:</dt><dd>${story.tier || "—"}</dd>
      </dl>
    </div>`;

  const sliderHtml = DIMS.map((d,i) => `
    <div class="dim">
      <label>${DIM_LABELS[d]} <span id="val-${d}">3.0</span></label>
      <input type="range" id="sl-${d}" min="1" max="5" step="0.1" value="3.0"
             oninput="document.getElementById('val-${d}').textContent=parseFloat(this.value).toFixed(1)">
    </div>`).join("");

  mc.innerHTML = `
    <div class="card">
      <div class="meta">
        Story <span>${story.ann_index + 1}/100</span> &nbsp;|&nbsp;
        Model: <span>${story.model_key || "?"}</span> &nbsp;|&nbsp;
        Format: <span>${story.format || "?"}</span> &nbsp;|&nbsp;
        Temp: <span>${story.temperature ?? "?"}</span>
      </div>
      ${gtHtml}
    </div>
    <div class="card">
      <div class="meta" style="margin-bottom:8px">Generated Story</div>
      <div id="story-box">${escHtml(story.story_text || story.generated_text || story.text || "(no text found)")}</div>
    </div>
    <div class="card">
      <div class="meta" style="margin-bottom:10px">Rate each dimension (1 = completely wrong, 5 = fully accurate)</div>
      <div class="sliders">${sliderHtml}</div>
      <div id="kbd">
        Keyboard: <kbd>Tab</kbd> move slider · <kbd>←</kbd><kbd>→</kbd> adjust ·
        <kbd>Enter</kbd> submit · <kbd>S</kbd> skip
      </div>
    </div>
    <button id="submit-btn" onclick="submitAnnotation()">Submit &amp; Next →</button>
    <button id="skip-btn"   onclick="skipStory()">Skip this story</button>
  `;

  // Focus first slider for keyboard nav
  document.getElementById("sl-species_id").focus();
}

function escHtml(t) {
  return t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

async function submitAnnotation() {
  const story = stories[currentIdx];
  const ratings = {};
  DIMS.forEach(d => {
    ratings[d] = parseFloat(document.getElementById("sl-"+d).value);
  });

  const payload = {
    ann_index:    story.ann_index,
    story_id:     story.story_id || null,
    model_key:    story.model_key,
    format:       story.format,
    species_name: story.species_name,
    tier:         story.tier,
    temperature:  story.temperature,
    timestamp:    new Date().toISOString(),
    ...ratings
  };

  const r = await fetch("/api/annotate", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });
  if (r.ok) {
    doneSet.add(story.ann_index);
    showToast();
    currentIdx++;
    setTimeout(advance, 300);
  } else {
    alert("Save failed — check server terminal.");
  }
}

function skipStory() {
  currentIdx++;
  advance();
}

function showToast() {
  const t = document.getElementById("toast");
  t.style.display = "block";
  setTimeout(() => t.style.display = "none", 1200);
}

function showDone() {
  document.getElementById("main-content").innerHTML = `
    <div id="done-screen">
      <h1>✓ Done!</h1>
      <p>All 100 stories annotated.<br>
         Annotations saved to <code>outputs/phase6_rq13/rq13_human_annotations.csv</code></p>
    </div>`;
  document.getElementById("progress-bar").style.width = "100%";
  document.getElementById("progress-txt").textContent = "100 / 100";
}

// Keyboard shortcut: Enter → submit, S → skip
document.addEventListener("keydown", e => {
  if (e.key === "Enter" && e.target.tagName !== "BUTTON") submitAnnotation();
  if (e.key === "s" || e.key === "S") skipStory();
});

init();
</script>
</body>
</html>
"""

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return HTML

@app.route("/api/stories")
def api_stories():
    """Return story list + set of already-annotated indices."""
    return jsonify({
        "stories":      STORIES,
        "done_indices": list(done_indices),
    })

@app.route("/api/annotate", methods=["POST"])
def api_annotate():
    """Save one annotation row immediately to CSV."""
    data = request.get_json(force=True)

    fieldnames = [
        "ann_index", "story_id", "model_key", "format", "species_name",
        "tier", "temperature", "timestamp",
        "species_id", "habitat", "diet", "iucn_status", "overall_accuracy"
    ]

    file_exists = os.path.exists(OUTPUT_CSV)
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

    done_indices.add(data["ann_index"])
    print(f"  [{len(done_indices):3d}/100] Saved ann_index={data['ann_index']} "
          f"| {data.get('model_key','?')} | {data.get('format','?')} "
          f"| {data.get('species_name','?')}")
    return jsonify({"status": "ok"})

# ── Inject ground truth into stories at startup ───────────────────────────────
if ground_truth:
    for s in STORIES:
        species = s.get("species_name", "")
        if species in ground_truth:
            s["ground_truth"] = ground_truth[species]

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs("./outputs/phase6_rq13", exist_ok=True)
    print(f"\n{'='*50}")
    print(f"  EcoMyth-VLM RQ13 Annotation Tool")
    print(f"  Stories loaded : {len(STORIES)}")
    print(f"  Already done   : {len(done_indices)}/100")
    print(f"  Remaining      : {100 - len(done_indices)}/100")
    print(f"  Output         : {OUTPUT_CSV}")
    print(f"{'='*50}")
    print(f"\n  Open in browser: http://localhost:{PORT}\n")
    app.run(port=PORT, debug=False)

"""
sample_100.py
Stratified sample of 100 stories from phase6_annotation_stories.json.
Balanced across 10 models x 4 formats (~2-3 per cell).
Ensures serial_number field exists — required by annotation tool.
Output: outputs/phase6_rq13/rq13_stories.json
"""

import json, random, os
from collections import defaultdict

random.seed(42)

INPUT  = "./outputs/phase6/phase6_annotation_stories.json"
OUTPUT = "./outputs/phase6_rq13/rq13_stories.json"
N      = 100

os.makedirs("./outputs/phase6_rq13", exist_ok=True)

with open(INPUT, "r", encoding="utf-8") as f:
    all_stories = json.load(f)

print(f"Total stories loaded: {len(all_stories)}")

# Ensure serial_number exists — HTML tool keys on this for save/resume
for i, s in enumerate(all_stories):
    if not s.get("serial_number"):
        s["serial_number"] = s.get("manifest_id") or f"story_{i:05d}"

# Strata: model x format
strata = defaultdict(list)
for story in all_stories:
    key = (story.get("model_key", "unknown"), story.get("format", "unknown"))
    strata[key].append(story)

print(f"Strata: {len(strata)}")
for k in sorted(strata.keys()):
    print(f"  {k[0]:25s} | {k[1]:15s} | {len(strata[k]):5d}")

# Stratified sample
per_cell  = N // len(strata)
remainder = N - per_cell * len(strata)
sampled   = []

for i, key in enumerate(sorted(strata.keys())):
    n = min(per_cell + (1 if i < remainder else 0), len(strata[key]))
    sampled.extend(random.sample(strata[key], n))

# Top up if needed
if len(sampled) < N:
    done_ids = {s["serial_number"] for s in sampled}
    extras   = [s for s in all_stories if s["serial_number"] not in done_ids]
    random.shuffle(extras)
    sampled.extend(extras[:N - len(sampled)])

sampled = sampled[:N]
random.shuffle(sampled)

# Check
check = defaultdict(int)
for s in sampled:
    check[(s.get("model_key","?"), s.get("format","?"))] += 1

print(f"\nFinal sample: {len(sampled)} stories")
for k in sorted(check): print(f"  {k[0]:25s} | {k[1]:15s} | {check[k]}")

missing_sn  = sum(1 for s in sampled if not s.get("serial_number"))
missing_txt = sum(1 for s in sampled if not (
    s.get("generated_text") or s.get("story_text") or s.get("text")))
print(f"\nMissing serial_number: {missing_sn}")
print(f"Missing text field:    {missing_txt}")

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(sampled, f, indent=2, ensure_ascii=False)

print(f"\nSaved to {OUTPUT}")
print("Next: python rq13_server.py")

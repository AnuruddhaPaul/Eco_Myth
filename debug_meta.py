"""Minimal test: reproduce the meta-tensor init path without loading weights."""
import sys, os, traceback
sys.path.insert(0, r"c:\Users\PC\Desktop\Programs\Eco_Myth")
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import torch
from accelerate import init_empty_weights

MODEL_PATH = r"c:\Users\PC\Desktop\Programs\Eco_Myth\models\Phi-4-multimodal-instruct"

# Load config only (fast)
from transformers import AutoConfig
print("Loading config...")
cfg = AutoConfig.from_pretrained(MODEL_PATH, trust_remote_code=True)
print(f"  Config OK: {cfg.__class__.__name__}")

# Now mimic what from_pretrained does: run __init__ inside init_empty_weights()
print("Running model __init__ inside init_empty_weights()...")
try:
    # import the custom model class
    from transformers.dynamic_module_utils import get_class_from_dynamic_module
    model_cls_name = "Phi4MMForCausalLM"

    # Directly import from the local file
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "modeling_phi4mm",
        os.path.join(MODEL_PATH, "modeling_phi4mm.py")
    )
    mod = importlib.util.load_from_spec = importlib.util.module_from_spec(spec)
    sys.modules["modeling_phi4mm"] = mod
    spec.loader.exec_module(mod)
    Phi4MMForCausalLM = mod.Phi4MMForCausalLM

    with init_empty_weights():
        model = Phi4MMForCausalLM(cfg)
    print("  __init__ completed successfully!")
    print(f"  Params on meta: {sum(1 for p in model.parameters() if p.is_meta)}")
except Exception:
    print("  FAILED:")
    traceback.print_exc()

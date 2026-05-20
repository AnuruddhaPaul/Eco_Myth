"""Quick diagnostic: load Phi-4-MM and print full traceback on failure."""
import sys, os, traceback
sys.path.insert(0, r"c:\Users\PC\Desktop\Programs\Eco_Myth")

import torch
from transformers import AutoProcessor, BitsAndBytesConfig, AutoModelForCausalLM

MODEL_PATH = r"c:\Users\PC\Desktop\Programs\Eco_Myth\models\Phi-4-multimodal-instruct"

BNB_4BIT = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
)

print("Loading processor...")
try:
    proc = AutoProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True)
    print("  Processor OK")
except Exception:
    print("  PROCESSOR FAILED:")
    traceback.print_exc()
    sys.exit(1)

print("Loading model...")
try:
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        quantization_config=BNB_4BIT,
        device_map="auto",
        dtype=torch.bfloat16,
        trust_remote_code=True,
        _attn_implementation="eager",
    )
    print("  Model loaded successfully!")
    print(f"  Device map: {model.hf_device_map}")
    raise KeyboardInterrupt("Model loaded — stopping as requested.")
except KeyboardInterrupt:
    raise
except Exception:
    print("  MODEL FAILED:")
    traceback.print_exc()
    sys.exit(1)

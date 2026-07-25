from llama_cpp import Llama
import json
import os

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Qwen2.5-3B-Instruct.Q4_K_M.gguf")
_first_call = True

llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=4096,        # matches our training max_seq_length
    n_threads = os.cpu_count() or 4,     # adjust to your CPU core count
    verbose=False,
    last_n_tokens_size=0
)

SYSTEM_INSTRUCTIONS = """You are a digital forensics assistant. You will be given a raw JSON artifact
(extracted file metadata OR a browser artifact record: cookie, transport-security entry, or
NEL record) from a forensic evidence extraction tool.

Your job: analyze it and output ONLY a JSON object with exactly these top-level fields:

{
  "entities": {
    "ips": [],
    "domains": [],
    "emails": [],
    "hashes": [],
    "urls": [],
    "usernames": [],
    "person_names": [],
    "phone_numbers": [],
    "addresses": []
  },
  "classification": {
    "risk": "benign" | "suspicious" | "malicious",
    "reason": "short justification, 1-3 sentences, specific to this artifact"
  },
  "artifact_summary": "one or two sentence human-readable summary of this artifact for an investigator"
}

Rules:
- Output ONLY the JSON object above. No markdown fences, no preamble, no explanation outside the JSON.
- Leave entity arrays empty ([]) if nothing of that type is present. Do not invent values.
- "reason" MUST reference at least one specific field/value from the input (e.g. a filename, timestamp, tool name, size, or attribute actually present in the artifact). NEVER use generic filler phrases like "no suspicious indicators", "metadata consistent", or "no signs of tampering" on their own -- if the file is unremarkable, say what specifically makes it unremarkable (e.g. "modified and created timestamps are 13 seconds apart, consistent with normal editing/save behavior" rather than just "no signs of tampering").
- Use "suspicious" or "malicious" only when there is a concrete indicator (e.g. typosquatting,
  known-bad TLD pattern, timestamp anomalies, hidden+system attributes on unexpected files,
  abnormal expiry dates, mismatched tool provenance). Default to "benign" when nothing stands out.
- ctime (NTFS file creation record) commonly becomes LATER than the modified timestamp whenever a
  file is copied, downloaded, extracted, or moved to a new location/drive -- this is normal filesystem
  behavior, NOT inherently suspicious by itself. Do not flag "ctime after modified" alone as suspicious.
  Only flag timestamp patterns when combined with additional concrete indicators (e.g. hidden+system
  attributes on an unexpected file type, a typosquatted filename, an executable in a sensitive system
  directory, or a modified timestamp that is itself impossible/inconsistent, such as predating the
  software/tool that created it).`
- For hashed/opaque domain fields (e.g. Chrome HSTS SHA256-hashed domains), put the hash value in
  "hashes", not "domains".
- CRITICAL: only include values in "entities" that literally, verbatim appear in the input artifact. NEVER invent, guess, or fabricate hashes, IPs, domains, or any other identifier that is not explicitly present in the given input. If a hash/IP/etc field is not present in the input, leave the corresponding array empty -- do not fill it with a plausible-looking placeholder.
- Filename-based typosquatting (character substitution, added/removed letters, homoglyphs mimicking a legitimate system process or brand name) is a strong indicator on its own, independent of NTFS attributes. Flag it even when hidden/system/archive attributes look otherwise normal.
"""

alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
"""
def truncate_large_fields(artifact: dict, max_chars: int = 3000) -> dict:
    """Truncate any string field (e.g. 'content', 'preview') that's too long,
    so a single huge file doesn't blow past the model's context limit."""
    cleaned = dict(artifact)
    for key, val in cleaned.items():
        if isinstance(val, str) and len(val) > max_chars:
            cleaned[key] = val[:max_chars] + f"... [truncated, original length {len(val)} chars]"
    return cleaned


EXCLUDE_FIELDS = {"artifact_embedding", "preview"}

def analyze_artifact(artifact: dict) -> dict:
    global _first_call  #to prevent cache leaks

    if _first_call:
        llm.reset()
        _first_call = False

    llm.reset()

    cleaned = {k: v for k, v in artifact.items() if k not in EXCLUDE_FIELDS}
    prompt = alpaca_prompt.format(
        SYSTEM_INSTRUCTIONS,
        json.dumps(truncate_large_fields(cleaned), ensure_ascii=False)
    )

    output = llm(prompt, max_tokens=400, stop=["<|im_end|>"], temperature=0.1)
    text = output["choices"][0]["text"].strip()

    result = extract_first_json(text)
    if result is not None:
        return result
    else:
        return {"error": "model output was not valid JSON", "raw_output": text}


def extract_first_json(raw_text: str):
    """
    Finds and parses the first complete, valid JSON object in raw_text,
    ignoring any trailing text the model may have generated afterward.
    Returns None if no valid JSON object is found.
    """
    decoder = json.JSONDecoder()
    idx = raw_text.find("{")
    if idx == -1:
        return None
    try:
        obj, _ = decoder.raw_decode(raw_text, idx)
        return obj
    except json.JSONDecodeError:
        return None


# # Example usage:
# result = analyze_artifact(truncate_large_fields(metadata))
# print(result)
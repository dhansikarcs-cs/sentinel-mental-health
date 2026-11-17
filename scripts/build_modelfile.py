"""Build a Modelfile for the Sentinel Ollama model from scripts/sentinel_prompt.md.

Source of truth for behavior is the prompt file, NOT model weights.
Run:  python scripts/build_modelfile.py  ->  writes scripts/Modelfile
Then: ollama create sentinel -f scripts/Modelfile

Base model: dolphin-mistral (local, chat-specialized Mistral 7B).
Refresher: how to clear a bad prior build —
    ollama cp sentinel sentinel-copied_bad_tag   (keep a snapshot)
    ollama rm sentinel                           (remove, so create is clean)
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPT_FILE = os.path.join(HERE, "sentinel_prompt.md")
MODELFILE = os.path.join(HERE, "Modelfile")
BASE_MODEL = "dolphin-mistral:latest"


def _section(text: str, name: str) -> str:
    match = re.search(rf"^## {name}\n(.*?)\n## END", text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"Missing section ## {name} in {PROMPT_FILE}")
    return match.group(1).strip()


def _fewshot(text: str) -> list[tuple[str, str]]:
    pairs = []
    blocks = re.split(r"^### user\n", text, flags=re.MULTILINE)[1:]
    for block in blocks:
        m = re.match(r"(.*?)\n### assistant\n(.*)", block, re.DOTALL)
        if m:
            pairs.append((m.group(1).strip(), m.group(2).strip()))
    return pairs


def esc(content: str) -> str:
    return content.replace("\\", "\\\\").replace('"', '\\"')


def main() -> None:
    with open(PROMPT_FILE, encoding="utf-8") as f:
        doc = f.read()

    system = _section(doc, "SYSTEM")
    patient = _section(doc, "PATIENT_JOURNAL_SUMMARY")
    clinical = _section(doc, "CLINICAL_JOURNAL_SUMMARY")
    notes = _section(doc, "NOTE_SYNTHESIS")
    fewshot = _fewshot(doc)

    modelfile_lines = [
        f"FROM {BASE_MODEL}",
        "",
        'SYSTEM """' + system + '"""',
        "",
        "PARAMETER temperature 0.3",
        "PARAMETER top_p 0.9",
        "PARAMETER num_ctx 4096",
        "",
        "# Sentinel prompt-training few-shots (curated, synthetic, non-clinical)",
        "# Sub-prompts baked in for exact-voice reference:",
        '#   PATIENT  """' + patient + '"""',
        '#   CLINICAL """' + clinical + '"""',
        '#   NOTES    """' + notes + '"""',
        "",
    ]

    for role, content in fewshot:
        modelfile_lines.append(f'MESSAGE {role} "{esc(content)}"')

    with open(MODELFILE, "w", encoding="utf-8") as f:
        f.write("\n".join(modelfile_lines))

    print(f"Modelfile written to {MODELFILE} (base={BASE_MODEL}, fewshots={len(fewshot)})")


if __name__ == "__main__":
    main()
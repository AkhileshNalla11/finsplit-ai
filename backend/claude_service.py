"""Claude-backed natural language bill parsing.

Claude does ONE job here: read the plain-English story and EXTRACT its structure
(people, items, who shared each item, how each item splits). All arithmetic is
done deterministically in `calculator.compute_split`, so the result always
balances and never depends on the model's math.

Two operations:
  - parse_split(description): extract structure → compute the split.
  - apply_correction(...): re-extract with a plain English correction → recompute.

Both call Claude, expect raw JSON back, and retry once with a stricter
instruction if the first response is not valid JSON.
"""

import base64
import json
import logging
import os
import re

import anthropic
import httpx

import calculator

logger = logging.getLogger(__name__)

# ── Anthropic (primary) ────────────────────────────────────────────────────────
# Claude only EXTRACTS structure; all math is in calculator.py. Haiku is enough.
# Override with CLAUDE_MODEL env var to use Sonnet for hard descriptions.
MODEL = os.environ.get("CLAUDE_MODEL") or "claude-haiku-4-5"

# ── OpenRouter (temporary testing override) ────────────────────────────────────
# Set USE_OPENROUTER=true + OPENROUTER_API_KEY to route through OpenRouter instead
# of the Anthropic API. All Anthropic credentials are kept untouched.
# IMPORTANT: these are read lazily (inside functions) so they're resolved AFTER
# load_dotenv() runs in main.py — not at module import time.

def _openrouter_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY") or ""

def _openrouter_model() -> str:
    return os.environ.get("OPENROUTER_MODEL") or "anthropic/claude-haiku-3-5"

# Extraction-only output is compact; no extended thinking needed.
MAX_TOKENS = 4096

# Short system preamble framing the role; a stricter variant is reused on retry.
# The actual task lives in the user-facing prompt templates below (verbatim per spec).
_SYSTEM = "You are a meticulous bill-splitting assistant. You always return raw, valid JSON only."
_SYSTEM_STRICT = (
    "You are a meticulous bill-splitting assistant. "
    "Return ONLY raw JSON. No markdown code fences, no prose, no explanation "
    "before or after. The response must be parseable by json.loads()."
)

SPLIT_PROMPT = """You are a bill-splitting assistant. Read this natural language description of a group meal or outing and EXTRACT its structure. Do NOT do any arithmetic — a separate calculator computes every amount. Just identify the people, each charge, who shared it, and how it should split.

Description: "{description}"

Rules:
- Identify every person mentioned.
- Create one item per distinct charge, with its total amount (read from the description) and the exact list of people who shared it.
- "split": use "equal" for almost everything — a charge divided evenly among the people who shared it (most food and drinks). Use "proportional" for a FIXED tax/service amount; set "sharedBy" to the people it applies to (usually everyone). NOTE: both tax and service charges are split EQUALLY among the people they apply to, not weighted by how much anyone ate.
- PERCENTAGE charges (e.g. "18% GST", "10% service charge", "15% tip") are special: do NOT compute the amount. Instead of "total", give "rate" (18% → 0.18) and "appliesTo" — the list of OTHER item labels this percentage is charged on (e.g. the food items, or "all" for the whole bill). Omit "sharedBy" and "split" for percentage items; the charge is split equally among everyone who consumed the base items.
- TIME-BASED shared costs (a hotel/booking/rental over several nights or days): if everyone is present the whole time, keep it as ONE item. ONLY if someone joins late or leaves early so the occupancy changes, split it into per-segment items (e.g. "Hotel night 1" shared by all, "Hotel nights 2-3" shared by those who stayed), each with its own total and sharers. The per-segment totals must add up to the original amount — never gift a segment or count any night twice.
- "category": classify each item as veg, nonveg, drinks, tax, or other.
- "payer": who actually fronted the money for THIS item. Use the person's name if one person paid for it (e.g. hotel paid by Kritik → "Kritik"; if one person paid the whole bill, put their name on every item — including every segment of a split booking). Use "self" when each person paid their own portion (e.g. "everyone paid for their own drinks") OR when the description doesn't say who paid.
- "coveredBy" (optional): use this for GIFTS/treats — when one person absorbs another's share with NO repayment expected (e.g. "Arjun covers Priya's share as a birthday treat", "the host treats everyone"). Keep the gifted person in "sharedBy" (they did consume it) and add "coveredBy" as a map of the gifted person → the giver, e.g. {{"Priya": "Arjun"}}. The gifted person then owes nothing for that item and the giver bears it. This is DIFFERENT from "payer": payer is a loan that gets repaid via settlement; coveredBy is a gift with no repayment.
- "assumptions": explain how you interpreted the description (who ate what, which charges are percentages/proportional, who paid, any gifts) so the user can verify your reading. Do NOT include computed amounts — the breakdown table shows those.

Return ONLY valid JSON, no markdown, no explanation outside the JSON:
{{
  "people": ["name1", "name2"],
  "items": [
    {{
      "label": "item name",
      "total": 0,
      "sharedBy": ["name1", "name2"],
      "category": "veg|nonveg|drinks|tax|other",
      "split": "equal|proportional",
      "payer": "name1 or self",
      "coveredBy": {{"name2": "name1"}}
    }},
    {{
      "label": "GST",
      "rate": 0.18,
      "appliesTo": ["item label 1", "item label 2"],
      "category": "tax",
      "payer": "name1 or self"
    }}
  ],
  "assumptions": ["assumption 1", "assumption 2"],
  "oneLiner": "one sentence plain English summary of the key splitting logic"
}}"""

CORRECTION_PROMPT = """You are a bill-splitting assistant. The user wants to correct a previous split. Re-EXTRACT the structure with the correction applied. Do NOT do any arithmetic — a separate calculator computes every amount.

Original description: "{original_description}"
Previous split: {previous_result}
User correction: "{correction}"

Apply the correction and return the updated structure in the same shape. If the correction changes how a charge is split (e.g. "split the tax equally"), set that item's "split" accordingly ("equal" or "proportional") and adjust its "sharedBy". If it changes who paid (e.g. "actually Kritik paid for the hotel"), update the "payer" on the relevant items ("self" if each paid their own). For a gift/treat where someone covers another's share with no repayment, use "coveredBy" ({{gifted person: giver}}). For a multi-night booking where someone joins late or leaves early, split it into per-segment items whose totals add up to the original (never gift a segment or double-count). Percentage charges keep "rate" + "appliesTo" instead of "total" — do not compute their amount.

Return ONLY valid JSON, no markdown:
{{
  "people": ["name1", "name2"],
  "items": [
    {{
      "label": "item name",
      "total": 0,
      "sharedBy": ["name1", "name2"],
      "category": "veg|nonveg|drinks|tax|other",
      "split": "equal|proportional",
      "payer": "name1 or self",
      "coveredBy": {{"name2": "name1"}}
    }},
    {{
      "label": "GST",
      "rate": 0.18,
      "appliesTo": ["item label 1"],
      "category": "tax",
      "payer": "name1 or self"
    }}
  ],
  "assumptions": ["assumption 1"],
  "oneLiner": "one sentence plain English summary of the key splitting logic"
}}"""


class ClaudeError(Exception):
    """Raised when Claude fails to produce a usable split after a retry."""


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ClaudeError("ANTHROPIC_API_KEY is not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _extract_json(text: str) -> dict:
    """Parse model output into a dict, tolerating stray markdown fences."""
    cleaned = text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences if the model added them.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    return json.loads(cleaned)


def _use_openrouter() -> bool:
    """True only when both the flag is set AND a key is present. Read at call time."""
    flag = (os.environ.get("USE_OPENROUTER") or "").lower() in ("1", "true", "yes")
    key = _openrouter_key()
    if flag and not key:
        logger.warning("USE_OPENROUTER=true but OPENROUTER_API_KEY is not set — falling back to Anthropic.")
        return False
    return flag and bool(key)


def _call_anthropic(prompt: str, strict: bool) -> str:
    """Existing Anthropic SDK path — unchanged."""
    client = _get_client()
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=_SYSTEM_STRICT if strict else _SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as exc:
        logger.error("Anthropic API error: %s", exc)
        raise ClaudeError(f"Anthropic API call failed: {exc}") from exc
    return "".join(block.text for block in message.content if block.type == "text")


def _call_openrouter(prompt: str, strict: bool) -> str:
    """OpenRouter via OpenAI-compatible chat/completions endpoint (no new deps — uses httpx)."""
    system = _SYSTEM_STRICT if strict else _SYSTEM
    payload = {
        "model": _openrouter_model(),
        "max_tokens": MAX_TOKENS,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {_openrouter_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://finsplit.ai",   # OpenRouter asks for a referrer
        "X-Title": "FinSplit AI",
    }
    try:
        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=90,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("OpenRouter HTTP error %s: %s", exc.response.status_code, exc.response.text[:300])
        raise ClaudeError(f"OpenRouter API call failed ({exc.response.status_code})") from exc
    except httpx.RequestError as exc:
        logger.error("OpenRouter request error: %s", exc)
        raise ClaudeError(f"OpenRouter request error: {exc}") from exc
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        logger.error("Unexpected OpenRouter response shape: %s", data)
        raise ClaudeError("OpenRouter returned an unexpected response shape") from exc


def _call(prompt: str, strict: bool = False) -> str:
    """Route to OpenRouter or Anthropic depending on env config."""
    if _use_openrouter():
        logger.info("Using OpenRouter (%s)", _openrouter_model())
        return _call_openrouter(prompt, strict)
    return _call_anthropic(prompt, strict)


def _extract_with_retry(prompt: str) -> dict:
    """Call Claude, parse JSON, retry once with a stricter instruction on failure."""
    try:
        return _extract_json(_call(prompt, strict=False))
    except json.JSONDecodeError:
        logger.warning("Claude returned malformed JSON; retrying with strict prompt.")
        try:
            return _extract_json(_call(prompt, strict=True))
        except json.JSONDecodeError as exc:
            logger.error("Claude returned malformed JSON on retry: %s", exc)
            raise ClaudeError("Claude did not return valid JSON after retry") from exc


def _compute(extraction: dict) -> dict:
    """Run the deterministic calculator, surfacing bad structure as a ClaudeError."""
    try:
        return calculator.compute_split(extraction)
    except ValueError as exc:
        logger.error("Could not compute split from extraction: %s", exc)
        raise ClaudeError(f"Could not compute split: {exc}") from exc


def extract_from_image(image_bytes: bytes, media_type: str) -> str:
    """Use Claude Vision to read a receipt and return a plain English item list."""
    client = _get_client()
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
    prompt = (
        "Read this receipt image carefully. "
        "List every line item with its price, and any taxes, service charges, or tips. "
        "Output plain English only — no JSON, no markdown, no extra commentary. Be concise."
    )
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
    except anthropic.APIError as exc:
        logger.error("Anthropic API error reading receipt: %s", exc)
        raise ClaudeError(f"Failed to read receipt image: {exc}") from exc
    return "".join(block.text for block in message.content if block.type == "text").strip()


def parse_split(description: str) -> dict:
    extraction = _extract_with_retry(SPLIT_PROMPT.format(description=description))
    return _compute(extraction)


def apply_correction(original_description: str, previous_result: dict, correction: str) -> dict:
    prompt = CORRECTION_PROMPT.format(
        original_description=original_description,
        previous_result=json.dumps(previous_result, ensure_ascii=False),
        correction=correction,
    )
    extraction = _extract_with_retry(prompt)
    return _compute(extraction)

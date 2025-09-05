# agents/chat_moderator.py
"""
ChatModerationAgent that returns:
{ "status": "<CapitalizedStatus>", "reason": "<short reason>", "description": "<longer description>" }

- Uses rule-based detection for status.
- Uses optional LLM (callable) to generate reason + description.
- Redacts PII before calling LLM and instructs LLM not to output PII.
"""

import re
from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel

# detection input model (used by FastAPI)
class ModerateInput(BaseModel):
    message: str
    sender_role: Optional[str] = "buyer"
    metadata: Optional[Dict[str, Any]] = None


class ChatModerationAgent:
    PHONE_PATTERNS = [
        re.compile(r"\b\d{10}\b"),
        re.compile(r"\+91[-\s]?\d{10}"),
        re.compile(r"\b91[-\s]?\d{10}\b"),
        re.compile(r"\b\d{5}[-\s]?\d{5}\b"),
        re.compile(r"\b\+?[0-9]{7,15}\b"),
    ]

    PROFANITY = {
        "idiot", "stupid", "bastard", "fuck",
        "motherfucker", "damn", "asshole", "chutiya", "gandu"
    }

    URL_PATTERN = re.compile(r"https?://\S+|www\.\S+|\b[a-z0-9.-]+\.(com|in|net|org|co|io|me)\b", flags=re.IGNORECASE)
    REPEATED_CHAR_PATTERN = re.compile(r"(.)\1{7,}", flags=re.DOTALL)

    PAYMENT_KEYWORDS = [
        "upi", "paytm", "phonepe", "gpay", "bank account", "ifsc",
        "transfer money", "send ₹", "send rs", "send rs.", "payment", "pay now"
    ]

    STATUS_MAP = {
        "abusive": ("Abusive", "Contains insulting language"),
        "spam": ("Spam", "Message looks like spam or scam"),
        "flagged_for_phone": ("Unsafe", "Contains a phone number"),
        "flagged": ("Flagged", "Contains content that needs review"),
        "safe": ("Safe", "No issues detected"),
    }

    def __init__(self, llm_client: Optional[Callable[[str], str]] = None):
        """
        llm_client: callable(prompt: str) -> str (or None)
        """
        self.llm = llm_client

    # ------ core detector (same logic you had) ------
    def _detailed_moderation(self, message: str) -> Dict[str, Any]:
        msg = (message or "").strip()
        lower = msg.lower()
        labels: List[str] = []
        reasons: List[str] = []

        # phones
        phones_found: List[str] = []
        for pat in self.PHONE_PATTERNS:
            found = pat.findall(msg)
            for f in found:
                if isinstance(f, tuple):
                    f = next((x for x in f if x), "")
                if f:
                    phones_found.append(re.sub(r"[^\d\+]", "", f))
        if phones_found:
            labels.append("contains_phone")
            reasons.append("Phone-like pattern(s) detected")

        # urls
        urls = self.URL_PATTERN.findall(msg)
        urls_norm = []
        for u in urls:
            if isinstance(u, tuple):
                urls_norm.append(next((p for p in u if p), ""))
            else:
                urls_norm.append(u)
        urls_norm = [u for u in urls_norm if u]
        if urls_norm:
            labels.append("contains_url")
            reasons.append("URL or domain detected")
            if len(msg.split()) <= 6:
                labels.append("possible_spam")
                reasons.append("Short message with URL → possible spam")

        # profanity
        profane_matches: List[str] = []
        for word in self.PROFANITY:
            if re.search(rf"\b{re.escape(word)}\b", lower):
                profane_matches.append(word)
        if profane_matches:
            labels.append("abusive")
            reasons.append("Profanity or insulting language found")

        # repeated char spam
        if self.REPEATED_CHAR_PATTERN.search(msg):
            labels.append("possible_spam")
            reasons.append("Repeated characters (spam-like)")

        # payment terms
        payment_hits = [k for k in self.PAYMENT_KEYWORDS if k in lower]
        if payment_hits:
            labels.append("payment_request")
            reasons.append("Message requests payment or transfer")

        # decide final status token
        if "abusive" in labels:
            final_decision = "abusive"
        elif "possible_spam" in labels:
            final_decision = "spam"
        elif "contains_phone" in labels and labels == ["contains_phone"]:
            final_decision = "flagged_for_phone"
        elif labels:
            final_decision = "flagged"
        else:
            final_decision = "safe"

        return {
            "agent": "chat_moderation",
            "status": final_decision,
            "labels": labels,
            "reason": " | ".join(reasons) if reasons else "No issues detected.",
            "original_message": message,
            "matches": {
                "phones": phones_found,
                "urls": urls_norm,
                "profanity": profane_matches,
                "payment_terms": payment_hits,
            },
        }

    # ------ redact PII for safe LLM prompt ------
    def _redact_for_prompt(self, text: str) -> str:
        # replace phone-like sequences with [PHONE], URLs with [URL]
        t = text
        # redact phones
        for pat in self.PHONE_PATTERNS:
            t = pat.sub("[PHONE]", t)
        # redact URLs
        t = self.URL_PATTERN.sub("[URL]", t)
        return t

    # ------ call LLM to get reason & description ------
    def _generate_llm_explanation(self, detailed: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Returns {"reason": "<short reason>", "description":"<longer description>"} or None
        """
        if not self.llm:
            return None

        status = detailed.get("status", "flagged")
        labels = detailed.get("labels", [])
        matches = detailed.get("matches", {})

        # Build non-PII observation text
        observed_parts = []
        if matches.get("phones"):
            observed_parts.append(f"{len(matches['phones'])} phone-like pattern(s)")
        if matches.get("urls"):
            observed_parts.append(f"{len(matches['urls'])} URL(s)")
        if matches.get("profanity"):
            observed_parts.append("insulting language")
        if matches.get("payment_terms"):
            observed_parts.append("payment request")
        observed = ", ".join(observed_parts) if observed_parts else "no explicit matches"

        # Prepare a safe, short prompt (explicit no-PII instruction)
        prompt = (
            "You are a concise moderation assistant. Produce two outputs in JSON form only:\n"
            '{ "reason": "<one short sentence, <=20 words>", "description": "<2-3 sentence explanation (no PII)>" }\n\n'
            "IMPORTANT: Do NOT include or repeat any phone numbers, emails, or full URLs. "
            "If PII exists, generalize as 'phone number' or 'URL'.\n\n"
            f"Detection summary: status={status}, observed={observed}, labels={labels}\n"
            f"Redacted user message: {self._redact_for_prompt(detailed.get('original_message',''))}\n\n"
            "Write a helpful, factual reason (one short sentence) and a slightly longer description (2-3 sentences)."
        )


        # Redact the original message when including sample context (we avoid including PII)
        # but keep the high-level observed summary above (we already did).
        try:
            raw = self.llm(prompt)
        except Exception:
            return None

        if not raw:
            return None

        # Try to extract JSON-like reason & description via regex
        text = raw.strip()
        # Try find JSON fields
        m_reason = re.search(r'"reason"\s*:\s*"([^"]{1,400}?)"', text)
        m_desc = re.search(r'"description"\s*:\s*"([^"]{1,2000}?)"', text)
        if m_reason and m_desc:
            return {"reason": m_reason.group(1).strip(), "description": m_desc.group(1).strip()}

        # If model returned plain text, heuristically split into short + long:
        # - If multiple lines, first line -> reason, rest -> description
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if len(lines) >= 2:
            return {"reason": lines[0], "description": " ".join(lines[1:])}
        if len(lines) == 1:
            # Use first sentence as reason, whole line as description
            first_sentence = re.split(r"[.!?]\s+", lines[0])[0]
            return {"reason": first_sentence, "description": lines[0]}

        # fallback: none
        return None

    # ------ public API: returns status + reason + description (LLM-powered if available) ------
    def moderate(self, message: str) -> Dict[str, Any]:
        """
        Returns:
          {
            "status": "<CapitalizedStatus>",
            "reason": "<short reason>",
            "description": "<longer description>",
            "matches": { "phones": [...], "urls": [...], "payment_terms": [...] }  # only if found
          }
        """
        detailed = self._detailed_moderation(message)
        status_key = detailed.get("status", "flagged")
        capital, fallback_reason = self.STATUS_MAP.get(
            status_key, ("Flagged", "Contains content that needs review")
        )

        # include the redacted original for LLM context
        redacted_msg = self._redact_for_prompt(message)
        detailed["redacted_message"] = redacted_msg

        # Try LLM for explanation (safe prompt + redaction done)
        llm_out = self._generate_llm_explanation(detailed)
        if llm_out:
            reason = llm_out.get("reason", fallback_reason)
            description = llm_out.get("description", detailed.get("reason", fallback_reason))
        else:
            reason = fallback_reason
            description = detailed.get("reason", fallback_reason)

        # return only matches that actually exist
        matches = {}
        for key in ["phones", "urls", "payment_terms"]:
            if detailed["matches"].get(key):
                matches[key] = detailed["matches"][key]

        return {
            "status": capital,
            "reason": reason,
            "description": description,
            "matches": matches,
        }

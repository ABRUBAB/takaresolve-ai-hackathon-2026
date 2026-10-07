"""PII scrubbing before text is sent to the LLM (AI-7 live mode), in English, Bangla and Banglish."""
import pytest
from uvera_ml.brief.pii import scrub, scrub_obj


@pytest.mark.parametrize("text, expected, kind", [
    ("Call me at +8801712345678 now", "Call me at [PHONE] now", "PHONE"),
    ("number 01812-345678 ok", "number [PHONE] ok", "PHONE"),
    ("8801912345678 and +880 1712 345678", "[PHONE] and [PHONE]", "PHONE"),
    ("আমার নম্বর ০১৭১২৩৪৫৬৭৮, টাকা পাঠান", "আমার নম্বর [PHONE], টাকা পাঠান", "PHONE"),
    ("bhai 01712345678 e bikash koren", "bhai [PHONE] e bikash koren", "PHONE"),
    ("NID 1234567890 ditei hobe", "NID [NID] ditei hobe", "NID"),
    ("জাতীয় পরিচয়পত্র ১৯৯০১২৩৪৫৬৭৮৯", "জাতীয় পরিচয়পত্র [NID]", "NID"),
    ("old NID 19901234567890123.", "old NID [NID].", "NID"),
    ("card 4111 1111 1111 1111 please", "card [CARD] please", "CARD"),
    ("card 4111-1111-1111-1111", "card [CARD]", "CARD"),
    ("card 4111111111111111", "card [CARD]", "CARD"),
    ("mail me: rahim.uddin+test@example.com", "mail me: [EMAIL]", "EMAIL"),
    ("go to https://bkash-help.xyz/login?id=1 now", "go to [URL] now", "URL"),
    ("visit www.free-gift.top today", "visit [URL] today", "URL"),
    ("লিংকে ক্লিক করুন bit.ly/3xYz", "লিংকে ক্লিক করুন [URL]", "URL"),
    ("Your OTP is 482913, do not share", "Your OTP is [OTP], do not share", "OTP"),
    ("আপনার ওটিপি কোড ৪৮২৯১৩ কাউকে বলবেন না", "আপনার ওটিপি কোড [OTP] কাউকে বলবেন না", "OTP"),
])
def test_scrub_replaces_pii(text, expected, kind):
    out, counts = scrub(text)
    assert out == expected
    assert counts.get(kind, 0) >= 1


@pytest.mark.parametrize("text", [
    "High scam risk. The receiver's wallet is 3 days old. Tk 5,000 is 80% of the balance.",
    "উচ্চ প্রতারণার ঝুঁকি। টাকা ৫,০০০, ৩ দিন পুরনো ওয়ালেট।",
    "Evidence R1, R2 and RULE1; policy card PC-03; CASE-0001 has 109 victims and Tk 1,234,567 at risk.",
    "Wallet C000123 sent to M00120 at 19:30.",
])
def test_scrub_keeps_amounts_ids_and_normal_text(text):
    assert scrub(text) == (text, {})


def test_scrub_obj_walks_nested_evidence():
    ev = {"kind": "pause_check", "amount_bdt": 5000, "customer_note": "call 01712345678 or mail a@b.co",
          "reasons": [{"id": "R1", "text_en": "New receiver", "text_bn": "নতুন প্রাপক ০১৮১২৩৪৫৬৭৮"}]}
    out, counts = scrub_obj(ev)
    assert out["customer_note"] == "call [PHONE] or mail [EMAIL]"
    assert out["reasons"][0]["text_bn"] == "নতুন প্রাপক [PHONE]"
    assert out["amount_bdt"] == 5000 and out["reasons"][0]["id"] == "R1"
    assert counts == {"PHONE": 2, "EMAIL": 1}
    assert ev["customer_note"].startswith("call 0171")  # the original is not modified


class FakeGemini:
    def __init__(self):
        self.prompts = []

    def json(self, prompt, schema, temperature=0.3, system=None):
        self.prompts.append(prompt)
        raise RuntimeError("offline test: fall back to the template")


def test_live_mode_sends_only_scrubbed_text_and_cached_mode_is_unchanged():
    from uvera_ml.serving.briefs import BriefEngine
    from uvera_ml.serving.store import ArtifactStore

    eng = BriefEngine(ArtifactStore(), mode="cached")
    eng.cache = {}
    fake = eng.gemini = FakeGemini()
    check = {"reasons": [{"text_en": "Receiver wallet is new", "text_bn": "নতুন ওয়ালেট"}], "calibrated_probability": 0.9,
             "risk_level": "high", "uncertainty_state": "confident", "human_review": "not_needed",
             "recommendation": ["verify_number"]}
    note = "Send to 01712345678, NID 1234567890, OTP 482913, see http://x.top/a or mail me@x.com"
    out = eng.for_transfer(check, 5000, note)
    assert out["source"] == "template"
    sent = fake.prompts[0]
    for secret in ("01712345678", "1234567890", "482913", "http://x.top/a", "me@x.com"):
        assert secret not in sent
    for tag in ("[PHONE]", "[NID]", "[OTP]", "[URL]", "[EMAIL]"):
        assert tag in sent
    assert eng.stats["pii_redactions"] == 5
    # the evidence kept for the response (and the cache key) is the original, unscrubbed one
    assert out["evidence_object"]["customer_note"] == note

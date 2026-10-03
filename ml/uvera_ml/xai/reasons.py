"""Turn exact TreeSHAP contributions (LightGBM pred_contrib) into plain-language reasons (English + Bangla).

The text only restates what the model's evidence says; it never adds new reasons.
"""
from __future__ import annotations

import numpy as np

REASON_TEXT = {
    "recipient_age_days": ("The receiving wallet is only {v:.0f} days old", "প্রাপকের ওয়ালেটটি মাত্র {v:.0f} দিন পুরোনো"),
    "recipient_in_count_7d": ("The receiver got {v:.0f} transfers in the last 7 days", "প্রাপক গত ৭ দিনে {v:.0f}টি লেনদেনে টাকা পেয়েছে"),
    "recipient_sender_days_7d": ("Many different people sent money to this receiver recently",
                                 "সম্প্রতি অনেক আলাদা মানুষ এই প্রাপককে টাকা পাঠিয়েছে"),
    "recipient_in_today_before": ("This receiver already got {v:.0f} transfers today", "এই প্রাপক আজই {v:.0f}টি লেনদেনে টাকা পেয়েছে"),
    "recipient_out_in_ratio_7d": ("Money sent to this receiver usually leaves quickly", "এই প্রাপকের কাছে আসা টাকা দ্রুত বের হয়ে যায়"),
    "recipient_cashout_count_7d": ("The receiver cashed out {v:.0f} times in 7 days", "প্রাপক ৭ দিনে {v:.0f} বার ক্যাশ আউট করেছে"),
    "amount_log": ("The amount is large for a transfer like this", "এই ধরনের লেনদেনের জন্য টাকার পরিমাণ বেশি"),
    "amount_z_30d": ("This is much more than you usually send", "আপনি সাধারণত যা পাঠান, এটি তার চেয়ে অনেক বেশি"),
    "amount_to_balance": ("This sends most of your balance", "এতে আপনার ব্যালেন্সের বেশিরভাগ চলে যাবে"),
    "first_time_pair": ("You have never sent money to this number before", "আপনি আগে কখনো এই নম্বরে টাকা পাঠাননি"),
    "cash_in_gap_min": ("Money was added to your wallet only {v:.0f} minutes ago", "মাত্র {v:.0f} মিনিট আগে আপনার ওয়ালেটে টাকা যোগ হয়েছে"),
    "device_change_72h": ("Your account was opened on a new device recently", "সম্প্রতি নতুন ডিভাইসে আপনার অ্যাকাউন্ট খোলা হয়েছে"),
    "pin_reset_72h": ("Your PIN was reset recently", "সম্প্রতি আপনার পিন রিসেট করা হয়েছে"),
    "sender_tenure_days": ("Your account is new", "আপনার অ্যাকাউন্টটি নতুন"),
    "sender_out_count_7d": ("Your activity this week is unusual", "এই সপ্তাহে আপনার লেনদেন অস্বাভাবিক"),
    "hour": ("Unusual time of day", "অস্বাভাবিক সময়"),
    "is_night": ("Late-night transfer", "গভীর রাতের লেনদেন"),
    "dow": ("Unusual day for this kind of transfer", "এই ধরনের লেনদেনের জন্য অস্বাভাবিক দিন"),
    "channel_ussd": ("Sent through USSD", "ইউএসএসডি দিয়ে পাঠানো"),
}


# Shown when a draft is LOW risk: the facts that pulled the score down (negative TreeSHAP), worded as what looked normal.
SAFE_TEXT = {
    "recipient_age_days": ("The receiving wallet has been open for {v:.0f} days", "প্রাপকের ওয়ালেটটি {v:.0f} দিন ধরে চালু আছে"),
    "recipient_in_count_7d": ("The receiver's incoming transfers look normal", "প্রাপকের কাছে আসা লেনদেন স্বাভাবিক"),
    "recipient_sender_days_7d": ("Few different people send money to this receiver", "খুব বেশি আলাদা মানুষ এই প্রাপককে টাকা পাঠায় না"),
    "recipient_in_today_before": ("The receiver has not had a rush of transfers today", "আজ প্রাপকের কাছে হঠাৎ অনেক লেনদেন আসেনি"),
    "recipient_out_in_ratio_7d": ("Money sent to this receiver does not leave quickly", "এই প্রাপকের কাছে আসা টাকা দ্রুত বের হয়ে যায় না"),
    "recipient_cashout_count_7d": ("The receiver rarely cashes out", "প্রাপক খুব কম ক্যাশ আউট করে"),
    "amount_log": ("The amount is small", "টাকার পরিমাণ কম"),
    "amount_z_30d": ("The amount is close to what you usually send", "আপনি সাধারণত যা পাঠান, পরিমাণটি তার কাছাকাছি"),
    "amount_to_balance": ("Most of your balance stays in your wallet", "আপনার ব্যালেন্সের বেশিরভাগই থেকে যাবে"),
    "first_time_pair": ("You have sent money to this number before", "আপনি আগেও এই নম্বরে টাকা পাঠিয়েছেন"),
    "cash_in_gap_min": ("No money was rushed in just before this", "এর ঠিক আগে তাড়াহুড়ো করে টাকা যোগ করা হয়নি"),
    "device_change_72h": ("No recent change of phone", "সম্প্রতি ফোন বদলানো হয়নি"),
    "pin_reset_72h": ("No recent PIN reset", "সম্প্রতি পিন রিসেট করা হয়নি"),
    "sender_tenure_days": ("Your account has been open for {v:.0f} days", "আপনার অ্যাকাউন্টটি {v:.0f} দিন ধরে চালু আছে"),
    "sender_out_count_7d": ("Your activity this week looks normal", "এই সপ্তাহে আপনার লেনদেন স্বাভাবিক"),
    "hour": ("A usual time of day", "স্বাভাবিক সময়"),
    "is_night": ("Not a late-night transfer", "গভীর রাতের লেনদেন নয়"),
    "dow": ("A usual day for this kind of transfer", "এই ধরনের লেনদেনের জন্য স্বাভাবিক দিন"),
    "channel_ussd": ("The channel used looks normal", "ব্যবহৃত মাধ্যম স্বাভাবিক"),
}


def _pick(contrib: np.ndarray, values: dict, features: list[str], k: int, lowers: bool) -> list[dict]:
    c = np.asarray(contrib[: len(features)], float)
    order = [i for i in np.argsort(c if lowers else -c) if (c[i] < 0 if lowers else c[i] > 0)][:k]
    table = SAFE_TEXT if lowers else REASON_TEXT
    out = []
    for i in order:
        f = features[i]
        v = values.get(f)
        en, bn = table.get(f, (f, f))
        try:
            en, bn = en.format(v=float(v)), bn.format(v=float(v))
        except (TypeError, ValueError):
            en, bn = en.replace(" {v:.0f}", ""), bn.replace(" {v:.0f}", "")
        out.append({"feature": f, "value": None if v is None or v != v else float(v), "contribution": float(c[i]),
                    "text_en": en, "text_bn": bn})
    return out


def top_reasons(contrib: np.ndarray, values: dict, features: list[str], k: int = 3) -> list[dict]:
    """contrib: one row of pred_contrib (len(features)+1, last = bias). Only reasons that RAISE risk are returned."""
    return _pick(contrib, values, features, k, lowers=False)


def safe_reasons(contrib: np.ndarray, values: dict, features: list[str], k: int = 3) -> list[dict]:
    """The k facts that LOWERED risk the most (negative contributions), for drafts the policy calls low risk."""
    return _pick(contrib, values, features, k, lowers=True)

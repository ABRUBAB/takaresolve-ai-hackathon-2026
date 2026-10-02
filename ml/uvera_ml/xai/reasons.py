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


def top_reasons(contrib: np.ndarray, values: dict, features: list[str], k: int = 3) -> list[dict]:
    """contrib: one row of pred_contrib (len(features)+1, last = bias). Only reasons that RAISE risk are returned."""
    c = np.asarray(contrib[: len(features)], float)
    order = [i for i in np.argsort(-c) if c[i] > 0][:k]
    out = []
    for i in order:
        f = features[i]
        v = values.get(f)
        en, bn = REASON_TEXT.get(f, (f, f))
        try:
            en, bn = en.format(v=float(v)), bn.format(v=float(v))
        except (TypeError, ValueError):
            en, bn = en.replace(" {v:.0f}", ""), bn.replace(" {v:.0f}", "")
        out.append({"feature": f, "value": None if v is None or v != v else float(v), "contribution": float(c[i]),
                    "text_en": en, "text_bn": bn})
    return out

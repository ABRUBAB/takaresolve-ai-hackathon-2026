"""AI-5 QR Shield features: one row per merchant per week, computed only from what an issuer can see."""
from __future__ import annotations

import numpy as np
import pandas as pd

from uvera_ml.sim.world import DAY, World

FEATURES = ["n_payments", "n_payers", "payments_per_payer", "one_time_payer_share", "first_time_share", "round_share",
            "amount_cv", "median_ticket", "ticket_ratio_category", "cashin_gap_share", "drain_share", "burst_share",
            "night_share", "cross_merchant_share", "repeat_payer_share", "peer_z_ticket", "peer_z_payers", "peer_z_round"]

REASON_TEXT = {
    "round_share": ("{v:.0%} of payments are round amounts (500/1,000/2,000…)", "{v:.0%} পেমেন্ট গোল অঙ্কের (৫০০/১,০০০/২,০০০…)"),
    "one_time_payer_share": ("{v:.0%} of payers paid once and never came back", "{v:.0%} ক্রেতা একবার পেমেন্ট করে আর ফেরেননি"),
    "first_time_share": ("{v:.0%} of payments come from first-time payers", "{v:.0%} পেমেন্ট প্রথমবারের ক্রেতাদের"),
    "cashin_gap_share": ("{v:.0%} of payments happen minutes after a cash-in", "{v:.0%} পেমেন্ট ক্যাশ-ইনের কয়েক মিনিট পরেই"),
    "drain_share": ("{v:.0%} of payers empty most of their wallet here", "{v:.0%} ক্রেতা এখানে প্রায় পুরো ব্যালেন্স খরচ করেন"),
    "burst_share": ("{v:.0%} of payments come in quick bursts from the same payer", "{v:.0%} পেমেন্ট একই ক্রেতার কাছ থেকে দ্রুত পরপর আসে"),
    "night_share": ("{v:.0%} of payments at unusual hours", "{v:.0%} পেমেন্ট অস্বাভাবিক সময়ে"),
    "cross_merchant_share": ("Payers also pay a few other shops with similar amounts", "ক্রেতারা অন্য কয়েকটি দোকানেও একই ধরনের অঙ্ক পাঠান"),
    "repeat_payer_share": ("A small group of payers pays again and again", "অল্প কয়েকজন ক্রেতা বারবার পেমেন্ট করেন"),
    "ticket_ratio_category": ("Average payment is {v:.1f}× the usual for this shop type", "গড় পেমেন্ট এই ধরনের দোকানের স্বাভাবিকের {v:.1f} গুণ"),
    "peer_z_ticket": ("Ticket size far from similar shops in the area", "এলাকার একই ধরনের দোকানের তুলনায় পেমেন্টের অঙ্ক অনেক আলাদা"),
    "peer_z_payers": ("Many more payers than similar shops", "একই ধরনের দোকানের চেয়ে অনেক বেশি ক্রেতা"),
    "peer_z_round": ("Far more round amounts than similar shops", "একই ধরনের দোকানের চেয়ে অনেক বেশি গোল অঙ্ক"),
}


def _robust_z(x: pd.Series) -> pd.Series:
    med = x.median()
    mad = (x - med).abs().median() * 1.4826
    return (x - med) / max(mad, 1e-6 + 0.05 * abs(med))


def build_qr_features(w: World) -> pd.DataFrame:
    ev = w.events
    qr = ev[(ev["etype"] == "qr_pay") & (ev["src_kind"] == 0) & (ev["dst_kind"] == 2)][
        ["t", "day", "src", "dst", "amount"]].rename(columns={"src": "payer", "dst": "merchant_id"}).copy()
    qr["week"] = qr["day"] // 7
    qr = qr.sort_values("t", kind="stable")
    a = qr["amount"].to_numpy(float)
    qr["is_round"] = ((a >= 500) & (np.mod(a, 500) == 0)).astype(np.int8)
    qr["night"] = (((qr["t"] % DAY) < 7 * 3600) | ((qr["t"] % DAY) >= 22 * 3600)).astype(np.int8)

    cin = ev.loc[(ev["etype"] == "cash_in") & (ev["dst_kind"] == 0), ["dst", "t"]].rename(columns={"dst": "payer", "t": "t_cin"})
    qr = pd.merge_asof(qr, cin.sort_values("t_cin"), left_on="t", right_on="t_cin", by="payer", direction="backward")
    qr["after_cashin"] = ((qr["t"] - qr["t_cin"]) <= 3600).fillna(False).astype(np.int8)

    dc = w.daily_customer.set_index(["customer_id", "day"])["balance_sod"]
    bal = dc.reindex(pd.MultiIndex.from_arrays([qr["payer"], qr["day"]])).to_numpy()
    qr["drain"] = (qr["amount"].to_numpy() >= 0.8 * np.nan_to_num(bal, nan=np.inf)).astype(np.int8)

    prev = qr.groupby(["payer", "merchant_id"])["t"].shift(1)
    qr["burst"] = ((qr["t"] - prev) <= 3600).fillna(False).astype(np.int8)
    nxt = qr.groupby(["payer", "merchant_id"])["t"].shift(-1)
    qr["burst"] = qr["burst"] | ((nxt - qr["t"]) <= 3600).fillna(False).astype(np.int8)
    qr["first_time"] = (qr.groupby(["payer", "merchant_id"]).cumcount() == 0).astype(np.int8)

    big = qr[qr["amount"] >= 700]
    n_shops = big.groupby(["payer", "week"])["merchant_id"].nunique().rename("payer_shops")
    qr = qr.join(n_shops, on=["payer", "week"])
    qr["multi_shop"] = (qr["payer_shops"].fillna(0) >= 2).astype(np.int8)
    pw = qr.groupby(["merchant_id", "week", "payer"]).size().rename("pw")
    qr = qr.join(pw, on=["merchant_id", "week", "payer"])
    qr["one_time"] = ((qr["pw"] == 1) & (qr["first_time"] == 1)).astype(np.int8)
    qr["repeat"] = (qr["pw"] >= 3).astype(np.int8)

    g = qr.groupby(["merchant_id", "week"])
    f = pd.DataFrame({
        "n_payments": g.size(),
        "n_payers": g["payer"].nunique(),
        "round_share": g["is_round"].mean(),
        "amount_cv": g["amount"].std().fillna(0) / g["amount"].mean(),
        "median_ticket": g["amount"].median(),
        "cashin_gap_share": g["after_cashin"].mean(),
        "drain_share": g["drain"].mean(),
        "burst_share": g["burst"].mean(),
        "night_share": g["night"].mean(),
        "first_time_share": g["first_time"].mean(),
        "cross_merchant_share": g["multi_shop"].mean(),
        "one_time_payer_share": g["one_time"].mean(),
        "repeat_payer_share": g["repeat"].mean(),
    }).reset_index()
    f["payments_per_payer"] = f["n_payments"] / f["n_payers"]
    mer = w.merchants.set_index("merchant_id")
    f["category"] = f["merchant_id"].map(mer["category"])
    f["zone"] = f["merchant_id"].map(mer["zone"])
    f["size"] = f["merchant_id"].map(mer["size"])
    cat_med = f.groupby(["category", "week"])["median_ticket"].transform("median")
    f["ticket_ratio_category"] = f["median_ticket"] / cat_med
    peer = f.groupby(["category", "zone", "week"])
    f["peer_z_ticket"] = peer["median_ticket"].transform(_robust_z).abs()
    f["peer_z_payers"] = peer["n_payers"].transform(_robust_z)
    f["peer_z_round"] = peer["round_share"].transform(_robust_z)
    f["peer_z_baseline"] = f[["peer_z_ticket", "peer_z_payers", "peer_z_round"]].clip(lower=0).sum(axis=1)
    f["volume"] = g["amount"].sum().to_numpy()

    truth = w.truth_merchants.set_index("merchant_id")
    f["is_disguised"] = f["merchant_id"].map(truth["is_disguised"]).astype(int)
    f["family"] = f["merchant_id"].map(truth["family"])
    f = f[f["n_payments"] >= 3].reset_index(drop=True)  # too few payments to judge a week
    return f

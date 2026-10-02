"""AI-1 Pause Check features. Every feature uses only information available BEFORE the transfer."""
from __future__ import annotations

import numpy as np
import pandas as pd

from uvera_ml.sim.world import DAY, World

SENDER = ["sender_tenure_days", "amount_log", "amount_z_30d", "amount_to_balance", "sender_out_count_7d",
          "cash_in_gap_min", "device_change_72h", "pin_reset_72h", "first_time_pair"]
RECIPIENT = ["recipient_age_days", "recipient_in_count_7d", "recipient_sender_days_7d", "recipient_in_today_before",
             "recipient_out_in_ratio_7d", "recipient_cashout_count_7d"]
CONTEXT = ["hour", "is_night", "dow", "channel_ussd"]
FEATURES = SENDER + RECIPIENT + CONTEXT
GROUPS = {"sender": SENDER, "recipient": RECIPIENT, "context": CONTEXT}
SLICE_COLS = ["zone", "channel", "tenure_bucket", "language", "segment"]


def _cidx(ids: pd.Series) -> np.ndarray:
    return ids.str.slice(1).astype(np.int64).to_numpy()


def _prev_sum(mat: np.ndarray, window: int) -> np.ndarray:
    """prev[d, i] = sum of mat[d-window : d, i] (strictly before day d)."""
    cs = np.vstack([np.zeros((1, mat.shape[1]), mat.dtype), np.cumsum(mat, axis=0)])
    d = np.arange(mat.shape[0])
    return cs[d] - cs[np.maximum(0, d - window)]


def build_ai1_features(w: World) -> pd.DataFrame:
    ev = w.events
    D, N = w.n_days, len(w.customers)
    reg = w.customers["registration_day"].to_numpy()
    cust_side_src = ev["src_kind"].to_numpy() == 0
    cust_side_dst = ev["dst_kind"].to_numpy() == 0
    day = ev["day"].to_numpy().astype(int)
    amt = ev["amount"].to_numpy(float)
    et = ev["etype"].astype(str).to_numpy()

    src_i = np.full(len(ev), -1, np.int64)
    dst_i = np.full(len(ev), -1, np.int64)
    src_i[cust_side_src] = _cidx(ev.loc[cust_side_src, "src"])
    dst_i[cust_side_dst] = _cidx(ev.loc[cust_side_dst, "dst"])

    def dense(mask, who, values):
        m = np.zeros((D, N), np.float64)
        np.add.at(m, (day[mask], who[mask]), values[mask] if np.ndim(values) else values)
        return m

    is_p2p = (et == "p2p") & cust_side_src & cust_side_dst
    out_any = cust_side_src & np.isin(et, ["p2p", "qr_pay", "bill_pay", "recharge", "cash_out"])
    out_cnt = dense(out_any, src_i, 1.0)
    p2p_cnt = dense(is_p2p, src_i, 1.0)
    p2p_sum = dense(is_p2p, src_i, amt)
    p2p_sq = dense(is_p2p, src_i, amt ** 2)
    in_cnt = dense(is_p2p, dst_i, 1.0)
    in_amt_all = dense(cust_side_dst, dst_i, amt)
    out_amt_all = dense(cust_side_src & np.isin(et, ["p2p", "qr_pay", "cash_out"]), src_i, amt)
    cashout = dense(cust_side_src & ((et == "cash_out") | ((et == "qr_pay") & (amt >= 1000))), src_i, 1.0)
    pairs = pd.DataFrame({"d": day[is_p2p], "s": src_i[is_p2p], "r": dst_i[is_p2p]}).drop_duplicates()
    sender_days = np.zeros((D, N))
    np.add.at(sender_days, (pairs["d"].to_numpy(), pairs["r"].to_numpy()), 1.0)

    P = {k: _prev_sum(v, 7) for k, v in dict(out=out_cnt, inc=in_cnt, inamt=in_amt_all, outamt=out_amt_all,
                                                 cashout=cashout, sdays=sender_days).items()}
    c30, s30, q30 = _prev_sum(p2p_cnt, 30), _prev_sum(p2p_sum, 30), _prev_sum(p2p_sq, 30)
    dc = w.daily_customer
    bal_mat = np.zeros((D, N))
    bal_mat[dc["day"].to_numpy().astype(int), _cidx(dc["customer_id"])] = dc["balance_sod"].to_numpy(float)

    f = ev.loc[is_p2p & (ev["mule_flow"].to_numpy() == 0),
               ["event_id", "t", "ts", "day", "src", "dst", "amount", "channel", "label_scam", "is_scam",
                "scam_family", "case_id"]].copy()
    s, r, d = _cidx(f["src"]), _cidx(f["dst"]), f["day"].to_numpy().astype(int)
    a = f["amount"].to_numpy(float)

    f["sender_tenure_days"] = d - reg[s]
    f["amount_log"] = np.log1p(a)
    mean30 = np.divide(s30[d, s], c30[d, s], out=np.full(len(f), np.nan), where=c30[d, s] > 0)
    var30 = np.divide(q30[d, s], c30[d, s], out=np.full(len(f), np.nan), where=c30[d, s] > 0) - mean30 ** 2
    std = np.sqrt(np.clip(var30, 0, None) + (0.1 * mean30 + 50) ** 2)
    f["amount_z_30d"] = np.where(c30[d, s] >= 2, (a - mean30) / std, np.nan)
    f["amount_to_balance"] = np.clip(a / (bal_mat[d, s] + 1.0), 0, 5)
    # helper columns (prefixed "_", never model inputs) used for counterfactual "what if the amount were lower"
    f["_mean30"], f["_std30"], f["_balance"] = mean30, std, bal_mat[d, s]
    f["sender_out_count_7d"] = P["out"][d, s]
    f["recipient_age_days"] = d - reg[r]
    f["recipient_in_count_7d"] = P["inc"][d, r]
    f["recipient_sender_days_7d"] = P["sdays"][d, r]
    f["recipient_out_in_ratio_7d"] = np.clip(P["outamt"][d, r] / (P["inamt"][d, r] + 100.0), 0, 5)
    f["recipient_cashout_count_7d"] = P["cashout"][d, r]

    f = f.sort_values("t", kind="stable")
    f["recipient_in_today_before"] = f.groupby(["dst", "day"]).cumcount()
    f["first_time_pair"] = (f.groupby(["src", "dst"]).cumcount() == 0).astype(np.int8)

    # minutes since the sender's last money-in event (cash-in, salary, remittance, incoming p2p) within 24 h
    inflow = ev.loc[cust_side_dst & np.isin(et, ["cash_in", "salary_in", "remit_in", "p2p"]), ["dst", "t"]]
    inflow = inflow.rename(columns={"dst": "src", "t": "t_in"}).sort_values("t_in")
    f = pd.merge_asof(f, inflow, left_on="t", right_on="t_in", by="src", direction="backward", allow_exact_matches=False)
    gap = (f["t"] - f["t_in"]) / 60.0
    f["cash_in_gap_min"] = np.where(gap.isna() | (gap > 1440), 1440.0, gap)

    sec = w.security.rename(columns={"customer_id": "src"})
    for kind in ("device_change", "pin_reset"):
        k = sec.loc[sec["kind"] == kind, ["src", "t"]].rename(columns={"t": f"t_{kind}"}).sort_values(f"t_{kind}")
        f = pd.merge_asof(f, k, left_on="t", right_on=f"t_{kind}", by="src", direction="backward")
        f[f"{kind}_72h"] = ((f["t"] - f[f"t_{kind}"]) <= 72 * 3600).fillna(False).astype(np.int8)

    sod = f["t"] % DAY
    f["hour"] = (sod / 3600).astype(float)
    f["is_night"] = ((f["hour"] < 6) | (f["hour"] >= 22)).astype(np.int8)
    f["dow"] = f["ts"].dt.dayofweek.astype(np.int8)
    f["channel_ussd"] = (f["channel"] == "ussd").astype(np.int8)

    cust = w.customers.set_index("customer_id")
    f["zone"] = f["src"].map(cust["zone"])
    f["language"] = f["src"].map(cust["language"])
    f["segment"] = f["src"].map(cust["segment"])
    f["tenure_bucket"] = pd.cut(f["sender_tenure_days"], [-1e9, 90, 365, 1e9], labels=["<90d", "90-365d", ">365d"]).astype(str)
    drop = [c for c in f.columns if c.startswith("t_")]
    return f.drop(columns=drop).sort_values("t", kind="stable").reset_index(drop=True)


def rule_baseline_score(df: pd.DataFrame, large_amount: float = 5000) -> np.ndarray:
    """The transparent rule a basic fraud system uses: large amount + new recipient (0, 1 or 2 points)."""
    return (df["amount"] >= large_amount).astype(int).to_numpy() + df["first_time_pair"].astype(int).to_numpy()

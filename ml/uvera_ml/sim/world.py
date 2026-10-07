"""UVERA-World: a seeded, fully synthetic mobile-money world.

Everything here is an [ASSUMPTION] documented in configs/assumptions.yaml and configs/patterns.yaml.
Labels (scam transfers, mule wallets, disguised QR merchants) come from a *hidden* process
(susceptible victims, mule wallets, merchant disguise families), never from a single feature rule.

Public tables (usable as model inputs):  customers, agents, merchants, events, security, daily_customer, daily_agent
Truth tables (labels / evaluation only):   truth_customers, truth_merchants, truth_cases
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from uvera_ml.common import load_config, sha256_frame, write_json

START = pd.Timestamp("2025-01-06")  # synthetic calendar start (a Monday); not a real event date
DAY = 86_400

ETYPES = ["salary_in", "remit_in", "cash_in", "p2p", "qr_pay", "bill_pay", "recharge", "cash_out"]
E = {name: i for i, name in enumerate(ETYPES)}
KIND = {"customer": 0, "agent": 1, "merchant": 2, "external": 3}
EXTERNAL = ["EMPLOYER", "REMITTANCE", "BILLER", "TELCO"]
ZONES = ["urban", "semi_urban", "rural"]
SEGMENTS = ["salaried", "daily_wage", "remittance", "student"]
LANGS = ["bangla", "banglish", "english"]
CATEGORIES = {  # median ticket (BDT), log-sigma, share of round-price sales for LEGIT merchants
    "grocery": (450, 0.6, 0.05),
    "pharmacy": (380, 0.6, 0.05),
    "restaurant": (320, 0.5, 0.10),
    "stationery": (120, 0.5, 0.05),
    "mobile_recharge": (100, 0.4, 0.90),
    "fashion": (1500, 0.6, 0.15),
    "electronics": (4200, 0.7, 0.20),
    "fixed_price_service": (1000, 0.3, 0.85),
}
CAT_P = [0.30, 0.12, 0.12, 0.08, 0.10, 0.10, 0.06, 0.12]
QR_FAMILIES = ["A_round_amount_atm", "B_split_under_limit", "C_cash_in_pass_through", "D_rotating_ring"]
# per-family scam behaviour: P(cash-in shortly before), P(account-takeover signals), share of balance, hours, P(odd amount)
SCAM_BEHAVIOUR = {
    "otp_reversal_counter": (0.60, 0.05, (0.50, 0.95), (9, 18), 0.30),
    "fake_customer_care": (0.25, 0.55, (0.60, 0.98), (10, 21), 0.20),
    "prize_lottery": (0.35, 0.05, (0.30, 0.80), (12, 22), 0.60),
    "investment_group": (0.30, 0.02, (0.20, 0.60), (18, 23), 0.30),
    "gold_jar_offer": (0.40, 0.03, (0.60, 0.99), (14, 23), 0.40),
    "refund_government": (0.20, 0.10, (0.10, 0.40), (9, 17), 0.50),
}


@dataclass
class World:
    customers: pd.DataFrame
    agents: pd.DataFrame
    merchants: pd.DataFrame
    events: pd.DataFrame
    security: pd.DataFrame
    daily_customer: pd.DataFrame
    daily_agent: pd.DataFrame
    truth_customers: pd.DataFrame
    truth_merchants: pd.DataFrame
    truth_cases: pd.DataFrame
    meta: dict = field(default_factory=dict)

    TABLES = ("customers", "agents", "merchants", "events", "security", "daily_customer", "daily_agent",
              "truth_customers", "truth_merchants", "truth_cases")

    def save(self, folder: str | Path) -> dict:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        hashes = {}
        for name in self.TABLES:
            df = getattr(self, name)
            df.to_parquet(folder / f"{name}.parquet", index=False)
            hashes[name] = sha256_frame(df)
        self.meta["hashes"] = hashes
        write_json(folder / "meta.json", self.meta)
        return hashes

    @classmethod
    def load(cls, folder: str | Path) -> "World":
        import json

        folder = Path(folder)
        tables = {n: pd.read_parquet(folder / f"{n}.parquet") for n in cls.TABLES}
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        return cls(**tables, meta=meta)

    @property
    def n_days(self) -> int:
        return int(self.meta["days"])


class _Log:
    """Column buffers for events, filled per day and concatenated once at the end."""

    COLS = ("etype", "src_kind", "src", "dst_kind", "dst", "amount", "t", "agent", "merchant",
            "is_scam", "family", "case", "qrfam", "mule_flow")

    def __init__(self):
        self.buf = {c: [] for c in self.COLS}

    def add(self, etype, src_kind, src, dst_kind, dst, amount, t, agent=-1, merchant=-1,
            is_scam=0, family=-1, case=-1, qrfam=-1, mule_flow=0):
        vals = dict(etype=etype, src_kind=src_kind, src=src, dst_kind=dst_kind, dst=dst, amount=amount, t=t,
                    agent=agent, merchant=merchant, is_scam=is_scam, family=family, case=case, qrfam=qrfam,
                    mule_flow=mule_flow)
        n = max(np.asarray(v).size if np.asarray(v).ndim else 1 for v in vals.values())
        if any(np.asarray(v).ndim and np.asarray(v).size == 0 for v in vals.values()):
            return
        for c, v in vals.items():
            arr = np.asarray(v)
            self.buf[c].append(np.full(n, arr) if arr.ndim == 0 else arr)

    def frame(self) -> dict:
        return {c: np.concatenate(v) if v else np.array([]) for c, v in self.buf.items()}


def _pick_in_zone(rng, zones: np.ndarray, groups: list, weights: np.ndarray | None = None) -> np.ndarray:
    """For each element, pick a member of groups[zone] (vectorised per zone; optional popularity weights)."""
    out = np.empty(len(zones), dtype=np.int64)
    for z, members in enumerate(groups):
        sel = zones == z
        if weights is None:
            out[sel] = members[rng.integers(0, len(members), sel.sum())]
        else:
            w = weights[members]
            out[sel] = rng.choice(members, sel.sum(), p=w / w.sum())
    return out


def _round_to(x, step):
    return np.maximum(step, np.round(np.asarray(x, dtype=float) / step) * step)


def generate_world(scale: str = "small", seed: int | None = None) -> World:
    cfg = load_config("assumptions")
    pat = load_config("patterns")
    seed = cfg["seed"] if seed is None else seed
    sc = cfg["scale"][scale]
    N, A, M, D = sc["customers"], sc["agents"], sc["merchants"], sc["days"]
    rates = cfg["rates"]
    rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------ entities
    zone = rng.choice(3, N, p=[cfg["zones"][z] for z in ZONES])
    p_ussd = np.array([0.20, 0.30, 0.45])[zone]
    channel = (rng.random(N) < p_ussd).astype(np.int8)  # 0 app, 1 ussd
    segment = rng.choice(4, N, p=[0.35, 0.35, 0.15, 0.15])
    income = np.exp(rng.normal(np.log(np.array([25000, 15000, 12000, 5000])[segment]), 0.35))
    tenure0 = np.where(rng.random(N) < 0.20, rng.integers(0, 60, N), rng.integers(60, 1800, N))
    reg_day = -tenure0
    joiners = rng.random(N) < 0.10
    reg_day[joiners] = rng.integers(1, D - 1, joiners.sum())
    lang = rng.choice(3, N, p=[cfg["text"]["languages"][k] for k in LANGS])
    is_hub = rng.random(N) < 0.05
    pay_dom = rng.integers(1, 6, N)
    bill_dom = rng.integers(5, 26, N)
    # latent susceptibility (hidden): higher for new users and USSD users; NOT a model feature
    susc = rng.beta(2, 8, N) * (1 + 1.2 * (tenure0 < 120) + 0.4 * channel)

    # mules (hidden)
    n_mule = max(6, int(round(N * 0.01)))
    mules = rng.choice(np.where(~joiners)[0], n_mule, replace=False)
    is_mule = np.zeros(N, bool)
    is_mule[mules] = True
    mule_start = np.full(N, -1)
    mule_end = np.full(N, -1)
    mule_start[mules] = rng.integers(0, max(1, D - 10), n_mule)
    mule_end[mules] = mule_start[mules] + rng.integers(7, 26, n_mule)
    # 45% newly opened accounts, 55% older "bought" accounts (overridable for distribution-shift tests)
    fresh = mules[rng.random(n_mule) < float(cfg.get("mule_fresh_share", 0.45))]
    reg_day[fresh] = mule_start[fresh] - rng.integers(0, 6, len(fresh))
    susc[mules] = 0

    agent_zone = rng.choice(3, A, p=[cfg["zones"][z] for z in ZONES])
    agent_size = rng.choice(3, A, p=[0.5, 0.35, 0.15])
    zone_agents = [np.where(agent_zone == z)[0] for z in range(3)]
    home_agent = _pick_in_zone(rng, zone, zone_agents)

    cat_names = list(CATEGORIES)
    m_cat = rng.choice(len(cat_names), M, p=CAT_P)
    m_zone = rng.choice(3, M, p=[cfg["zones"][z] for z in ZONES])
    m_size = rng.choice(3, M, p=[0.6, 0.3, 0.1])
    disguised = rng.random(M) < rates["disguised_qr_merchant_share"]
    disguised &= np.isin(np.array(cat_names)[m_cat], ["grocery", "stationery", "mobile_recharge", "pharmacy", "fashion"])
    m_fam = np.full(M, -1)
    m_fam[disguised] = rng.choice(4, disguised.sum(), p=[0.30, 0.25, 0.25, 0.20])
    zone_merchants = [np.where(m_zone == z)[0] for z in range(3)]
    popularity = np.array([1.0, 2.5, 5.0])[m_size] * rng.uniform(0.5, 1.5, M)
    reg_merch = np.stack([_pick_in_zone(rng, zone, zone_merchants, popularity) for _ in range(3)], axis=1)
    m_intensity = np.where(m_fam >= 0, rng.uniform(0.05, 0.4, M), 0.0)  # share of a disguised shop's day spent on fake sales
    m_transit = (m_fam < 0) & (rng.random(M) < 0.10)  # honest shops near bus stands/markets: many one-time customers
    # every shop has its own honest habits, so honest shops overlap with disguised ones
    m_round_extra = np.where(rng.random(M) < 0.25, rng.uniform(0.2, 0.6, M), 0.0)  # fixed-price packs
    m_sig_extra = np.where(rng.random(M) < 0.15, rng.uniform(0.3, 0.7, M), 0.0)    # mixed goods, wide prices
    m_bulk = rng.beta(1, 30, M)                                                    # bulk / wholesale buys
    m_twice = rng.beta(1, 20, M)                                                   # same customer pays again soon

    # contacts: 4 same-zone people + 2 from anywhere (hubs over-represented)
    zone_people = [np.where(zone == z)[0] for z in range(3)]
    hubs = np.where(is_hub)[0]
    contacts = np.empty((N, 6), dtype=np.int64)
    for z in range(3):
        idx = np.where(zone == z)[0]
        contacts[idx, :4] = rng.choice(zone_people[z], (len(idx), 4))
    contacts[:, 4] = rng.integers(0, N, N)
    contacts[:, 5] = np.where(rng.random(N) < 0.5, rng.choice(hubs, N), rng.integers(0, N, N))

    # QR family D rings: 2-4 D merchants share a fixed set of 5-15 payers
    d_merch = np.where(m_fam == 3)[0]
    rings = []
    rng.shuffle(d_merch)
    i = 0
    while i < len(d_merch):
        k = int(rng.integers(2, 5))
        ms = d_merch[i:i + k]
        i += k
        z = m_zone[ms[0]]
        payers = rng.choice(zone_people[z], int(rng.integers(5, 16)), replace=False)
        rings.append((ms, payers[~is_mule[payers]]))
    ring_of = np.full(M, -1)
    for r, (ms, _) in enumerate(rings):
        ring_of[ms] = r

    # ------------------------------------------------------------------ simulation state
    bal = income * rng.uniform(0.1, 0.6, N)
    bal[mules] = rng.uniform(0, 500, n_mule)
    log = _Log()
    sec_rows = []  # (customer, t, kind)
    case_rows = []  # (case, victim, mule, family, day, amount)
    bal_sod = np.zeros((D, N), np.float32)
    d_in = np.zeros((D, N), np.float32)
    d_out = np.zeros((D, N), np.float32)
    bal_eod = np.zeros((D, N), np.float32)
    ag_cashout = np.zeros((D, A), np.float32)
    ag_cashin = np.zeros((D, A), np.float32)
    mule_case = np.full(N, -1)
    mule_last_in = np.full(N, -99)
    pending_invest = []  # (day, victim, mule, case)
    case_id = 0
    fam_names = list(pat["scam_families"])
    fam_share = np.array([pat["scam_families"][f]["share"] for f in fam_names])
    fam_amt = {f: tuple(pat["scam_families"][f]["amount_bdt"]) for f in fam_names}
    fest_start = int(round(cfg["calendar"]["festival_bump"]["start_fraction"] * D))
    fest_len = cfg["calendar"]["festival_bump"]["length_days"]
    fest_mult = cfg["calendar"]["festival_bump"]["volume_multiplier"]

    def secs(n, lo_h, hi_h):
        return rng.uniform(lo_h * 3600, hi_h * 3600, n)

    def credit(idx, amt, d):
        np.add.at(bal, idx, amt)
        np.add.at(d_in[d], idx, amt)

    def debit(idx, amt, d):
        np.add.at(bal, idx, -amt)
        np.add.at(d_out[d], idx, amt)

    for d in range(D):
        date = START + pd.Timedelta(days=d)
        dow, dom = date.dayofweek, date.day
        base = d * DAY
        fest = fest_start <= d < fest_start + fest_len
        fmult = fest_mult if fest else 1.0
        fri = dow == 4  # Friday: weekend in Bangladesh
        active = (reg_day <= d) & ~is_mule
        mule_active = is_mule & (mule_start <= d) & (d <= mule_end)
        bal_sod[d] = bal

        # ---------------- inflows
        idx = np.where(active & (segment == 0) & (pay_dom == dom))[0]
        amt = _round_to(income[idx] * rng.uniform(0.95, 1.05, len(idx)), 100)
        log.add(E["salary_in"], KIND["external"], 0, KIND["customer"], idx, amt, base + secs(len(idx), 9, 12))
        credit(idx, amt, d)

        idx = np.where(active & (segment == 1) & (rng.random(N) < (0.33 if fri else 0.55)))[0]
        amt = _round_to(income[idx] / 22 * rng.uniform(0.6, 1.5, len(idx)), 10)
        ag = home_agent[idx]
        log.add(E["cash_in"], KIND["agent"], ag, KIND["customer"], idx, amt, base + secs(len(idx), 17, 21.5), agent=ag)
        credit(idx, amt, d)
        np.add.at(ag_cashin[d], ag, amt)

        idx = np.where(active & (((segment == 2) & (rng.random(N) < 1 / 18)) | ((segment == 3) & (pay_dom == dom))))[0]
        amt = _round_to(income[idx] * rng.uniform(0.5, 1.3, len(idx)), 100)
        log.add(E["remit_in"], KIND["external"], 1, KIND["customer"], idx, amt, base + secs(len(idx), 10, 20))
        credit(idx, amt, d)

        idx = np.where(active & (rng.random(N) < 0.04))[0]
        amt = _round_to(rng.uniform(500, 5000, len(idx)), 100)
        ag = np.where(rng.random(len(idx)) < 0.8, home_agent[idx], rng.integers(0, A, len(idx)))
        log.add(E["cash_in"], KIND["agent"], ag, KIND["customer"], idx, amt, base + secs(len(idx), 9, 21), agent=ag)
        credit(idx, amt, d)
        np.add.at(ag_cashin[d], ag, amt)

        # ---------------- normal security events
        for kind, p in (("device_change", 0.002), ("pin_reset", 0.0012)):
            idx = np.where(active & (rng.random(N) < p))[0]
            sec_rows.append(np.column_stack([idx, base + secs(len(idx), 7, 23), np.full(len(idx), 0 if kind == "device_change" else 1)]))

        # ---------------- normal p2p (incl. legit look-alikes)
        rate = np.array([0.30, 0.18, 0.25, 0.15])[segment] * (1.1 if fri else 1.0) * fmult
        snd = np.where(active & (rng.random(N) < rate) & (bal > 100))[0]
        new_rec = rng.random(len(snd)) < 0.12
        rec = contacts[snd, rng.integers(0, 6, len(snd))]
        n_new = new_rec.sum()
        young = np.where((reg_day <= d) & (reg_day > d - 45) & ~is_mule)[0]
        pick = rng.random(n_new)
        rec[new_rec] = np.where(pick < 0.35, rng.choice(hubs, n_new),
                                np.where((pick < 0.60) & (len(young) > 0), rng.choice(young if len(young) else hubs, n_new),
                                         rng.integers(0, N, n_new)))
        amt = np.exp(rng.normal(np.log(income[snd] * 0.04), 1.15))
        r = rng.random(len(snd))
        amt = np.where(r < 0.6, _round_to(amt, 10), np.where(r < 0.9, _round_to(amt, 100), np.round(amt)))
        look = (rng.random(len(snd)) < rates["legit_lookalike_share"] * (3 if fest else 1)) & (bal[snd] > 3000)
        amt = np.where(look, _round_to(bal[snd] * rng.uniform(0.4, 0.9, len(snd)), 100), amt)
        relook = look & (rng.random(len(snd)) < 0.6)
        rec[relook] = rng.integers(0, N, relook.sum())
        ok = (rec != snd) & (reg_day[rec] <= d) & ~is_mule[rec]
        snd, rec, amt = snd[ok], rec[ok], np.minimum(amt[ok], bal[snd[ok]] * 0.9)
        log.add(E["p2p"], KIND["customer"], snd, KIND["customer"], rec, amt, base + secs(len(snd), 8, 23))
        debit(snd, amt, d)
        credit(rec, amt, d)
        n_p2p_today = len(snd)

        # monthly family support: salaried / remittance customers send a large share to family soon after pay day
        sup_snd = np.where(active & np.isin(segment, [0, 2]) & (np.abs(dom - pay_dom - 1) <= 1)
                           & (rng.random(N) < 0.40) & (bal > 2000))[0]
        sup_rec = contacts[sup_snd, 0]
        ok = (sup_rec != sup_snd) & (reg_day[sup_rec] <= d) & ~is_mule[sup_rec]
        sup_snd, sup_rec = sup_snd[ok], sup_rec[ok]
        sup_amt = np.minimum(_round_to(income[sup_snd] * rng.uniform(0.1, 0.4, len(sup_snd)), 500), bal[sup_snd] * 0.9)
        log.add(E["p2p"], KIND["customer"], sup_snd, KIND["customer"], sup_rec, sup_amt, base + secs(len(sup_snd), 9, 22))
        debit(sup_snd, sup_amt, d)
        credit(sup_rec, sup_amt, d)
        n_p2p_today += len(sup_snd)

        # ---------------- QR merchant payments (normal sales, also at disguised shops)
        qr_rate = np.where(channel == 0, 0.35, 0.08) * (0.85 if dom >= 25 else 1.2 if dom <= 5 else 1.0) * (0.8 if fri else 1.0) * fmult
        pay = np.where(active & (rng.random(N) < qr_rate) & (bal > 80))[0]
        mer = np.where(rng.random(len(pay)) < 0.8, reg_merch[pay, rng.integers(0, 3, len(pay))],
                       _pick_in_zone(rng, zone[pay], zone_merchants))
        med = np.array([CATEGORIES[cat_names[c]][0] for c in m_cat[mer]])
        sig = np.array([CATEGORIES[cat_names[c]][1] for c in m_cat[mer]]) + m_sig_extra[mer]
        rshare = np.minimum(np.array([CATEGORIES[cat_names[c]][2] for c in m_cat[mer]]) + m_round_extra[mer], 0.95)
        amt = np.exp(rng.normal(np.log(med), sig))
        bulk = rng.random(len(pay)) < m_bulk[mer]
        amt = np.where(bulk, amt * rng.uniform(4, 15, len(pay)), amt)
        is_round = rng.random(len(pay)) < rshare
        amt = np.where(is_round, _round_to(amt, np.where(med >= 500, 500, 50)), np.round(amt))
        amt = np.minimum(amt, bal[pay] * 0.9)
        keep = amt >= 10
        pay, mer, amt = pay[keep], mer[keep], amt[keep]
        tq = base + secs(len(pay), 8, 22)
        topup = rng.random(len(pay)) < 0.05  # honest: top up at an agent, then pay a shop
        if topup.any():
            cin = _round_to(amt[topup] + rng.uniform(100, 2000, topup.sum()), 100)
            ag = home_agent[pay[topup]]
            log.add(E["cash_in"], KIND["agent"], ag, KIND["customer"], pay[topup], cin,
                    tq[topup] - rng.uniform(120, 1800, topup.sum()), agent=ag)
            credit(pay[topup], cin, d)
            np.add.at(ag_cashin[d], ag, cin)
        log.add(E["qr_pay"], KIND["customer"], pay, KIND["merchant"], mer, amt, tq, merchant=mer)
        debit(pay, amt, d)
        twice = (rng.random(len(pay)) < m_twice[mer]) & (bal[pay] > amt)  # honest: pay twice at the same shop
        log.add(E["qr_pay"], KIND["customer"], pay[twice], KIND["merchant"], mer[twice], np.round(amt[twice] * rng.uniform(0.2, 1.0, twice.sum())),
                tq[twice] + rng.uniform(120, 1500, twice.sum()), merchant=mer[twice])
        debit(pay[twice], np.round(amt[twice] * 0.6), d)
        for shop in np.where(m_transit)[0]:  # transit shops: one-time walk-in customers, normal tickets
            walk = rng.choice(zone_people[m_zone[shop]], rng.poisson(3))
            walk = walk[active[walk] & (bal[walk] > 100)]
            med, sig, _ = CATEGORIES[cat_names[m_cat[shop]]]
            wa = np.minimum(np.round(np.exp(rng.normal(np.log(med), sig, len(walk)))), bal[walk] * 0.9)
            log.add(E["qr_pay"], KIND["customer"], walk, KIND["merchant"], shop, wa, base + secs(len(walk), 7, 22), merchant=shop)
            debit(walk, wa, d)

        # ---------------- bills, recharge, cash-out
        idx = np.where(active & (bill_dom == dom) & (bal > 300))[0]
        amt = np.minimum(_round_to(income[idx] * rng.uniform(0.04, 0.1, len(idx)), 10), bal[idx] * 0.8)
        log.add(E["bill_pay"], KIND["customer"], idx, KIND["external"], 2, amt, base + secs(len(idx), 9, 22))
        debit(idx, amt, d)

        idx = np.where(active & (rng.random(N) < 0.12) & (bal > 60))[0]
        amt = rng.choice([20, 30, 50, 100, 200], len(idx), p=[0.15, 0.15, 0.3, 0.3, 0.1]).astype(float)
        amt = np.minimum(amt, bal[idx] * 0.9)
        log.add(E["recharge"], KIND["customer"], idx, KIND["external"], 3, amt, base + secs(len(idx), 7, 23))
        debit(idx, amt, d)

        co_rate = np.where(channel == 0, 0.10, 0.16) * np.where(segment == 1, 0.5, 1.0) * fmult
        idx = np.where(active & (rng.random(N) < co_rate) & (bal > 400))[0]
        amt = np.minimum(_round_to(bal[idx] * rng.uniform(0.2, 0.7, len(idx)), 100), bal[idx])
        ag = np.where(rng.random(len(idx)) < 0.8, home_agent[idx], _pick_in_zone(rng, zone[idx], zone_agents))
        log.add(E["cash_out"], KIND["customer"], idx, KIND["agent"], ag, amt, base + secs(len(idx), 9, 21), agent=ag)
        debit(idx, amt, d)
        np.add.at(ag_cashout[d], ag, amt)

        # ---------------- scams (authorised push payments to mule wallets)
        mule_ids = np.where(mule_active)[0]
        todays = [(v, m, c, "investment_group") for (dd, v, m, c) in pending_invest if dd == d and mule_active[m]]
        pending_invest = [p for p in pending_invest if p[0] > d]
        if len(mule_ids):
            n_scam = rng.poisson(rates["scam_share_of_p2p"] * n_p2p_today * (1.3 if fest else 1.0))
            cand = np.where(active & (bal > 300))[0]
            if n_scam and len(cand):
                w = susc[cand] ** 1.5
                victims = rng.choice(cand, min(n_scam, len(cand)), replace=False, p=w / w.sum())
                fams = rng.choice(fam_names, len(victims), p=fam_share)
                for v, f in zip(victims, fams):
                    m = int(rng.choice(mule_ids))
                    todays.append((int(v), m, case_id, f))
                    if f == "investment_group":
                        for k in range(1, int(rng.integers(2, 5))):
                            pending_invest.append((d + k, int(v), m, case_id))
                    case_id += 1
        for v, m, c, f in todays:
            p_cash, p_take, frac, hours, p_odd = SCAM_BEHAVIOUR[f]
            t = base + rng.uniform(hours[0] * 3600, hours[1] * 3600)
            if rng.random() < p_cash:
                cin = float(_round_to(rng.uniform(1000, 6000), 100))
                ag = int(home_agent[v])
                log.add(E["cash_in"], KIND["agent"], np.array([ag]), KIND["customer"], np.array([v]), np.array([cin]),
                        np.array([t - rng.uniform(600, 3600)]), agent=np.array([ag]))
                credit(np.array([v]), np.array([cin]), d)
                ag_cashin[d, ag] += cin
            if rng.random() < p_take:
                kind = int(rng.integers(0, 2))
                sec_rows.append(np.array([[v, t - rng.uniform(3600, 48 * 3600), kind]]))
            lo, hi = fam_amt[f]
            amount = float(np.clip(bal[v] * rng.uniform(*frac) * rng.uniform(0.4, 1.0), lo * rng.uniform(0.2, 1.0), hi))
            amount = min(amount, bal[v] * 0.99)
            amount = float(np.round(amount / 10) * 10 - (rng.integers(1, 9) * 10 if rng.random() < p_odd else 0))
            if amount < 50:
                continue
            log.add(E["p2p"], KIND["customer"], np.array([v]), KIND["customer"], np.array([m]), np.array([amount]),
                    np.array([t]), is_scam=1, family=fam_names.index(f), case=c)
            debit(np.array([v]), np.array([amount]), d)
            credit(np.array([m]), np.array([amount]), d)
            mule_case[m] = c
            mule_last_in[m] = d
            if c not in {row[0] for row in case_rows[-50:]}:
                case_rows.append((c, v, m, fam_names.index(f), d, amount))

        # ---------------- mule outflows: hop to another mule, agent cash-out, or QR cash-out at a disguised shop
        movers = np.where(mule_active & (bal > 500) & (d - mule_last_in <= 2) & (rng.random(N) < 0.7))[0]
        cashout_shops = np.where(np.isin(m_fam, [0, 2]))[0]
        for m in movers:
            c = int(mule_case[m])
            r = rng.random()
            t = base + rng.uniform(10 * 3600, 22 * 3600)
            others = mule_ids[mule_ids != m]
            if r < 0.35 and len(others):
                to = int(rng.choice(others))
                amount = float(_round_to(bal[m] * rng.uniform(0.8, 0.98), 10))
                log.add(E["p2p"], KIND["customer"], np.array([m]), KIND["customer"], np.array([to]), np.array([amount]),
                        np.array([t]), case=c, mule_flow=1)
                debit(np.array([m]), np.array([amount]), d)
                credit(np.array([to]), np.array([amount]), d)
                mule_case[to] = c
                mule_last_in[to] = d
            elif r < 0.70 or not len(cashout_shops):
                amount = float(min(_round_to(bal[m] * rng.uniform(0.85, 0.99), 100), bal[m]))
                ag = int(rng.choice(zone_agents[zone[m]]))
                log.add(E["cash_out"], KIND["customer"], np.array([m]), KIND["agent"], np.array([ag]), np.array([amount]),
                        np.array([t]), agent=np.array([ag]), case=c, mule_flow=1)
                debit(np.array([m]), np.array([amount]), d)
                ag_cashout[d, ag] += amount
            else:
                shop = int(rng.choice(cashout_shops))
                total = bal[m] * rng.uniform(0.85, 0.99)
                parts = _round_to(np.full(int(rng.integers(1, 4)), total / 3), 1000)
                parts = parts[np.cumsum(parts) <= bal[m]]
                if len(parts):
                    log.add(E["qr_pay"], KIND["customer"], np.full(len(parts), m), KIND["merchant"], np.full(len(parts), shop),
                            parts, t + np.arange(len(parts)) * rng.uniform(60, 900), merchant=np.full(len(parts), shop),
                            case=c, qrfam=m_fam[shop], mule_flow=1)
                    debit(np.full(len(parts), m), parts, d)

        # ---------------- QR disguise families (customers using shops as an ATM)
        for shop in np.where(m_fam >= 0)[0]:
            fam = m_fam[shop]
            z = m_zone[shop]
            people = zone_people[z]
            if fam == 0:  # A: many one-time payers, round amounts
                k = rng.poisson(5 * fmult * m_intensity[shop])
                payers = rng.choice(people, k)
                payers = payers[active[payers]]
                amts = rng.choice([500, 1000, 1000, 2000, 2000, 3000, 5000], len(payers)).astype(float)
                ok = bal[payers] >= amts
                payers, amts = payers[ok], amts[ok]
                log.add(E["qr_pay"], KIND["customer"], payers, KIND["merchant"], shop, amts,
                        base + secs(len(payers), 10, 21), merchant=shop, qrfam=0)
                debit(payers, amts, d)
            elif fam == 1:  # B: same payer splits into bursts
                for p in rng.choice(people, rng.poisson(2 * m_intensity[shop])):
                    if not active[p]:
                        continue
                    n = int(rng.integers(2, 6))
                    total = rng.uniform(3000, 9000)
                    amts = np.round(total / n * rng.uniform(0.95, 1.05, n) / 10) * 10
                    if bal[p] < amts.sum():
                        cin = float(_round_to(amts.sum() - bal[p] + 200, 100))
                        ag = int(home_agent[p])
                        t0 = base + rng.uniform(10, 19) * 3600
                        log.add(E["cash_in"], KIND["agent"], np.array([ag]), KIND["customer"], np.array([p]), np.array([cin]),
                                np.array([t0 - rng.uniform(600, 7200)]), agent=np.array([ag]))
                        credit(np.array([p]), np.array([cin]), d)
                        ag_cashin[d, ag] += cin
                    else:
                        t0 = base + rng.uniform(10, 19) * 3600
                    ts = t0 + np.sort(rng.uniform(0, rng.uniform(5, 40) * 60, n))
                    log.add(E["qr_pay"], KIND["customer"], np.full(n, p), KIND["merchant"], shop, amts, ts, merchant=shop, qrfam=1)
                    debit(np.full(n, p), amts, d)
            elif fam == 2:  # C: cash-in then drain to the shop within minutes
                for p in rng.choice(people, rng.poisson(3 * m_intensity[shop])):
                    if not active[p]:
                        continue
                    cin = float(_round_to(rng.uniform(2000, 8000), 100))
                    ag = int(home_agent[p])
                    t0 = base + rng.uniform(10, 20) * 3600
                    log.add(E["cash_in"], KIND["agent"], np.array([ag]), KIND["customer"], np.array([p]), np.array([cin]),
                            np.array([t0]), agent=np.array([ag]))
                    credit(np.array([p]), np.array([cin]), d)
                    ag_cashin[d, ag] += cin
                    amount = float(np.round(bal[p] * rng.uniform(0.85, 1.0)))
                    log.add(E["qr_pay"], KIND["customer"], np.array([p]), KIND["merchant"], shop, np.array([amount]),
                            np.array([t0 + rng.uniform(2, 45) * 60]), merchant=shop, qrfam=2)
                    debit(np.array([p]), np.array([amount]), d)
        for ms, payers in rings:  # D: rotating ring, repeat payers, shifting amounts, odd hours
            go = payers[(rng.random(len(payers)) < 0.2) & active[payers]]
            for p in go:
                shop = int(rng.choice(ms))
                med = CATEGORIES[cat_names[m_cat[shop]]][0]
                amount = float(np.round(med * rng.uniform(1.5, 6.0) / 10) * 10 + rng.integers(1, 9))
                t = base + rng.uniform(7, 23.5) * 3600
                if bal[p] < amount:
                    cin = float(_round_to(amount - bal[p] + 300, 100))
                    ag = int(home_agent[p])
                    log.add(E["cash_in"], KIND["agent"], np.array([ag]), KIND["customer"], np.array([p]), np.array([cin]),
                            np.array([t - rng.uniform(600, 5400)]), agent=np.array([ag]))
                    credit(np.array([p]), np.array([cin]), d)
                    ag_cashin[d, ag] += cin
                log.add(E["qr_pay"], KIND["customer"], np.array([p]), KIND["merchant"], shop, np.array([amount]),
                        np.array([t]), merchant=shop, qrfam=3)
                debit(np.array([p]), np.array([amount]), d)

        bal = np.maximum(bal, 0)
        bal_eod[d] = bal

    # ------------------------------------------------------------------ assemble tables
    f = log.frame()
    ev = pd.DataFrame({
        "t": f["t"].astype(np.int64), "etype": f["etype"].astype(np.int8),
        "src_kind": f["src_kind"].astype(np.int8), "src_i": f["src"].astype(np.int64),
        "dst_kind": f["dst_kind"].astype(np.int8), "dst_i": f["dst"].astype(np.int64),
        "amount": np.round(f["amount"].astype(float), 2), "agent_i": f["agent"].astype(np.int64),
        "merchant_i": f["merchant"].astype(np.int64), "is_scam": f["is_scam"].astype(np.int8),
        "family_i": f["family"].astype(np.int8), "case_id": f["case"].astype(np.int64),
        "qrfam_i": f["qrfam"].astype(np.int8), "mule_flow": f["mule_flow"].astype(np.int8),
    })
    ev = ev[ev["amount"] > 0].sort_values(["t", "src_i"], kind="stable").reset_index(drop=True)
    ev["event_id"] = np.arange(len(ev), dtype=np.int64)
    ev["day"] = (ev["t"] // DAY).astype(np.int16)
    ev["ts"] = START + pd.to_timedelta(ev["t"], unit="s")
    ev["etype"] = pd.Categorical.from_codes(ev["etype"], ETYPES)

    cust_ids = np.array([f"C{i:06d}" for i in range(N)])
    agent_ids = np.array([f"A{i:04d}" for i in range(A)])
    merch_ids = np.array([f"M{i:05d}" for i in range(M)])

    def ids(kind_col, idx_col):
        out = np.empty(len(ev), dtype=object)
        k, i = ev[kind_col].to_numpy(), ev[idx_col].to_numpy()
        for kind, table in ((0, cust_ids), (1, agent_ids), (2, merch_ids), (3, np.array(EXTERNAL))):
            sel = k == kind
            out[sel] = table[i[sel]]
        return out

    ev["src"] = ids("src_kind", "src_i")
    ev["dst"] = ids("dst_kind", "dst_i")
    ev["agent_id"] = np.where(ev["agent_i"] >= 0, agent_ids[ev["agent_i"].clip(0)], None)
    ev["merchant_id"] = np.where(ev["merchant_i"] >= 0, merch_ids[ev["merchant_i"].clip(0)], None)
    ev["scam_family"] = np.where(ev["family_i"] >= 0, np.array(fam_names)[ev["family_i"].clip(0)], None)
    ev["qr_family"] = np.where(ev["qrfam_i"] >= 0, np.array(QR_FAMILIES)[ev["qrfam_i"].clip(0)], None)
    cust_channel = np.array(["app", "ussd"])[channel]
    ev["channel"] = np.where(ev["src_kind"] == 0, cust_channel[np.where(ev["src_kind"] == 0, ev["src_i"], 0)],
                             np.where(ev["dst_kind"] == 0, cust_channel[np.where(ev["dst_kind"] == 0, ev["dst_i"], 0)], "app"))

    # label noise: some scams are never reported, some normal transfers are wrongly reported (equal counts)
    p2p = ev.index[(ev["etype"] == "p2p") & (ev["mule_flow"] == 0)]
    pos = ev.index[(ev["etype"] == "p2p") & (ev["is_scam"] == 1)]
    n_flip = int(round(len(pos) * rates["label_noise"]))
    if n_flip:
        lose = rng.choice(pos, n_flip, replace=False)
        neg = np.setdiff1d(p2p, pos)
        gain = rng.choice(neg, n_flip, replace=False)
        ev["label_scam"] = ev["is_scam"].astype(np.int8)
        ev.loc[lose, "label_scam"] = 0
        ev.loc[gain, "label_scam"] = 1
    else:
        ev["label_scam"] = ev["is_scam"].astype(np.int8)

    keep_cols = ["event_id", "ts", "t", "day", "etype", "src_kind", "src", "dst_kind", "dst", "amount", "channel",
                 "agent_id", "merchant_id", "label_scam", "is_scam", "scam_family", "case_id", "qr_family", "mule_flow"]
    ev = ev[keep_cols]

    sec = np.concatenate([r for r in sec_rows if len(r)]) if sec_rows else np.zeros((0, 3))
    security = pd.DataFrame({"customer_id": cust_ids[sec[:, 0].astype(int)], "t": sec[:, 1].astype(np.int64),
                             "kind": np.array(["device_change", "pin_reset"])[sec[:, 2].astype(int)]})
    security = security[security["t"] >= 0].sort_values("t").reset_index(drop=True)
    security["ts"] = START + pd.to_timedelta(security["t"], unit="s")

    customers = pd.DataFrame({
        "customer_id": cust_ids, "zone": np.array(ZONES)[zone], "channel": cust_channel,
        "segment": np.array(SEGMENTS)[segment], "registration_day": reg_day, "language": np.array(LANGS)[lang],
        "home_agent": agent_ids[home_agent], "monthly_income_band": pd.cut(income, [0, 8000, 15000, 25000, 1e9],
                                                                            labels=["<8k", "8-15k", "15-25k", "25k+"]).astype(str),
    })
    agents = pd.DataFrame({"agent_id": agent_ids, "zone": np.array(ZONES)[agent_zone],
                           "size": np.array(["small", "medium", "large"])[agent_size]})
    merchants = pd.DataFrame({"merchant_id": merch_ids, "zone": np.array(ZONES)[m_zone],
                              "category": np.array(cat_names)[m_cat], "size": np.array(["small", "medium", "large"])[m_size]})
    truth_customers = pd.DataFrame({"customer_id": cust_ids, "is_mule": is_mule, "mule_start": mule_start,
                                    "mule_end": mule_end, "susceptibility": np.round(susc, 4), "is_hub": is_hub})
    truth_merchants = pd.DataFrame({"merchant_id": merch_ids, "is_disguised": m_fam >= 0,
                                    "family": np.where(m_fam >= 0, np.array(QR_FAMILIES)[m_fam.clip(0)], None),
                                    "ring_id": ring_of})
    truth_cases = pd.DataFrame(case_rows, columns=["case_id", "victim_i", "mule_i", "family_i", "day", "first_amount"])
    truth_cases["victim"] = cust_ids[truth_cases["victim_i"]]
    truth_cases["mule"] = cust_ids[truth_cases["mule_i"]]
    truth_cases["family"] = np.array(fam_names)[truth_cases["family_i"]]
    truth_cases = truth_cases[["case_id", "victim", "mule", "family", "day", "first_amount"]]

    days = np.arange(D)
    daily_customer = pd.DataFrame({
        "customer_id": np.repeat(cust_ids, D), "day": np.tile(days, N),
        "inflow": d_in.T.ravel(), "outflow": d_out.T.ravel(),
        "balance_sod": bal_sod.T.ravel(), "balance_eod": bal_eod.T.ravel(),
    })
    daily_customer = daily_customer[daily_customer["day"] >= daily_customer["customer_id"].map(
        dict(zip(cust_ids, np.maximum(reg_day, 0))))].reset_index(drop=True)
    daily_agent = pd.DataFrame({"agent_id": np.repeat(agent_ids, D), "day": np.tile(days, A),
                                "cash_out": ag_cashout.T.ravel(), "cash_in": ag_cashin.T.ravel()})
    for df in (daily_customer, daily_agent):
        df["date"] = START + pd.to_timedelta(df["day"], unit="D")

    meta = {"scale": scale, "seed": int(seed), "days": int(D), "start": str(START.date()),
            "n_events": int(len(ev)), "n_scam_transfers": int(ev["is_scam"].sum()),
            "n_cases": int(len(truth_cases)), "n_mules": int(n_mule), "n_disguised_merchants": int((m_fam >= 0).sum()),
            "festival_days": [fest_start, fest_start + fest_len - 1], "version": cfg["version"]}
    return World(customers, agents, merchants, ev, security, daily_customer, daily_agent,
                 truth_customers, truth_merchants, truth_cases, meta)


def load_or_generate(folder: str | Path, scale: str = "full", seed: int | None = None) -> World:
    """Load a saved world if it exists (checkpoint), else generate and save it."""
    folder = Path(folder)
    if (folder / "meta.json").exists():
        w = World.load(folder)
        if w.meta.get("scale") == scale:
            print("Loaded cached world from", folder)
            return w
    w = generate_world(scale, seed)
    w.save(folder)
    return w

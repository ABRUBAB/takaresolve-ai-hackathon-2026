"""Online (streaming) versions of the 19 AI-1 features.

One implementation, used by BOTH the feature-worker (apply event + snapshot features) and the scorer (read features):
the state lives in Redis and is aggregated by server-side Lua so every update is atomic and a pipelined batch of
events is applied strictly in order (exact point-in-time features, same as the batch builder).

Redis data model (one hash per wallet, one hash per sender for counterparties):
  c:{wallet}  reg            registration day (customer master / KYC snapshot, loaded by bootstrap)
              bal bd bs      running balance, day of last roll, balance at start of day bd
              li lip         last money-in time and the one before it (for "strictly before t")
              ld lp          last device change / PIN reset time (security event stream)
  ledger:sod:{day}  {wallet} -> start-of-day ledger balance (daily snapshot from the core ledger, loaded by the
                    producer / a batch job at day start); falls back to the stream-rebuilt balance if absent
              o{d} n{d} s{d} q{d}   per-day sender counters: outgoing count, p2p count, p2p sum, p2p sum of squares
              i{d} u{d} a{d} b{d} k{d}  per-day receiver counters: p2p in-count, distinct sender-days, money in,
                                    money out (p2p/qr/cash-out), cash-outs. Days older than 30 are pruned on day roll.
  p:{sender}  {receiver} -> last day this pair transacted (first_time_pair, distinct sender-days)

Window semantics match uvera_ml.features.ai1 exactly: "7d" = the 7 full days before the event's day,
"30d" = the 30 full days before, "today before" = earlier transfers on the same day.
"""
from __future__ import annotations

import math

import numpy as np

DAY = 86_400
FEATURES = ["sender_tenure_days", "amount_log", "amount_z_30d", "amount_to_balance", "sender_out_count_7d",
            "cash_in_gap_min", "device_change_72h", "pin_reset_72h", "first_time_pair",
            "recipient_age_days", "recipient_in_count_7d", "recipient_sender_days_7d", "recipient_in_today_before",
            "recipient_out_in_ratio_7d", "recipient_cashout_count_7d",
            "hour", "is_night", "dow", "channel_ussd"]

_LUA_FEATURES = r"""
local function num(v) if v then return tonumber(v) or 0 end return 0 end
local function features(S, R, P, rid, d, L, sid)
  local sf = {'reg', 'bal', 'bd', 'bs', 'li', 'lip', 'ld', 'lp'}
  for k = 1, 7 do sf[#sf + 1] = 'o' .. (d - k) end
  for k = 1, 30 do local x = d - k; sf[#sf + 1] = 'n' .. x; sf[#sf + 1] = 's' .. x; sf[#sf + 1] = 'q' .. x end
  local sv = redis.call('HMGET', S, unpack(sf))
  local o7 = 0
  for k = 9, 15 do o7 = o7 + num(sv[k]) end
  local c30, s30, q30 = 0, 0, 0
  for k = 16, #sf, 3 do c30 = c30 + num(sv[k]); s30 = s30 + num(sv[k + 1]); q30 = q30 + num(sv[k + 2]) end
  local rf = {'reg', 'i' .. d}
  for k = 1, 7 do local x = d - k; rf[#rf + 1] = 'i' .. x; rf[#rf + 1] = 'u' .. x; rf[#rf + 1] = 'a' .. x; rf[#rf + 1] = 'b' .. x; rf[#rf + 1] = 'k' .. x end
  local rv = redis.call('HMGET', R, unpack(rf))
  local i7, u7, a7, b7, k7 = 0, 0, 0, 0, 0
  for k = 3, #rf, 5 do i7 = i7 + num(rv[k]); u7 = u7 + num(rv[k + 1]); a7 = a7 + num(rv[k + 2]); b7 = b7 + num(rv[k + 3]); k7 = k7 + num(rv[k + 4]) end
  local bal = redis.call('HGET', L, sid)  -- start-of-day ledger snapshot (core banking), if loaded for day d
  if not bal then
    bal = sv[2]  -- fallback: balance rebuilt from the event stream
    if sv[3] and tonumber(sv[3]) == d then bal = sv[4] end
  end
  local pair = redis.call('HEXISTS', P, rid)
  return {sv[1] or '', bal or '', sv[5] or '', sv[6] or '', sv[7] or '', sv[8] or '',
          tostring(o7), tostring(c30), tostring(s30), tostring(q30),
          rv[1] or '', rv[2] or '0', tostring(i7), tostring(u7), tostring(a7), tostring(b7), tostring(k7), tostring(pair)}
end
"""

# KEYS: c:{sender} c:{receiver} p:{sender} ledger:sod:{day}   ARGV: day receiver_id sender_id
READ_LUA = _LUA_FEATURES + r"""
return features(KEYS[1], KEYS[2], KEYS[3], ARGV[2], tonumber(ARGV[1]), KEYS[4], ARGV[3])
"""

# KEYS: c:{src} c:{dst} p:{src} ledger:sod:{day}   ARGV: etype src_kind dst_kind amount t day want_features dst_id src_id
APPLY_LUA = _LUA_FEATURES + r"""
local METRICS = {'o', 'n', 's', 'q', 'i', 'u', 'a', 'b', 'k'}
local function roll(K, d)
  local bd = tonumber(redis.call('HGET', K, 'bd') or '-1')
  if d <= bd then return end
  redis.call('HSET', K, 'bd', d, 'bs', redis.call('HGET', K, 'bal') or '0')
  if bd >= 0 then
    local del = {}
    for x = math.max(bd - 31, d - 62), d - 31 do
      for _, m in ipairs(METRICS) do del[#del + 1] = m .. x end
    end
    if #del > 0 then redis.call('HDEL', K, unpack(del)) end
  end
end
local e, sk, dk = ARGV[1], tonumber(ARGV[2]), tonumber(ARGV[3])
local amt, t, d = tonumber(ARGV[4]), tonumber(ARGV[5]), tonumber(ARGV[6])
local S, R, P, rid = KEYS[1], KEYS[2], KEYS[3], ARGV[8]
local res = 0
if ARGV[7] == '1' then res = features(S, R, P, rid, d, KEYS[4], ARGV[9]) end
if e == 'device_change' then redis.call('HSET', S, 'ld', t) return res end
if e == 'pin_reset' then redis.call('HSET', S, 'lp', t) return res end
local p2p = (e == 'p2p') and sk == 0 and dk == 0
if sk == 0 then
  roll(S, d)
  if e == 'p2p' or e == 'qr_pay' or e == 'bill_pay' or e == 'recharge' or e == 'cash_out' then redis.call('HINCRBY', S, 'o' .. d, 1) end
  if p2p then
    redis.call('HINCRBY', S, 'n' .. d, 1); redis.call('HINCRBYFLOAT', S, 's' .. d, amt); redis.call('HINCRBYFLOAT', S, 'q' .. d, amt * amt)
  end
  if e == 'p2p' or e == 'qr_pay' or e == 'cash_out' then redis.call('HINCRBYFLOAT', S, 'b' .. d, amt) end
  if e == 'cash_out' or (e == 'qr_pay' and amt >= 1000) then redis.call('HINCRBY', S, 'k' .. d, 1) end
  redis.call('HINCRBYFLOAT', S, 'bal', -amt)
end
if dk == 0 then
  roll(R, d)
  if p2p then
    redis.call('HINCRBY', R, 'i' .. d, 1)
    if redis.call('HGET', P, rid) ~= tostring(d) then
      redis.call('HINCRBY', R, 'u' .. d, 1); redis.call('HSET', P, rid, d)
    end
  end
  redis.call('HINCRBYFLOAT', R, 'a' .. d, amt)
  if e == 'cash_in' or e == 'salary_in' or e == 'remit_in' or e == 'p2p' then
    local li = tonumber(redis.call('HGET', R, 'li') or '-1')
    if li < 0 then redis.call('HSET', R, 'li', t)
    elseif t > li then redis.call('HSET', R, 'lip', li, 'li', t) end
  end
  redis.call('HINCRBYFLOAT', R, 'bal', amt)
end
return res
"""


def keys(sender: str, receiver: str, day: int) -> list[str]:
    return [f"c:{sender}", f"c:{receiver}", f"p:{sender}", f"ledger:sod:{day}"]


def _f(v: str, default: float = math.nan) -> float:
    return float(v) if v not in ("", None) else default


def finalize(raw: list, t: int, amount: float, channel: str, sender_balance: float | None = None) -> np.ndarray:
    """Turn the Lua aggregates into the 19-feature vector (same formulas as build_ai1_features)."""
    d = t // DAY
    (reg_s, bal, li, lip, ld, lp, o7, c30, s30, q30, reg_r, in_today, i7, u7, a7, b7, k7, pair) = raw
    c30, s30, q30 = float(c30), float(s30), float(q30)
    if c30 >= 2:
        mean = s30 / c30
        std = math.sqrt(max(q30 / c30 - mean * mean, 0.0) + (0.1 * mean + 50) ** 2)
        z = (amount - mean) / std
    else:
        z = math.nan
    balance = sender_balance if sender_balance is not None else max(_f(bal, 0.0), 0.0)
    li, lip = _f(li), _f(lip)
    last_in = li if li < t else lip  # strictly before t
    gap = 1440.0 if math.isnan(last_in) or (t - last_in) / 60.0 > 1440 else (t - last_in) / 60.0
    ld, lp = _f(ld), _f(lp)
    sod = t % DAY
    hour = sod / 3600.0
    return np.array([
        d - _f(reg_s, d), math.log1p(amount), z, min(5.0, max(0.0, amount / (balance + 1.0))), float(o7),
        gap, float(not math.isnan(ld) and t - ld <= 72 * 3600), float(not math.isnan(lp) and t - lp <= 72 * 3600),
        float(int(pair) == 0),
        d - _f(reg_r, d), float(i7), float(u7), float(in_today), min(5.0, max(0.0, float(b7) / (float(a7) + 100.0))), float(k7),
        hour, float(hour < 6 or hour >= 22), float(d % 7), float(channel == "ussd"),
    ], dtype=float)

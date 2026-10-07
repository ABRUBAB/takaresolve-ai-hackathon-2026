"""Small helpers for scripted runs: reset worker stats, wait for the stream to drain, save worker stats / drift.

  python -m uvscale.phase reset
  python -m uvscale.phase save /repo/reports/scalability/x.json "description"
  python -m uvscale.phase drift /repo/reports/scalability/drift.json
"""
import json, sys, time, urllib.request as u
import redis
W = "http://feature-worker:9100"
def post(p): u.urlopen(u.Request(W + p, method="POST"), timeout=10)
def get(p): return json.loads(u.urlopen(W + p, timeout=10).read())
def drain():
    r = redis.Redis(host="redis", decode_responses=True)
    while True:
        g = [g for g in r.xinfo_groups("uvera:events") if g["name"] == "features"]
        if g and g[0]["lag"] == 0 and g[0]["pending"] == 0: break
        time.sleep(0.5)
    time.sleep(3)
    return r
if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "reset": post("/stats/reset"); post("/drift/reset")
    elif cmd == "save":
        r = drain(); s = get("/stats"); s["what"] = sys.argv[3]; s["redis_used_memory_mb"] = round(r.info("memory")["used_memory"] / 2**20, 1)
        json.dump(s, open(sys.argv[2], "w"), indent=1); print(json.dumps(s)[:600])
    elif cmd == "drift":
        drain(); d = get("/drift"); json.dump(d, open(sys.argv[2], "w"), indent=1); print(d["status"], d["max_psi"], d["top_drifted"][:4])

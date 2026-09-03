"""End-to-end API smoke test against a running server (default http://127.0.0.1:8000).

    python -m scripts.api_smoke [base_url]
"""

from __future__ import annotations

import io
import sys
import urllib.request
import json
from pathlib import Path

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def call(method: str, path: str, body=None, files=None):
    url = BASE + path
    if files:
        boundary = "----compassboundary1234"
        buf = bytearray()
        for k, v in (body or {}).items():
            buf += f"--{boundary}\r\n".encode()
            buf += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
            buf += f"{v}\r\n".encode()
        for k, (fn, data) in files.items():
            buf += f"--{boundary}\r\n".encode()
            buf += (
                f'Content-Disposition: form-data; name="{k}"; filename="{fn}"\r\n'
                f"Content-Type: text/csv\r\n\r\n"
            ).encode()
            buf += data + b"\r\n"
        buf += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(url, data=bytes(buf), method=method)
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    else:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:  # surface the server's error body
        raise SystemExit(f"{method} {path} -> {e.code}\n{e.read().decode()}") from e


def main() -> int:
    checks: list[tuple[str, bool]] = []

    health = call("GET", "/api/health")
    checks.append(("health ok + offline", health["status"] == "ok" and health["offline"]))

    status = call("GET", "/api/model/status")
    checks.append(("active model present", status["active_version"] is not None))
    checks.append(("corpus 200 rows", status["corpus_size"] == 200))
    checks.append(("13 flagged", status["flagged_count"] == 13))
    checks.append(("faculty matching inactive", status["faculty_matching_active"] is False))
    v_before = status["active_version"]

    flagged = call("GET", "/api/corpus/flagged")
    reasons = {f["flag_reason"] for f in flagged}
    checks.append(("flagged has duplicate_project_id", any("duplicate" in r for r in reasons)))
    checks.append(("flagged excluded from clusters", all(f["cluster_id"] is None for f in flagged)))

    dup = [f for f in flagged if f["project_id"].endswith("-B")]
    checks.append(("duplicate suffixed -B exists", len(dup) == 1))

    # non-quantum student -> must NOT be force-matched
    s = call("POST", "/api/students", {
        "name": "NQ", "skills": ["react", "typescript", "css"],
        "interests": ["web design", "accessibility"], "tech_comfort": "high",
    })
    rec = call("POST", "/api/recommendations", {"student_id": s["id"], "filters": {}})
    checks.append(("non-quantum -> low_confidence/no_signal",
                   rec["mode"] in {"low_confidence", "no_signal"}))
    checks.append(("every rec cites a project_id",
                   all(r["project_id"] for r in rec["recommendations"])))
    checks.append(("every rec has a real cosine score",
                   all(isinstance(r["similarity"], (int, float)) for r in rec["recommendations"])))
    checks.append(("no rec claims 100%",
                   all(r["similarity"] < 1.0 for r in rec["recommendations"])))

    # quantum student -> routed
    q = call("POST", "/api/students", {
        "name": "Q", "skills": ["qiskit", "python", "linear algebra"],
        "interests": ["quantum machine learning", "optimization"],
    })
    qrec = call("POST", "/api/recommendations", {"student_id": q["id"]})
    checks.append(("quantum -> routed", qrec["mode"] == "routed"))
    checks.append(("routed rec has recommendation_id",
                   all(r.get("recommendation_id") for r in qrec["recommendations"])))

    refine = call("POST", "/api/recommendations/refine", {
        "student_id": q["id"], "constraint": "show me more optimization ideas, avoid AR/VR",
    })
    hay = " ".join((r["title"] + r["statement"]).lower() for r in refine["recommendations"])
    checks.append(("refine parsed negative ar/vr", "ar/vr" in refine["refinement"]["negative"]))
    checks.append(("refine removed AR/VR titles", " ar " not in hay and "ar/vr" not in hay))

    fb = call("POST", "/api/feedback", {
        "recommendation_id": qrec["recommendations"][0]["recommendation_id"], "verdict": "accept",
    })
    checks.append(("feedback accepted", fb["verdict"] == "accept"))

    fac = call("GET", "/api/faculty-preferences")
    checks.append(("faculty prefs empty + inactive",
                   fac["active_in_scoring"] is False))
    call("POST", "/api/faculty-preferences", {
        "faculty_name": "Dr Test", "domain": "quantum ml", "notes": "likes VQE topics",
    })
    fac2 = call("GET", "/api/faculty-preferences")
    checks.append(("faculty pref added but still inactive in scoring",
                   len(fac2["items"]) == 1 and fac2["active_in_scoring"] is False))

    # upload a tiny CSV batch + retrain
    csv = (
        "ProjectID,Title,Problem Statement\n"
        "BATCH-900,Edge ML for Wearables,"
        "\"On-device inference on low-power wearables is constrained by memory and battery; "
        "explore quantised models and scheduling to keep latency under 50ms.\"\n"
        "BATCH-901,,\"missing title row, should be flagged as missing_title on ingest\"\n"
        "BATCH-902,Numeric Statement Row,0\n"
    )
    up = call("POST", "/api/corpus/upload", body={"source_batch": "smoke-batch"},
              files={"file": ("batch.csv", csv.encode())})
    checks.append(("upload inserted 3", up["inserted"] == 3))
    checks.append(("upload flagged 2 of 3", up["report"]["flagged_rows"] == 2))

    mv = call("POST", "/api/model/retrain", {"notes": "smoke"})
    checks.append(("retrain bumped version", mv["version"] == v_before + 1))
    status2 = call("GET", "/api/model/status")
    checks.append(("new version active", status2["active_version"] == v_before + 1))
    checks.append(("corpus grew by 3", status2["corpus_size"] == 203))
    checks.append(("previous version retained", len(status2["versions"]) >= 2))

    # rollback
    call("POST", "/api/model/activate", {"version": v_before})
    status3 = call("GET", "/api/model/status")
    checks.append(("rollback works", status3["active_version"] == v_before))

    print()
    ok = True
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    print()
    print("ALL PASSED" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

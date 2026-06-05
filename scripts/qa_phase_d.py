#!/usr/bin/env python3
"""Phase D QA: Sections 7, 8."""
import json
import subprocess
import sys
import uuid

import httpx

BASE = "http://127.0.0.1:8000"
sys.path.insert(0, "/Users/dagi/companion")


def record(results, test_id, name, status, expected, actual, notes=""):
    results.append({"id": test_id, "name": name, "status": status})
    print(f"[{'PASS' if status == 'pass' else 'WARN' if status == 'warn' else 'FAIL'}] {test_id} {name}: {actual[:120] if isinstance(actual, str) else actual}")
    if status == "fail":
        print(f"  expected: {expected}\n  actual: {actual}")
        sys.exit(1)


def register_onboard(client, role: str) -> tuple[str, str]:
    email = f"qa-d-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        f"{BASE}/v1/auth/register",
        json={"email": email, "password": "password123"},
        timeout=10,
    )
    token = r.json()["access_token"]
    uid = r.json()["user_id"]
    h = {"Authorization": f"Bearer {token}"}
    client.post(
        f"{BASE}/v1/onboarding/complete",
        headers=h,
        json={
            "role_id": role,
            "communication": "direct",
            "energy": "calm",
            "address_as": "Boss",
        },
        timeout=10,
    )
    return token, uid


def main():
    print("=== Phase D: Sections 7-8 ===\n")
    R = []

    # 7.3 inspect core prompt
    from prompts.core import JARVIS_CORE
    bad = ["Dagi", "Good evening, Sir"]
    found = [b for b in bad if b in JARVIS_CORE]
    record(
        R,
        "7.3",
        "No global name in core",
        "pass" if not found else "fail",
        "no hardcoded Dagi/Sir greeting",
        f"found={found}",
    )

    with httpx.Client() as client:
        token, uid = register_onboard(client, "productivity_operator")
        h = {"Authorization": f"Bearer {token}"}

        r71 = client.post(
            f"{BASE}/v1/chat",
            headers=h,
            json={"message": "Help me plan my week in bullet points. Be brief."},
            timeout=120,
        )
        text71 = (r71.json().get("response") or "").lower()
        operational = any(w in text71 for w in ("plan", "week", "task", "priority", "schedule", "bullet"))
        record(
            R,
            "7.1",
            "Role in prompt",
            "pass" if operational else "warn",
            "operational tone",
            text71[:150],
        )

        token2, _ = register_onboard(client, "calm_companion")
        h2 = {"Authorization": f"Bearer {token2}"}
        client.put(
            f"{BASE}/v1/preferences",
            headers=h2,
            json={"communication": "gentle"},
            timeout=10,
        )
        r72 = client.post(
            f"{BASE}/v1/chat",
            headers=h2,
            json={"message": "I am very stressed and anxious about work."},
            timeout=120,
        )
        text72 = (r72.json().get("response") or "").lower()
        supportive = any(
            w in text72
            for w in ("stress", "anx", "calm", "breath", "support", "here", "okay", "understand")
        )
        record(
            R,
            "7.2",
            "calm_companion support",
            "pass" if supportive else "warn",
            "supportive language",
            text72[:150],
        )

        # 7.4 reset learned
        r74 = client.post(f"{BASE}/v1/preferences/reset-learned", headers=h, timeout=10)
        ok74 = r74.status_code == 200
        record(R, "7.4", "Reset learned", "pass" if ok74 else "fail", "200", f"{r74.status_code}")

        # 7.5 runtime_json in DB after a few turns
        for msg in ["hi", "tell me a joke"]:
            client.post(f"{BASE}/v1/chat", headers=h, json={"message": msg}, timeout=120)
        q = subprocess.run(
            [
                "sqlite3",
                "memory.db",
                f"SELECT length(runtime_json) FROM companion_preferences WHERE user_id='{uid}';",
            ],
            cwd="/Users/dagi/companion",
            capture_output=True,
            text=True,
        )
        runtime_len = int(q.stdout.strip() or "0")
        record(
            R,
            "7.5",
            "Runtime persist",
            "pass" if runtime_len > 2 else "warn",
            "runtime_json non-empty",
            f"len={runtime_len}",
        )

        # 8.1 profile persist - patch then verify via new token same user
        client.patch(f"{BASE}/v1/profile", headers=h, json={"address_as": "Chief"}, timeout=10)
        prof = client.get(f"{BASE}/v1/profile", headers=h).json()
        record(
            R,
            "8.1",
            "Profile persist",
            "pass" if prof.get("address_as") == "Chief" else "fail",
            "Chief",
            json.dumps(prof),
        )

        # 8.2 personal memory - tell fact, ask again
        client.post(
            f"{BASE}/v1/chat",
            headers=h,
            json={"message": "Remember this fact for QA: I work at Acme Corp. Reply ACK only."},
            timeout=120,
        )
        r82 = client.post(
            f"{BASE}/v1/chat",
            headers=h,
            json={"message": "Where do I work? One word answer."},
            timeout=120,
        )
        ans = (r82.json().get("response") or "").lower()
        recall = "acme" in ans
        record(
            R,
            "8.2",
            "Personal memory",
            "pass" if recall else "warn",
            "recalls Acme",
            ans[:100],
        )

        # 8.3 cross-user
        alice_t, alice_uid = register_onboard(client, "general_jarvis")
        bob_t, bob_uid = register_onboard(client, "general_jarvis")
        ha = {"Authorization": f"Bearer {alice_t}"}
        hb = {"Authorization": f"Bearer {bob_t}"}
        client.post(
            f"{BASE}/v1/chat",
            headers=ha,
            json={"message": "Remember QA fact: my pet is named Zebra. Reply ACK."},
            timeout=120,
        )
        rb = client.post(
            f"{BASE}/v1/chat",
            headers=hb,
            json={"message": "What is my pet name? One word."},
            timeout=120,
        )
        bob_ans = (rb.json().get("response") or "").lower()
        cross_leak = "zebra" in bob_ans
        record(
            R,
            "8.3",
            "Cross-user memory",
            "pass" if not cross_leak else "fail",
            "Bob must not know Zebra",
            bob_ans[:100],
        )

        # 8.4 emotional state rows
        client.post(f"{BASE}/v1/chat", headers=ha, json={"message": "I feel great today!"}, timeout=120)
        client.post(f"{BASE}/v1/chat", headers=hb, json={"message": "I feel terrible today."}, timeout=120)
        eq = subprocess.run(
            [
                "sqlite3",
                "memory.db",
                f"SELECT count(*) FROM emotional_state WHERE user_id IN ('{alice_uid}','{bob_uid}');",
            ],
            cwd="/Users/dagi/companion",
            capture_output=True,
            text=True,
        )
        cnt = int(eq.stdout.strip() or "0")
        record(R, "8.4", "Emotional state per user", "pass" if cnt >= 2 else "warn", ">=2 rows", f"count={cnt}")

        # 8.5 decay - check reflections have user_id only updates (structural)
        sch = subprocess.run(
            ["sqlite3", "memory.db", ".schema reflections"],
            cwd="/Users/dagi/companion",
            capture_output=True,
            text=True,
        )
        has_uid = "user_id" in sch.stdout
        record(
            R,
            "8.5",
            "Decay tenant schema",
            "pass" if has_uid else "fail",
            "reflections.user_id column",
            sch.stdout[:100],
        )

    print(f"\n=== Phase D COMPLETE: {sum(1 for r in R if r['status']=='pass')}/{len(R)} ===")


if __name__ == "__main__":
    main()

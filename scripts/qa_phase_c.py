#!/usr/bin/env python3
"""Phase C QA: Sections 5, 6 (OpenAI calls)."""
import json
import subprocess
import sys
import uuid

import httpx

BASE = "http://127.0.0.1:8000"
RESULTS = []


def record(test_id, name, status, expected, actual, notes=""):
    RESULTS.append({"id": test_id, "name": name, "status": status, "expected": expected, "actual": actual, "notes": notes})
    print(f"[{'PASS' if status == 'pass' else 'WARN' if status == 'warn' else 'FAIL'}] {test_id} {name}")
    if status == "fail":
        print(f"  expected: {expected}\n  actual: {actual}\n  {notes}")
        for r in RESULTS:
            print(json.dumps(r))
        sys.exit(1)


def register_onboard(client, email: str, address: str, communication: str = "balanced") -> str:
    r = client.post(
        f"{BASE}/v1/auth/register",
        json={"email": email, "password": "password123"},
        timeout=10,
    )
    if r.status_code == 409:
        r = client.post(
            f"{BASE}/v1/auth/login",
            json={"email": email, "password": "password123"},
            timeout=10,
        )
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    client.post(
        f"{BASE}/v1/onboarding/complete",
        headers=h,
        json={
            "communication": communication,
            "energy": "calm",
            "address_as": address,
        },
        timeout=10,
    )
    return token


def parse_sse(body: str) -> list[dict]:
    events = []
    for line in body.split("\n"):
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


def main():
    print("=== Phase C: Sections 5-6 ===\n")
    with httpx.Client() as client:
        token = register_onboard(
            client,
            f"qa-c-alice-{uuid.uuid4().hex[:6]}@example.com",
            "Sir",
            "gentle",
        )
        h = {"Authorization": f"Bearer {token}"}

        # 5.1 sync chat
        r = client.post(
            f"{BASE}/v1/chat",
            headers=h,
            json={"message": "hey do you know who i am"},
            timeout=120,
        )
        data = r.json() if r.status_code == 200 else {}
        ok = (
            r.status_code == 200
            and "response" in data
            and "intent" in data
            and "response_time_s" in data
        )
        record(
            "5.1",
            "Sync chat",
            "pass" if ok else "fail",
            "200 with response, intent, response_time_s",
            f"{r.status_code} keys={list(data.keys())} resp={str(data.get('response',''))[:80]}",
        )

        # 5.2 stream
        with client.stream(
            "POST",
            f"{BASE}/v1/chat/stream",
            headers=h,
            json={"message": "hello"},
            timeout=120,
        ) as resp:
            body = resp.read().decode()
            status = resp.status_code
        events = parse_sse(body)
        types = [e.get("type") for e in events]
        has_token = "token" in types
        has_done = "done" in types
        ok2 = status == 200 and has_token and has_done
        record(
            "5.2",
            "Stream chat",
            "pass" if ok2 else "fail",
            "token + done SSE events",
            f"status={status} types={types[:10]} len={len(body)}",
        )

        # 5.4 address in reply (qualitative)
        r54 = client.post(
            f"{BASE}/v1/chat",
            headers=h,
            json={"message": "what should you call me? answer in one short sentence."},
            timeout=120,
        )
        resp_text = (r54.json().get("response") or "").lower() if r54.status_code == 200 else ""
        mentions = any(x in resp_text for x in ("chief", "sir", "boss", "call"))
        record(
            "5.4",
            "Address in reply",
            "pass" if mentions else "warn",
            "uses address_as from profile",
            resp_text[:200],
        )

        # 6.1-6.4 two users
        alice_email = f"qa-alice-{uuid.uuid4().hex[:6]}@example.com"
        bob_email = f"qa-bob-{uuid.uuid4().hex[:6]}@example.com"
        alice_t = register_onboard(client, alice_email, "Sir", "gentle")
        bob_t = register_onboard(client, bob_email, "Boss", "direct")
        ha = {"Authorization": f"Bearer {alice_t}"}
        hb = {"Authorization": f"Bearer {bob_t}"}

        ra = client.post(f"{BASE}/v1/auth/register", json={"email": alice_email, "password": "x"})
        # get user ids from me
        me_a = client.get(f"{BASE}/v1/auth/me", headers=ha).json()
        me_b = client.get(f"{BASE}/v1/auth/me", headers=hb).json()
        ok61 = me_a["user_id"] != me_b["user_id"]
        record("6.1", "Two tokens", "pass" if ok61 else "fail", "distinct user_id", f"{me_a['user_id'][:8]} vs {me_b['user_id'][:8]}")

        client.post(
            f"{BASE}/v1/chat",
            headers=ha,
            json={"message": "Remember only for this test: my secret code is ALPHA. Reply OK only."},
            timeout=120,
        )
        rb = client.post(
            f"{BASE}/v1/chat",
            headers=hb,
            json={"message": "What is my secret code? Answer only the code or say you do not know."},
            timeout=120,
        )
        bob_resp = (rb.json().get("response") or "").upper() if rb.status_code == 200 else ""
        leaked = "ALPHA" in bob_resp and "DO NOT" not in bob_resp
        ok62 = rb.status_code == 200 and not leaked
        record(
            "6.2",
            "Conversation isolation",
            "pass" if ok62 else "fail",
            "Bob must not see ALPHA",
            bob_resp[:200],
        )

        pa = client.get(f"{BASE}/v1/profile", headers=ha).json()
        pb = client.get(f"{BASE}/v1/profile", headers=hb).json()
        ok63 = pa.get("address_as") == "Sir" and pb.get("address_as") == "Boss"
        record("6.3", "Profile isolation", "pass" if ok63 else "fail", "Sir vs Boss", f"{pa} | {pb}")

        pra = client.get(f"{BASE}/v1/preferences", headers=ha).json()
        prb = client.get(f"{BASE}/v1/preferences", headers=hb).json()
        ok64 = pra.get("communication") == "gentle" and prb.get("communication") == "direct"
        record("6.4", "Prefs isolation", "pass" if ok64 else "fail", "different communication baselines", f"{pra.get('communication')} vs {prb.get('communication')}")

        # 6.5 SQL
        q = subprocess.run(
            [
                "sqlite3",
                "memory.db",
                "SELECT user_id, key, value FROM user_profile WHERE key='address_as' ORDER BY user_id LIMIT 20;",
            ],
            cwd="/Users/dagi/companion",
            capture_output=True,
            text=True,
        )
        lines = [ln for ln in q.stdout.strip().split("\n") if ln]
        uids = {ln.split("|")[0] for ln in lines if "|" in ln}
        ok65 = len(uids) >= 2 or len(lines) >= 2
        record("6.5", "SQL spot-check", "pass" if ok65 else "warn", "multiple user_id rows", q.stdout[:300])

    print(f"\n=== Phase C COMPLETE: {sum(1 for r in RESULTS if r['status']=='pass')}/{len(RESULTS)} ===")
    warns = [r for r in RESULTS if r["status"] == "warn"]
    if warns:
        print(f"Warnings: {len(warns)}")


if __name__ == "__main__":
    main()

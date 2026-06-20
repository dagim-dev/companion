#!/usr/bin/env python3
"""Phase B QA: Sections 3, 4."""
import json
import sys
import uuid

import httpx

BASE = "http://127.0.0.1:8000"
VALID_ROLES = {"general_nova"}
RESULTS = []


def record(test_id, name, status, expected, actual, notes=""):
    RESULTS.append({"id": test_id, "name": name, "status": status, "expected": expected, "actual": actual, "notes": notes})
    print(f"[{'PASS' if status == 'pass' else 'WARN' if status == 'warn' else 'FAIL'}] {test_id} {name}")
    if status == "fail":
        print(f"  expected: {expected}\n  actual: {actual}\n  {notes}")
        for r in RESULTS:
            print(json.dumps(r))
        sys.exit(1)


def register_fresh(client: httpx.Client) -> tuple[str, str]:
    email = f"qa-b-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        f"{BASE}/v1/auth/register",
        json={"email": email, "password": "password123"},
        timeout=10,
    )
    if r.status_code != 200:
        raise RuntimeError(f"register failed: {r.status_code} {r.text}")
    return r.json()["access_token"], email


def main():
    print("=== Phase B: Sections 3-4 ===\n")
    with httpx.Client() as client:
        token, _ = register_fresh(client)
        h = {"Authorization": f"Bearer {token}"}

        # 3.1 chat gate
        r = client.post(f"{BASE}/v1/chat", headers=h, json={"message": "hi"}, timeout=30)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        detail = body.get("detail", body)
        code = detail.get("code") if isinstance(detail, dict) else None
        ok = r.status_code == 409 and code == "needs_onboarding"
        record("3.1", "Chat gate", "pass" if ok else "fail", "409 needs_onboarding", f"{r.status_code} {json.dumps(detail)[:200]}")

        # 3.2 roles compatibility
        r2 = client.get(f"{BASE}/v1/onboarding/roles", headers=h, timeout=10)
        roles = r2.json() if r2.status_code == 200 else []
        ids = {x["id"] for x in roles} if isinstance(roles, list) else set()
        ok2 = r2.status_code == 200 and ids == VALID_ROLES
        record("3.2", "Role catalog", "pass" if ok2 else "fail", f"NOVA-only {VALID_ROLES}", f"status={r2.status_code} ids={ids}")

        # 3.4 invalid role (before complete)
        r4 = client.post(
            f"{BASE}/v1/onboarding/complete",
            headers=h,
            json={
                "role_id": "invalid",
                "communication": "balanced",
                "energy": "calm",
                "address_as": "Friend",
            },
            timeout=10,
        )
        ok4 = r4.status_code == 400
        record("3.4", "Invalid role", "pass" if ok4 else "fail", "400", f"{r4.status_code} {r4.text[:150]}")

        # 3.5 invalid communication
        r5 = client.post(
            f"{BASE}/v1/onboarding/complete",
            headers=h,
            json={
                "role_id": "general_nova",
                "communication": "harsh",
                "energy": "calm",
                "address_as": "Friend",
            },
            timeout=10,
        )
        ok5 = r5.status_code == 422
        record("3.5", "Invalid communication", "pass" if ok5 else "fail", "422", f"{r5.status_code}")

        # 3.3 complete onboarding
        r3 = client.post(
            f"{BASE}/v1/onboarding/complete",
            headers=h,
            json={
                "communication": "gentle",
                "energy": "calm",
                "challenge_level": "low",
                "emotional_support": "high",
                "address_as": "Boss",
            },
            timeout=10,
        )
        prefs = r3.json() if r3.status_code == 200 else {}
        ok3 = r3.status_code == 200 and prefs.get("onboarding_completed") is True
        record("3.3", "Complete onboarding", "pass" if ok3 else "fail", "200 onboarding_completed true", f"{r3.status_code} {json.dumps(prefs)[:200]}")

        # 3.6 GET preferences
        r6 = client.get(f"{BASE}/v1/preferences", headers=h, timeout=10)
        p6 = r6.json() if r6.status_code == 200 else {}
        ok6 = r6.status_code == 200 and p6.get("role_id") == "general_nova"
        record("3.6", "GET preferences", "pass" if ok6 else "fail", "general_nova", json.dumps(p6)[:200])

        # 3.7 PUT preferences
        r7 = client.put(
            f"{BASE}/v1/preferences",
            headers=h,
            json={"communication": "direct", "challenge_level": "high"},
            timeout=10,
        )
        r7b = client.get(f"{BASE}/v1/preferences", headers=h, timeout=10)
        p7 = r7b.json() if r7b.status_code == 200 else {}
        ok7 = r7.status_code == 200 and p7.get("challenge_level") == "high"
        record("3.7", "PUT preferences", "pass" if ok7 else "fail", "challenge_level high", json.dumps(p7)[:200])

        # 3.8 me after onboard
        r8 = client.get(f"{BASE}/v1/auth/me", headers=h, timeout=10)
        me = r8.json() if r8.status_code == 200 else {}
        ok8 = me.get("onboarding_completed") is True
        record("3.8", "Me after onboard", "pass" if ok8 else "fail", "onboarding_completed true", json.dumps(me))

        # 4.1 GET profile
        r41 = client.get(f"{BASE}/v1/profile", headers=h, timeout=10)
        prof = r41.json() if r41.status_code == 200 else {}
        ok41 = prof.get("address_as") == "Boss"
        record("4.1", "GET profile", "pass" if ok41 else "fail", "address_as Boss", json.dumps(prof))

        # 4.2 PATCH profile
        r42 = client.patch(f"{BASE}/v1/profile", headers=h, json={"address_as": "Chief"}, timeout=10)
        r42b = client.get(f"{BASE}/v1/profile", headers=h, timeout=10)
        prof2 = r42b.json() if r42b.status_code == 200 else {}
        ok42 = r42.status_code == 200 and prof2.get("address_as") == "Chief"
        record("4.2", "PATCH profile", "pass" if ok42 else "fail", "Chief", json.dumps(prof2))

        # 4.3 empty
        r43 = client.patch(f"{BASE}/v1/profile", headers=h, json={"address_as": ""}, timeout=10)
        ok43 = r43.status_code == 422
        record("4.3", "Empty address_as", "pass" if ok43 else "fail", "422", f"{r43.status_code}")

        # 4.4 max length
        r44 = client.patch(f"{BASE}/v1/profile", headers=h, json={"address_as": "x" * 33}, timeout=10)
        ok44 = r44.status_code == 422
        record("4.4", "Max length address_as", "pass" if ok44 else "fail", "422", f"{r44.status_code}")

    print(f"\n=== Phase B COMPLETE: {sum(1 for r in RESULTS if r['status']=='pass')}/{len(RESULTS)} ===")
    print("Note: 4.5-4.7 UI tests deferred to Phase E browser checks")


if __name__ == "__main__":
    main()

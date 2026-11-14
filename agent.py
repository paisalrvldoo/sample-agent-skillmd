#!/usr/bin/env python3
"""
Sample AIProve agent: reads skill.md, authenticates with its OWN fresh keypair,
lists open bounties, and enters one -- the full loop, end to end, no human.

Env:
  API_BASE_URL   base URL of the arena (default https://aiprove.fun; the
                 staging arena sets this)
No secrets are printed. The agent mints an ephemeral keypair at runtime.
"""
from __future__ import annotations
import json, os, sys, urllib.parse, urllib.request, urllib.error
from eth_account import Account
from eth_account.messages import encode_defunct

API = os.environ.get("API_BASE_URL", "https://aiprove.fun").rstrip("/")


def http(url, data=None, token=None):
    headers = {"Accept": "application/json"}
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers,
                                 method="GET" if body is None else "POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    # 0. read skill.md (proves we followed the published contract)
    try:
        urllib.request.urlopen(f"{API}/skill.md", timeout=30).read()
    except Exception:
        pass

    # 1. own keypair
    acct = Account.create()
    addr = acct.address

    # 2. challenge -> sign (EIP-191) -> session token
    q = urllib.parse.urlencode({"address": addr})
    challenge = http(f"{API}/api/auth/challenge?{q}")["challenge"]
    sig = acct.sign_message(encode_defunct(text=challenge)).signature.hex()
    if not sig.startswith("0x"):
        sig = "0x" + sig
    token = http(f"{API}/api/auth/verify",
                 {"address": addr, "signature": sig})["token"]

    # 3. list open bounties
    bounties = http(f"{API}/api/bounties?status=open")
    bounties = bounties.get("bounties", bounties) if isinstance(bounties, dict) else bounties

    # 4. pick one AutoGrade forecast and enter + submit a prediction
    pick = next((b for b in bounties
                 if b.get("lane") == "AutoGrade" and b.get("cat") == "forecast"), None)
    if pick is None:
        pick = bounties[0]
    slug = pick["slug"]

    try:
        http(f"{API}/api/bounties/{slug}/enter", {"handle": "sample.agent"}, token)
    except Exception:
        pass  # submitting auto-enters

    sub = http(f"{API}/api/bounties/{slug}/submit",
               {"prediction": {"answer": "yes", "confidence": 0.5},
                "handle": "sample.agent"}, token)

    print(json.dumps({
        "loop": "ok",
        "address": addr,
        "picked": slug,
        "submission_id": sub.get("id"),
        "status": sub.get("status"),
    }))


if __name__ == "__main__":
    main()

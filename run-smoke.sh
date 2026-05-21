#!/usr/bin/env bash
# Smoke test — encodes all Phase 0 acceptance criteria.
# Exits 0 only when every check passes.
set -euo pipefail

OPENSEARCH_URL="http://localhost:9200"
INDEX="searchlab-v0"
SAMPLE_PDF="test-corpus/sample.pdf"
KNOWN_PHRASE="avian carriers"

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1" >&2; exit 1; }

echo "=== SearchLab Phase 0 Smoke Test ==="
echo

# ── Check 1: OpenSearch is up ────────────────────────────────────────────────
echo "Check 1: OpenSearch reachable at $OPENSEARCH_URL"
if ! curl -sf "$OPENSEARCH_URL" > /dev/null; then
    fail "OpenSearch not reachable. Run: docker compose up -d"
fi
pass "OpenSearch is up"

# ── Check 2: Ingest and count chunks ─────────────────────────────────────────
echo
echo "Check 2: Ingest $SAMPLE_PDF and verify chunk count > 0"

# Delete index if it exists so we start clean
curl -sf -X DELETE "$OPENSEARCH_URL/$INDEX" > /dev/null 2>&1 || true
sleep 1

./searchlab ingest "$SAMPLE_PDF"

COUNT=$(curl -sf "$OPENSEARCH_URL/$INDEX/_count" | python3 -c "import sys,json; print(json.load(sys.stdin)['count'])")
if [[ "$COUNT" -le 0 ]]; then
    fail "Chunk count is $COUNT — expected > 0"
fi
pass "Chunk count after ingest: $COUNT"

# ── Check 3: Query returns a hit ─────────────────────────────────────────────
echo
echo "Check 3: Query for known phrase returns at least one hit"

./searchlab query "$KNOWN_PHRASE" | tee /tmp/query_output.txt

HITS=$(grep -c "avian\|carrier\|pigeon\|bird\|IP" /tmp/query_output.txt 2>/dev/null || echo 0)
# More reliable: check the table has at least one data row (rank 1)
if ! grep -q "^1 " /tmp/query_output.txt 2>/dev/null && ! grep -qE "^1\s" /tmp/query_output.txt 2>/dev/null; then
    fail "Query returned no ranked results"
fi
pass "Query returned results"

# ── Check 4: Re-ingest is idempotent ─────────────────────────────────────────
echo
echo "Check 4: Re-ingest does not increase chunk count (idempotency)"

./searchlab ingest "$SAMPLE_PDF"
sleep 1

COUNT2=$(curl -sf "$OPENSEARCH_URL/$INDEX/_count" | python3 -c "import sys,json; print(json.load(sys.stdin)['count'])")
if [[ "$COUNT2" -ne "$COUNT" ]]; then
    fail "Chunk count changed from $COUNT to $COUNT2 after re-ingest (not idempotent)"
fi
pass "Chunk count unchanged after re-ingest: $COUNT2"

echo
echo "=== All checks passed ==="

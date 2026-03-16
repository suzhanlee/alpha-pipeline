#!/usr/bin/env bash
# 동시 백테스트 실행 스크립트 — 두 개의 백테스트를 동시에 실행하고 SSE 스트림을 관찰한다.
#
# 사용법:
#   chmod +x scripts/run_concurrent.sh
#   ./scripts/run_concurrent.sh
#
# 정상적인 경우: 각 run_id가 자기 자신의 step/ticker 정보만 스트리밍해야 한다.
# 비정상적인 경우: 한 쪽 스트림에서 다른 쪽 run_id의 데이터가 섞여 나온다.

BASE="http://localhost:8000"

echo "=== Starting two concurrent backtests ==="

# Launch MACD and SMA simultaneously
RUN1=$(curl -s -X POST "$BASE/api/backtest" \
  -H "Content-Type: application/json" \
  -d '{"strategy":"macd"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['run_id'])")

RUN2=$(curl -s -X POST "$BASE/api/backtest" \
  -H "Content-Type: application/json" \
  -d '{"strategy":"sma_cross"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['run_id'])")

echo "Run 1 (macd):      $RUN1"
echo "Run 2 (sma_cross): $RUN2"
echo ""
echo "=== Streaming progress for Run 1 ==="
echo "Watch if any event contains run_id=$RUN2 — that would indicate a race condition."
echo ""

curl -N "$BASE/api/progress/$RUN1" &
STREAM_PID=$!

sleep 5
kill $STREAM_PID 2>/dev/null

echo ""
echo "=== Results ==="
echo "Run 1:" && curl -s "$BASE/api/result/$RUN1" | python3 -m json.tool
echo "Run 2:" && curl -s "$BASE/api/result/$RUN2" | python3 -m json.tool

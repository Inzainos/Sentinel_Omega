#!/bin/bash
echo "--- Starting API (8787) ---"
python3 -m uvicorn sentinel_omega.infrastructure.dashboard.api:app --host 0.0.0.0 --port 8787 > api_log.txt 2>&1 &
echo "--- Starting Dash/Plotly Principal (8128) ---"
cd /home/deamon/Sentinel_Omega/sentinel_omega/infrastructure/dashboard/dash && { python app.py > dash_log.txt 2>&1 & }
echo "--- Starting React/Vite Legacy (5173) ---"
cd /home/deamon/Sentinel_Omega/sentinel_omega/infrastructure/dashboard/web && { npm run dev -- --host 0.0.0.0 > web_log.txt 2>&1 & }
echo "Waiting for stabilization..."
sleep 10
echo "--- API Log ---"
cat api_log.txt
echo "--- Dash Log ---"
cat dash_log.txt
echo "--- Web Log ---"
cat web_log.txt
ss -tulpn | grep -E '8787|8128|5173'

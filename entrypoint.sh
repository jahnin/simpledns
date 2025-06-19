#!/bin/sh
set -e

# If Corefile volume is empty on first run, seed it with template
if [ ! -f /etc/coredns/Corefile ]; then
  cp /app/Corefile.template /etc/coredns/Corefile
fi

# Start CoreDNS in the background and capture PID for hot‑reloads
coredns -conf /etc/coredns/Corefile &
export COREDNS_PID=$!
echo "CoreDNS started (pid $COREDNS_PID)"

# Launch Flask app (consider gunicorn for prod)
python /app/app.py

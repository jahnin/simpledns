#!/bin/sh
set -e

COREFILE=/etc/coredns/Corefile
TEMPLATE=/app/Corefile.template

# If the Corefile doesn’t exist yet, copy the template in place
if [ ! -f "$COREFILE" ]; then
  cp "$TEMPLATE" "$COREFILE"
fi

# If DNS_FORWARDERS is set, replace commas with spaces and patch the Corefile
if [ -n "$DNS_FORWARDERS" ]; then
  # Convert "1.1.1.1,2.2.2.2"  ->  "1.1.1.1 2.2.2.2"
  FORWARD_LIST=$(echo "$DNS_FORWARDERS" | tr ',' ' ')

  # Rewrite only the IP list after "forward ."
  # Keeps any leading whitespace and trailing comment intact
  sed -i -E \
    "s#^(\\s*forward \\.)[^#]*#\\1 ${FORWARD_LIST} #" \
    "$COREFILE"
fi

# Start CoreDNS in the background (PID captured for hot reloads)
coredns -conf "$COREFILE" &
export COREDNS_PID=$!
echo "CoreDNS started (pid $COREDNS_PID)"

# Environment‑driven defaults:
: "${GUNICORN_WORKERS:=4}"        # default 4 workers
: "${GUNICORN_BIND:=0.0.0.0:8000}"# default bind address

exec gunicorn -w "$GUNICORN_WORKERS" -b "$GUNICORN_BIND" app:app
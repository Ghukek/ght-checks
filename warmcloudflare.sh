#!/bin/bash

set -a  # automatically export variables
source .env
set +a

# Host variants to cover
HOSTS=(
  "https://ghukek.com"
  "https://www.ghukek.com"
)

# Frequently updated pages (fast warm)
FAST_PATHS=(
  "/ght-i.html"
  "/ght-i-raw.html"
  "/lookups.json"
  "/lookupsex.json"
  "/base.json"
  "/basex.json"
  "/script.js"
  "/styles.css"
)

# Full site list (includes everything)
FULL_PATHS=(
  "${FAST_PATHS[@]}"
  "/ght-i-offline.html"
  "/sw.js"
  "/icon-192.png"
  "/grkkeyboard.png"
  "/"
  "/public_domain_icon_200x200.png"
  "/manifest.json"
  "/alt/MBSBx.json"
  "/alt/datadates.json"
  "/alt/KJVNA.json"
  "/alt/MBSB.json"
  "/alt/BSBx.json"
  "/alt/BSB.json"
  "/alt/Tyn1526SP.json"
  "/alt/KJV1769x.json"
  "/alt/KJV1769.json"
  "/alt/WycSPx.json"
  "/alt/WycSP.json"
  "/alt/Tyn1534x.json"
  "/alt/Tyn1534.json"
  "/alt/Gen1599x.json"
  "/alt/Gen1599.json"
  "/alt/WEBx.json"
  "/alt/WEB.json"
  "/alt/MSBx.json"
  "/alt/MSB.json"
  "/alt/KJV1611x.json"
  "/alt/KJV1611.json"
  "/alt/Wycliffex.json"
  "/alt/Wycliffe.json"
  "/alt/VULGATE.json"
  "/alt/VULGATEx.json"
  "/ght.html"
  "/ghtg.html"
  "/index.html"
  "/jsonsource.html"
  "/miniatures.html"
  "/nicene.html"
  "/public_domain_icon_200x200.png"
  "/uniqueght.html"
  # add all pages here
)

MODE=${1:-fast}

if [[ "$MODE" == "full" ]]; then
  PATHS=("${FULL_PATHS[@]}")
  echo "Running FULL purge + warm..."

elif [[ "$MODE" == "single" ]]; then
  if [[ -z "$2" ]]; then
    echo "Usage: $0 single <path>"
    exit 1
  fi

  PATHS=("$2")
  echo "Running SINGLE purge for: $2"

else
  PATHS=("${FAST_PATHS[@]}")
  echo "Running FAST purge + warm..."
fi
# Build full URLs for all hosts
URLS=()
for path in "${PATHS[@]}"; do
  [[ "$path" != /* ]] && path="/$path"
  for host in "${HOSTS[@]}"; do
    URLS+=("${host}${path}")
  done
done

# Convert URLs array to JSON
JSON_URLS=$(printf '%s\n' "${URLS[@]}" | jq -R . | jq -s .)

echo ""
echo "Purging Cloudflare cache..."

curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  --data "{\"files\": $JSON_URLS}"

echo ""
echo "Warming cache..."

for url in "${URLS[@]}"; do
  echo "Fetching: $url"

  for i in {1..2}; do
    curl -s -D - -o /dev/null "$url" | grep -i "cf-cache-status"
  done

  echo ""
done

echo "Done."

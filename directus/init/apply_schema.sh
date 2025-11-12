#!/bin/sh
echo "[INIT] Applying schema snapshot..."
npx directus schema apply /directus/schema.yaml || true

#!/bin/bash
# Bloom — monthly data refresh (local).
# A headless Claude pass re-researches Singapore enrichment centres and updates
# ONLY data/raw_*.json (no shell/git given to the model). This script then
# validates the JSON, rebuilds classes.json, and deploys if anything changed.
# Run by the com.bloom.refresh LaunchAgent, 04:00 SGT on the 1st of each month.
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
BLOOM="$HOME/bloom-enrichment"
CLAUDE="$HOME/.local/bin/claude"
mkdir -p "$BLOOM/logs"
exec >> "$BLOOM/logs/refresh.log" 2>&1
echo "===== $(date '+%Y-%m-%d %H:%M:%S') bloom refresh start ====="
cd "$BLOOM" || exit 1
git pull --quiet origin main || true

PROMPT="Refresh Bloom's Singapore enrichment-centre data. Edit ONLY these files in the current repo: data/raw_math.json, data/raw_drama.json, data/raw_stem.json, data/raw_gym.json, data/raw_artmusic.json, data/raw_language.json. For each category, do fresh web research on current Singapore enrichment providers and update the entries. Keep the EXACT existing JSON schema for every entry — fields: n (category label), prov (provider name), regs (array from North/North-East/East/West/Central), a ([minAge,maxAge]), price (monthly SGD integer, or null if fees-on-enquiry), f (focus tags array), disp (child-disposition tags array), trial (true/false/null), rev (one honest sentence), src (source domain). Add newly-found real centres, update changed prices/info, and remove any that have clearly closed. Be conservative and accurate — never fabricate; use null when unknown. Each file must remain a valid JSON array. Do not modify, run, or create any other files, and do not run any commands."

# 1) Research pass — model can only touch files + the web (no Bash/git)
"$CLAUDE" -p "$PROMPT" --model sonnet --allowedTools Read Write Edit Glob Grep WebSearch WebFetch \
  || { echo "claude run failed — leaving data untouched"; git checkout -- data/ 2>/dev/null; exit 1; }

# 2) Validate every raw file; revert + abort if any got corrupted
for f in data/raw_*.json; do
  python3 -c "import json; json.load(open('$f'))" 2>/dev/null \
    || { echo "INVALID JSON: $f — reverting all data/ and aborting"; git checkout -- data/; exit 1; }
done

# 3) Rebuild the merged classes.json
python3 data/build.py || { echo "build.py failed — reverting"; git checkout -- data/ classes.json; exit 1; }

# 4) Deploy only if something actually changed
if git diff --quiet && git diff --cached --quiet; then
  echo "no changes — nothing to deploy"
else
  git add -A && git commit -q -m "Bloom: monthly data refresh ($(date '+%Y-%m'))" \
    && git push -q origin main && echo "deployed refreshed data"
fi
echo "===== $(date '+%Y-%m-%d %H:%M:%S') bloom refresh done ====="

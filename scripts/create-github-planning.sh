#!/usr/bin/env bash
set -euo pipefail

# Create the CoreQuote planning labels, milestones, and issues in GitHub.
#
# Requirements:
# - GitHub CLI installed: https://cli.github.com/
# - Authenticated with a token that can create labels, milestones, and issues:
#   gh auth login
#
# Run from the repository root:
#   ./scripts/create-github-planning.sh
#
# Optional GitHub Projects assignment:
#   PROJECT_NUMBER=1 ./scripts/create-github-planning.sh
#
# The script is intentionally idempotent where practical:
# - Existing labels are skipped.
# - Existing milestones are skipped.
# - Existing issues are matched by exact title and updated instead of duplicated.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISSUE_DIR="$ROOT_DIR/planning/issues"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required." >&2
  exit 1
fi

if [[ ! -d "$ISSUE_DIR" ]]; then
  echo "Issue directory not found: $ISSUE_DIR" >&2
  exit 1
fi

cd "$ROOT_DIR"

REPO="$(gh repo view --json nameWithOwner --jq '.nameWithOwner')"
OWNER="${REPO%%/*}"

label_exists() {
  local name="$1"
  gh label list --limit 1000 --json name --jq '.[].name' | grep -Fxq "$name"
}

ensure_label() {
  local name="$1"
  local color="$2"
  local description="$3"

  if label_exists "$name"; then
    echo "Label exists: $name"
    return
  fi

  echo "Creating label: $name"
  gh label create "$name" --color "$color" --description "$description"
}

milestone_number() {
  local title="$1"
  gh api "repos/$REPO/milestones?state=all&per_page=100" \
    --jq ".[] | select(.title == \"$title\") | .number" | head -n 1
}

ensure_milestone() {
  local title="$1"
  local description="$2"
  local number
  number="$(milestone_number "$title")"

  if [[ -n "$number" ]]; then
    echo "Milestone exists: $title"
    return
  fi

  echo "Creating milestone: $title"
  gh api -X POST "repos/$REPO/milestones" \
    -f title="$title" \
    -f description="$description" >/dev/null
}

get_meta() {
  local file="$1"
  local key="$2"
  awk -F': ' -v key="$key" '
    /^---[[:space:]]*$/ {
      marker += 1
      next
    }
    marker == 1 && $1 == key {
      sub(/^[^:]*: /, "")
      gsub(/^"/, "")
      gsub(/"$/, "")
      print
      exit
    }
  ' "$file"
}

write_body_without_front_matter() {
  local file="$1"
  local output="$2"
  awk '
    /^---[[:space:]]*$/ {
      marker += 1
      next
    }
    marker >= 2 {
      print
    }
  ' "$file" > "$output"
}

issue_number_by_title() {
  local title="$1"
  gh issue list --state all --limit 1000 --json number,title \
    --jq ".[] | select(.title == \"$title\") | .number" | head -n 1
}

issue_url_by_number() {
  local number="$1"
  gh issue view "$number" --json url --jq '.url'
}

project_add_issue() {
  local issue_url="$1"

  if [[ -z "${PROJECT_NUMBER:-}" ]]; then
    return
  fi

  echo "Adding issue to project $PROJECT_NUMBER: $issue_url"
  gh project item-add "$PROJECT_NUMBER" --owner "$OWNER" --url "$issue_url" >/dev/null || {
    echo "Could not add issue to project $PROJECT_NUMBER. Continuing." >&2
  }
}

ensure_issue() {
  local file="$1"
  local title milestone labels number issue_url body_file
  title="$(get_meta "$file" "title")"
  milestone="$(get_meta "$file" "milestone")"
  labels="$(get_meta "$file" "labels")"

  if [[ -z "$title" || -z "$milestone" || -z "$labels" ]]; then
    echo "Missing title, milestone, or labels metadata in $file" >&2
    exit 1
  fi

  body_file="$(mktemp)"
  write_body_without_front_matter "$file" "$body_file"

  create_label_args=()
  edit_label_args=()
  IFS=',' read -r -a label_names <<< "$labels"
  for label in "${label_names[@]}"; do
    create_label_args+=(--label "$label")
    edit_label_args+=(--add-label "$label")
  done

  number="$(issue_number_by_title "$title")"
  if [[ -n "$number" ]]; then
    echo "Updating issue #$number: $title"
    gh issue edit "$number" \
      --title "$title" \
      --body-file "$body_file" \
      --milestone "$milestone" \
      "${edit_label_args[@]}" >/dev/null
    issue_url="$(issue_url_by_number "$number")"
  else
    echo "Creating issue: $title"
    issue_url="$(gh issue create \
      --title "$title" \
      --body-file "$body_file" \
      --milestone "$milestone" \
      "${create_label_args[@]}")"
  fi

  rm -f "$body_file"
  project_add_issue "$issue_url"
}

ensure_label "phase-1-trust" "0E8A16" "Phase 1: Trustworthy Quote Flow"
ensure_label "phase-2-outputs" "1D76DB" "Phase 2: Real Quote Outputs"
ensure_label "phase-3-speed" "5319E7" "Phase 3: Job Entry Speed"
ensure_label "phase-4-library-pricing" "B60205" "Phase 4: Library and Pricing Maintenance"
ensure_label "phase-5-production" "FBCA04" "Phase 5: Production Handoff"
ensure_label "phase-6-workflow" "D93F0B" "Phase 6: Client and Business Workflow"
ensure_label "type-feature" "0052CC" "Feature or product capability"
ensure_label "type-bug" "D73A4A" "Bug or incorrect behavior"
ensure_label "type-epic" "6F42C1" "Large planning epic"
ensure_label "type-test" "0E8A16" "Real job or product test"
ensure_label "codex-ready" "2EA44F" "Ready for Codex implementation planning"
ensure_label "needs-spec" "BFDADC" "Needs more product specification"
ensure_label "needs-real-job-test" "FBCA04" "Needs validation against a realistic cabinetry job"
ensure_label "blocked" "000000" "Blocked by another decision or dependency"
ensure_label "ui" "C5DEF5" "User interface work"
ensure_label "backend" "5319E7" "Backend or API work"
ensure_label "pdf-export" "F9D0C4" "PDF or export output work"
ensure_label "data-model" "D4C5F9" "Data model or persistence work"
ensure_label "pricing" "FEF2C0" "Pricing, markups, or costs"
ensure_label "production" "BFD4F2" "Workshop or production handoff"

ensure_milestone "Phase 1 — Trustworthy Quote Flow" "Make the quote flow trustworthy before export or client use."
ensure_milestone "Phase 2 — Real Quote Outputs" "Generate professional client and workshop outputs."
ensure_milestone "Phase 3 — Job Entry Speed" "Speed up full job entry after the core flow is trusted."
ensure_milestone "Phase 4 — Library & Pricing Maintenance" "Improve library setup, imports, and price maintenance."
ensure_milestone "Phase 5 — Production Handoff" "Improve shop-floor schedules, labels, and production outputs."
ensure_milestone "Phase 6 — Client & Business Workflow" "Add client, approval, payment, user, and business workflows."

for issue_file in "$ISSUE_DIR"/*.md; do
  ensure_issue "$issue_file"
done

echo "GitHub planning setup complete for $REPO."

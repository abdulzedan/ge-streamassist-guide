#!/usr/bin/env bash
# ------------------------------------------------------------------
# deploy.sh - provision, build, deploy and operate the soak test.
#
#   ./soak/deploy.sh deploy                    # APIs, SA, bucket, image, 3 Cloud Run jobs, 3 schedulers (paused)
#   ./soak/deploy.sh start [HOURS] [PROFILE]   # write campaign.json (default 24h, standard) and resume schedulers
#   ./soak/deploy.sh stop                      # pause schedulers and close the campaign window
#   ./soak/deploy.sh status                    # campaign, scheduler states, recent executions, run count
#   ./soak/deploy.sh run fast|heavy|report     # execute one job now and wait for it
#   ./soak/deploy.sh report [LABEL]            # render the report for the campaign window, download to soak/out/<LABEL>
#   ./soak/deploy.sh destroy                   # delete schedulers + jobs (bucket and SA are kept)
#
# Reads the repo .env for PROJECT_ID / LOCATION / APP_ID / ASSISTANT_ID / API_VERSION.
# ------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "${REPO_ROOT}/.env"
: "${PROJECT_ID:?set PROJECT_ID in .env}"; : "${APP_ID:?set APP_ID in .env}"
LOCATION="${LOCATION:-global}"; ASSISTANT_ID="${ASSISTANT_ID:-default_assistant}"; API_VERSION="${API_VERSION:-v1alpha}"

REGION="${SOAK_REGION:-us-central1}"
SA_NAME="ge-soak"
SA="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
PROJECT_NUMBER="${SOAK_PROJECT_NUMBER:-$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')}"
BUCKET="${SOAK_BUCKET:-ge-soak-${PROJECT_NUMBER}}"
AR_REPO="${SOAK_AR_REPO:-cloud-run-source-deploy}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/ge-soak"
TAG="${SOAK_TAG:-$(git -C "${REPO_ROOT}" rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M)}"

# Fixtures for the capability checks (override via env before running deploy).
ADK_AGENT_ID="${SOAK_ADK_AGENT_ID:-11867618434103444869}"
A2A_AGENT_ID="${SOAK_A2A_AGENT_ID:-1030712722314703187}"
DATA_STORE_ID="${SOAK_DATA_STORE_ID:-architecture-documentation_1770737462806}"
LICENSE_LIMIT="${SOAK_LICENSE_LIMIT:-160}"
LICENSE_COUNT="${SOAK_LICENSE_COUNT:-20}"
LICENSE_EDITION="${SOAK_LICENSE_EDITION:-Standard}"

ENV_VARS="PROJECT_ID=${PROJECT_ID},LOCATION=${LOCATION},APP_ID=${APP_ID},ASSISTANT_ID=${ASSISTANT_ID},API_VERSION=${API_VERSION}"
ENV_VARS+=",SOAK_BUCKET=${BUCKET},SOAK_PROJECT_NUMBER=${PROJECT_NUMBER},SOAK_REGION=${REGION}"
ENV_VARS+=",SOAK_ADK_AGENT_ID=${ADK_AGENT_ID},SOAK_A2A_AGENT_ID=${A2A_AGENT_ID},SOAK_DATA_STORE_ID=${DATA_STORE_ID}"
ENV_VARS+=",SOAK_LICENSE_LIMIT=${LICENSE_LIMIT},SOAK_LICENSE_COUNT=${LICENSE_COUNT},SOAK_LICENSE_EDITION=${LICENSE_EDITION}"

G="gcloud --project=${PROJECT_ID} --quiet"
say() { printf '\n==> %s\n' "$*"; }

# -- building blocks -------------------------------------------------

ensure_foundation() {
  say "APIs"
  ${G} services enable run.googleapis.com cloudscheduler.googleapis.com cloudbuild.googleapis.com \
    artifactregistry.googleapis.com storage.googleapis.com discoveryengine.googleapis.com >/dev/null
  say "service account ${SA}"
  ${G} iam service-accounts describe "${SA}" >/dev/null 2>&1 || \
    ${G} iam service-accounts create "${SA_NAME}" --display-name="GE StreamAssist soak-test runner" >/dev/null
  for role in roles/discoveryengine.user roles/discoveryengine.viewer roles/run.invoker; do
    ${G} projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SA}" --role="${role}" --condition=None >/dev/null
  done
  say "bucket gs://${BUCKET}"
  ${G} storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1 || \
    ${G} storage buckets create "gs://${BUCKET}" --location="${REGION}" --uniform-bucket-level-access >/dev/null
  ${G} storage buckets add-iam-policy-binding "gs://${BUCKET}" --member="serviceAccount:${SA}" --role=roles/storage.objectAdmin >/dev/null
  say "artifact registry ${AR_REPO}"
  ${G} artifacts repositories describe "${AR_REPO}" --location="${REGION}" >/dev/null 2>&1 || \
    ${G} artifacts repositories create "${AR_REPO}" --location="${REGION}" --repository-format=docker >/dev/null
}

build_image() {
  say "building ${IMAGE}:${TAG} with Cloud Build (context = repo root, see .gcloudignore)"
  ${G} builds submit --config "${REPO_ROOT}/soak/cloudbuild.yaml" \
    --substitutions="_IMAGE=${IMAGE},_TAG=${TAG}" "${REPO_ROOT}"
}

deploy_job() {  # name  timeout  args...
  local name="$1" timeout="$2"; shift 2
  local args; args="$(IFS=,; echo "$*")"
  local verb=create
  ${G} run jobs describe "${name}" --region="${REGION}" >/dev/null 2>&1 && verb=update
  say "${verb} job ${name} (${args})"
  ${G} run jobs "${verb}" "${name}" --region="${REGION}" --image="${IMAGE}:${TAG}" \
    --service-account="${SA}" --tasks=1 --max-retries=0 --task-timeout="${timeout}" \
    --memory=512Mi --cpu=1 --args="${args}" --set-env-vars="${ENV_VARS}" >/dev/null
}

deploy_schedule() {  # name  cron  job
  local name="$1" cron="$2" job="$3"
  local uri="https://run.googleapis.com/v2/projects/${PROJECT_ID}/locations/${REGION}/jobs/${job}:run"
  local verb=create
  ${G} scheduler jobs describe "${name}" --location="${REGION}" >/dev/null 2>&1 && verb=update
  say "${verb} schedule ${name} '${cron}' -> ${job}"
  ${G} scheduler jobs "${verb}" http "${name}" --location="${REGION}" --schedule="${cron}" --time-zone="Etc/UTC" \
    --uri="${uri}" --http-method=POST --oauth-service-account-email="${SA}" \
    --description="ge-soak: triggers Cloud Run job ${job}" >/dev/null
}

schedulers() { echo ge-soak-fast ge-soak-heavy ge-soak-report; }

set_schedulers() {  # pause|resume
  for s in $(schedulers); do ${G} scheduler jobs "$1" "$s" --location="${REGION}" >/dev/null && echo "  $1 $s"; done
}

# -- commands --------------------------------------------------------

cmd_deploy() {
  ensure_foundation
  build_image
  deploy_job ge-soak-fast   900s  run --tier fast
  deploy_job ge-soak-heavy  3300s run --tier heavy
  deploy_job ge-soak-report 900s  report --label latest
  deploy_schedule ge-soak-fast   "*/5 * * * *" ge-soak-fast
  deploy_schedule ge-soak-heavy  "2 */4 * * *" ge-soak-heavy
  deploy_schedule ge-soak-report "7 * * * *"   ge-soak-report
  say "pausing schedulers until 'start'"
  set_schedulers pause
  echo; echo "Deployed ${IMAGE}:${TAG}. Next: ./soak/deploy.sh run fast   (one manual run)   then   ./soak/deploy.sh start 24"
}

cmd_start() {
  local hours="${1:-24}" profile="${2:-standard}"
  local id start end created
  id="soak-$(date -u +%Y%m%dT%H%M%SZ)"
  created="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  # start at the next 5-minute boundary so slot accounting begins clean
  start="$(python3 -c 'import datetime as d,math; n=d.datetime.now(d.timezone.utc); s=(math.floor(n.timestamp()/300)+1)*300; print(d.datetime.fromtimestamp(s,d.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))')"
  end="$(python3 -c "import datetime as d; s=d.datetime.strptime('${start}','%Y-%m-%dT%H:%M:%SZ'); print((s+d.timedelta(hours=${hours})).strftime('%Y-%m-%dT%H:%M:%SZ'))")"
  say "campaign ${id}: ${start} -> ${end} (${hours}h, profile ${profile})"
  printf '{"id":"%s","profile":"%s","start_at":"%s","end_at":"%s","hours":%s,"created_at":"%s","created_by":"%s","image":"%s"}\n' \
    "${id}" "${profile}" "${start}" "${end}" "${hours}" "${created}" "$(gcloud config get-value account 2>/dev/null)" "${IMAGE}:${TAG}" \
    | ${G} storage cp - "gs://${BUCKET}/campaign.json"
  set_schedulers resume
  echo; echo "Runs land in gs://${BUCKET}/runs/, hourly report in gs://${BUCKET}/reports/latest/report.md"
  echo "Final artifact after ${end}:  ./soak/deploy.sh report final"
}

cmd_stop() {
  set_schedulers pause
  local now; now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if ${G} storage cat "gs://${BUCKET}/campaign.json" >/tmp/ge-soak-campaign.json 2>/dev/null; then
    python3 - "${now}" <<'PY' </tmp/ge-soak-campaign.json >/tmp/ge-soak-campaign.new
import json,sys
c=json.load(sys.stdin); c["end_at"]=min(c.get("end_at",sys.argv[1]),sys.argv[1]); c["stopped_at"]=sys.argv[1]
print(json.dumps(c))
PY
    ${G} storage cp /tmp/ge-soak-campaign.new "gs://${BUCKET}/campaign.json"
    say "campaign window closed at ${now}"
  fi
}

cmd_status() {
  say "campaign"; ${G} storage cat "gs://${BUCKET}/campaign.json" 2>/dev/null || echo "(none)"
  say "schedulers"; ${G} scheduler jobs list --location="${REGION}" --filter="name~ge-soak" --format="table(name.basename(),schedule,state,lastAttemptTime)"
  say "recent fast executions"; ${G} run jobs executions list --job=ge-soak-fast --region="${REGION}" --limit=5 \
    --format="table(name.basename(),status.completionTime,status.succeededCount,status.failedCount)" 2>/dev/null || true
  say "run records"; for d in $(date -u +%Y-%m-%d) $(date -u -v-1d +%Y-%m-%d 2>/dev/null || date -u -d yesterday +%Y-%m-%d); do
    printf '  %s: %s\n' "$d" "$(${G} storage ls "gs://${BUCKET}/runs/${d}/" 2>/dev/null | wc -l | tr -d ' ')"; done
  echo; echo "latest report: gs://${BUCKET}/reports/latest/report.md"
}

cmd_run() {
  local which="${1:?usage: deploy.sh run fast|heavy|report}"
  say "executing ge-soak-${which} now"
  ${G} run jobs execute "ge-soak-${which}" --region="${REGION}" --wait
  say "log tail"
  ${G} logging read "resource.type=cloud_run_job AND resource.labels.job_name=ge-soak-${which}" \
    --limit=40 --freshness=30m --format="value(jsonPayload.message,textPayload)" | tac
}

cmd_report() {
  local label="${1:-final}"
  say "rendering report '${label}' for the campaign window"
  ${G} run jobs execute ge-soak-report --region="${REGION}" --wait --args="report,--label,${label}"
  mkdir -p "${REPO_ROOT}/soak/out/${label}"
  ${G} storage cp -r "gs://${BUCKET}/reports/${label}/*" "${REPO_ROOT}/soak/out/${label}/"
  say "artifact downloaded to soak/out/${label}/"; ls -la "${REPO_ROOT}/soak/out/${label}/"
}

cmd_destroy() {
  for s in $(schedulers); do ${G} scheduler jobs delete "$s" --location="${REGION}" 2>/dev/null && echo "deleted schedule $s" || true; done
  for j in ge-soak-fast ge-soak-heavy ge-soak-report; do ${G} run jobs delete "$j" --region="${REGION}" 2>/dev/null && echo "deleted job $j" || true; done
  echo "kept: gs://${BUCKET} (results) and ${SA}. Remove manually if no longer needed."
}

case "${1:-}" in
  deploy)  cmd_deploy ;;
  start)   cmd_start "${2:-24}" "${3:-standard}" ;;
  stop)    cmd_stop ;;
  status)  cmd_status ;;
  run)     cmd_run "${2:-}" ;;
  report)  cmd_report "${2:-final}" ;;
  destroy) cmd_destroy ;;
  *) sed -n '2,13p' "$0"; exit 1 ;;
esac

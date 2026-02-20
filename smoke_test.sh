#!/usr/bin/env bash

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/docker/docker-compose.yml}"
BASE_URL="${SMOKE_BASE_URL:-http://127.0.0.1:8080}"
LOGIN_URL="${SMOKE_LOGIN_URL:-/accounts/login/}"
CRUD_LIST_URL="${SMOKE_CRUD_LIST_URL:-/tramites/}"
STATIC_PROBE_URL="${SMOKE_STATIC_PROBE_URL:-/static/img/segey-logo.png}"
MEDIA_PROBE_URL="${SMOKE_MEDIA_PROBE_URL:-/media/smoke/smoke.txt}"
EXPECTED_SERVICES_RAW="${SMOKE_EXPECTED_SERVICES:-db redis web worker nginx}"
LOG_LINES="${SMOKE_LOG_LINES:-300}"
LOG_ERROR_PATTERN="${SMOKE_LOG_ERROR_PATTERN:-Traceback \\(most recent call last\\)|CRITICAL|Unhandled exception}"
REPORT_DIR="${SMOKE_REPORT_DIR:-${ROOT_DIR}/smoke_test_reports}"
BACKUP_DIR="${SMOKE_BACKUP_DIR:-${ROOT_DIR}/backups}"

SMOKE_USER="${SMOKE_USER:-}"
SMOKE_PASSWORD="${SMOKE_PASSWORD:-}"
SMOKE_PDF_URL="${SMOKE_PDF_URL:-}"
SMOKE_BACKUP_CMD="${SMOKE_BACKUP_CMD:-}"
SMOKE_RESTORE_CMD="${SMOKE_RESTORE_CMD:-}"
SMOKE_CRUD_CREATE_CMD="${SMOKE_CRUD_CREATE_CMD:-}"
SMOKE_CRUD_UPDATE_CMD="${SMOKE_CRUD_UPDATE_CMD:-}"
SMOKE_CRUD_DELETE_CMD="${SMOKE_CRUD_DELETE_CMD:-}"

RUN_UP=1
RUN_BUILD=1
RUN_RESTART=1
RUN_RESTORE=0
INTERACTIVE=0
STRICT=0

declare -a PASS_ITEMS
declare -a FAIL_ITEMS
declare -a WARN_ITEMS

TMP_DIR="$(mktemp -d)"
COOKIE_JAR="${TMP_DIR}/cookies.txt"
LOGIN_HTML="${TMP_DIR}/login.html"
LOGIN_HEADERS="${TMP_DIR}/login_headers.txt"
REPORT_FILE=""

cleanup() {
  rm -rf "${TMP_DIR}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

usage() {
  cat <<'EOF'
Uso:
  ./smoke_test.sh [opciones]

Opciones:
  --skip-up            No ejecuta "docker compose up".
  --skip-build         Con --skip-up ausente, usa "up -d" sin "--build".
  --skip-restart       Omite validacion de persistencia tras restart.
  --run-restore        Ejecuta prueba de restore (requiere SMOKE_RESTORE_CMD).
  --interactive        Pregunta checks manuales al final.
  --strict             Trata WARN como falla (exit code != 0).
  --compose-file PATH  Ruta al docker-compose.yml.
  --base-url URL       URL base para probes HTTP.
  --help               Muestra esta ayuda.

Variables utiles:
  SMOKE_EXPECTED_SERVICES="db redis web worker nginx"
  SMOKE_USER / SMOKE_PASSWORD
  SMOKE_PDF_URL=/ruta/o/url/pdf
  SMOKE_BACKUP_CMD="scripts/backup.sh"
  SMOKE_RESTORE_CMD="scripts/restore.sh /ruta/backup"
  SMOKE_CRUD_CREATE_CMD / SMOKE_CRUD_UPDATE_CMD / SMOKE_CRUD_DELETE_CMD
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-up)
      RUN_UP=0
      shift
      ;;
    --skip-build)
      RUN_BUILD=0
      shift
      ;;
    --skip-restart)
      RUN_RESTART=0
      shift
      ;;
    --run-restore)
      RUN_RESTORE=1
      shift
      ;;
    --interactive)
      INTERACTIVE=1
      shift
      ;;
    --strict)
      STRICT=1
      shift
      ;;
    --compose-file)
      COMPOSE_FILE="$2"
      shift 2
      ;;
    --base-url)
      BASE_URL="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Parametro no reconocido: $1"
      usage
      exit 2
      ;;
  esac
done

compose() {
  docker compose -f "${COMPOSE_FILE}" "$@"
}

contains_item() {
  local needle="$1"
  shift
  local item=""
  for item in "$@"; do
    if [[ "${item}" == "${needle}" ]]; then
      return 0
    fi
  done
  return 1
}

to_url() {
  local value="$1"
  if [[ "${value}" =~ ^https?:// ]]; then
    printf '%s\n' "${value}"
  else
    printf '%s%s\n' "${BASE_URL%/}" "${value}"
  fi
}

record_pass() {
  local msg="$1"
  PASS_ITEMS+=("${msg}")
  printf '[PASS] %s\n' "${msg}"
}

record_fail() {
  local msg="$1"
  FAIL_ITEMS+=("${msg}")
  printf '[FAIL] %s\n' "${msg}"
}

record_warn() {
  local msg="$1"
  WARN_ITEMS+=("${msg}")
  printf '[WARN] %s\n' "${msg}"
}

run_check() {
  local label="$1"
  shift
  if "$@"; then
    record_pass "${label}"
    return 0
  fi
  record_fail "${label}"
  return 1
}

print_header() {
  echo ""
  echo "============================================================"
  echo "$1"
  echo "============================================================"
}

manual_question() {
  local label="$1"
  local instruction="$2"

  if [[ "${INTERACTIVE}" -eq 0 || ! -t 0 ]]; then
    record_warn "${label} (manual pendiente): ${instruction}"
    return
  fi

  local answer=""
  printf "[MANUAL] %s\n" "${instruction}"
  read -r -p "Resultado para '${label}' [p=pass/f=fail/w=warn]: " answer
  case "${answer}" in
    p|P) record_pass "${label} (validado manualmente)" ;;
    f|F) record_fail "${label} (fallo manual)" ;;
    *) record_warn "${label} (manual pendiente/no concluyente)" ;;
  esac
}

mkdir -p "${REPORT_DIR}" >/dev/null 2>&1 || true
REPORT_FILE="${REPORT_DIR}/smoke_test_$(date +%Y%m%d_%H%M%S).md"

print_header "Smoke Test Semiautomatico - Migracion Docker"
echo "Compose file: ${COMPOSE_FILE}"
echo "Base URL: ${BASE_URL}"
echo "Reporte: ${REPORT_FILE}"

print_header "A) Infraestructura"

if ! command -v docker >/dev/null 2>&1; then
  record_fail "Docker no esta instalado o disponible en PATH"
fi

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  record_fail "No existe compose file: ${COMPOSE_FILE}"
else
  record_pass "Compose file encontrado"
fi

if [[ "${RUN_UP}" -eq 1 && -f "${COMPOSE_FILE}" ]] && command -v docker >/dev/null 2>&1; then
  if [[ "${RUN_BUILD}" -eq 1 ]]; then
    if compose up -d --build; then
      record_pass "docker compose up -d --build sin errores"
    else
      record_fail "docker compose up -d --build fallo"
    fi
  else
    if compose up -d; then
      record_pass "docker compose up -d sin errores"
    else
      record_fail "docker compose up -d fallo"
    fi
  fi
else
  record_warn "Se omitio 'docker compose up' (--skip-up)"
fi

declare -a running_services=()
declare -a configured_services=()

if command -v docker >/dev/null 2>&1 && [[ -f "${COMPOSE_FILE}" ]]; then
  while IFS= read -r line; do
    [[ -n "${line}" ]] && running_services+=("${line}")
  done < <(compose ps --services --status running 2>/dev/null || true)

  while IFS= read -r line; do
    [[ -n "${line}" ]] && configured_services+=("${line}")
  done < <(compose config --services 2>/dev/null || true)
fi

if [[ ${#configured_services[@]} -gt 0 ]]; then
  echo "Servicios en compose: ${configured_services[*]}"
else
  echo "Servicios en compose: (ninguno)"
fi

if [[ ${#running_services[@]} -gt 0 ]]; then
  echo "Servicios running: ${running_services[*]}"
else
  echo "Servicios running: (ninguno)"
fi

IFS=' ' read -r -a expected_services <<< "${EXPECTED_SERVICES_RAW}"
for svc in "${expected_services[@]}"; do
  if contains_item "${svc}" "${running_services[@]-}"; then
    record_pass "Servicio esperado arriba: ${svc}"
  else
    record_fail "Servicio esperado ausente/no running: ${svc}"
  fi
done

if compose ps >/dev/null 2>&1; then
  record_pass "docker compose ps responde correctamente"
else
  record_fail "docker compose ps fallo"
fi

print_header "B) Aplicacion"

if contains_item "web" "${running_services[@]-}"; then
  if compose exec -T web python manage.py migrate --check --noinput; then
    record_pass "Migraciones aplicadas sin pendientes"
  else
    record_fail "Hay migraciones pendientes o error ejecutando migrate --check"
  fi
else
  record_fail "No se puede validar migraciones: servicio web no esta running"
fi

login_full_url="$(to_url "${LOGIN_URL}")"
login_code="$(curl -sS -o "${LOGIN_HTML}" -w '%{http_code}' -c "${COOKIE_JAR}" "${login_full_url}" || true)"
if [[ "${login_code}" =~ ^2|^3 ]]; then
  record_pass "Pagina de login accesible (${login_code})"
else
  record_fail "Pagina de login no accesible (${login_code})"
fi

AUTH_READY=0
if [[ -n "${SMOKE_USER}" && -n "${SMOKE_PASSWORD}" ]]; then
  csrf_token="$(grep -o 'name="csrfmiddlewaretoken" value="[^"]*"' "${LOGIN_HTML}" | head -n1 | sed 's/.*value="//; s/"$//')"
  if [[ -z "${csrf_token}" ]]; then
    record_fail "No se pudo extraer CSRF token para login automatico"
  else
    login_post_code="$(
      curl -sS \
        -b "${COOKIE_JAR}" \
        -c "${COOKIE_JAR}" \
        -e "${login_full_url}" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        --data-urlencode "csrfmiddlewaretoken=${csrf_token}" \
        --data-urlencode "username=${SMOKE_USER}" \
        --data-urlencode "password=${SMOKE_PASSWORD}" \
        --data-urlencode "next=/" \
        -D "${LOGIN_HEADERS}" \
        -o /dev/null \
        -w '%{http_code}' \
        "${login_full_url}" || true
    )"
    if grep -qi "sessionid" "${COOKIE_JAR}" && [[ "${login_post_code}" =~ ^2|^3 ]]; then
      record_pass "Login automatico con credenciales de smoke test"
      AUTH_READY=1
    else
      record_fail "Login automatico fallo (codigo=${login_post_code})"
    fi
  fi
else
  record_warn "Login con credenciales no ejecutado (define SMOKE_USER y SMOKE_PASSWORD)"
fi

crud_list_url="$(to_url "${CRUD_LIST_URL}")"
if [[ "${AUTH_READY}" -eq 1 ]]; then
  crud_code="$(curl -sS -b "${COOKIE_JAR}" -o /dev/null -w '%{http_code}' "${crud_list_url}" || true)"
  if [[ "${crud_code}" == "200" ]]; then
    record_pass "Listado CRUD principal accesible autenticado (${CRUD_LIST_URL})"
  else
    record_fail "Listado CRUD principal no accesible autenticado (${crud_code})"
  fi
else
  record_warn "Validacion automatica de CRUD lista omitida por falta de login autenticado"
fi

if [[ -n "${SMOKE_CRUD_CREATE_CMD}" && -n "${SMOKE_CRUD_UPDATE_CMD}" && -n "${SMOKE_CRUD_DELETE_CMD}" ]]; then
  if bash -lc "${SMOKE_CRUD_CREATE_CMD}" && bash -lc "${SMOKE_CRUD_UPDATE_CMD}" && bash -lc "${SMOKE_CRUD_DELETE_CMD}"; then
    record_pass "CRUD completo (create/update/delete) via comandos personalizados"
  else
    record_fail "CRUD completo via comandos personalizados fallo"
  fi
else
  manual_question \
    "CRUD completo (crear/listar/editar/eliminar)" \
    "Ejecuta manualmente CRUD de 1 registro y confirma en UI."
fi

print_header "C) Media y PDF"

SMOKE_MARKER="smoke-$(date +%s)-${RANDOM}"
if contains_item "web" "${running_services[@]-}"; then
  if compose exec -T web sh -lc "mkdir -p media/smoke && printf '%s\n' '${SMOKE_MARKER}' > media/smoke/smoke.txt"; then
    media_url="$(to_url "${MEDIA_PROBE_URL}")"
    media_code="$(curl -sS -o "${TMP_DIR}/media_probe.txt" -w '%{http_code}' "${media_url}" || true)"
    if [[ "${media_code}" == "200" ]] && grep -q "${SMOKE_MARKER}" "${TMP_DIR}/media_probe.txt"; then
      record_pass "Probe media accesible y contenido valido (${MEDIA_PROBE_URL})"
    else
      record_fail "Probe media no accesible/incorrecto (codigo=${media_code})"
    fi
  else
    record_fail "No se pudo crear media probe en contenedor web"
  fi
else
  record_fail "No se puede validar media: servicio web no esta running"
fi

if [[ -n "${SMOKE_PDF_URL}" ]]; then
  pdf_url="$(to_url "${SMOKE_PDF_URL}")"
  pdf_code="$(curl -sS -b "${COOKIE_JAR}" -D "${TMP_DIR}/pdf_headers.txt" -o "${TMP_DIR}/probe.pdf" -w '%{http_code}' "${pdf_url}" || true)"
  pdf_header="$(tr -d '\r' < "${TMP_DIR}/pdf_headers.txt" | grep -i '^Content-Type:' | tail -n1 | awk '{print tolower($2)}')"
  pdf_magic="$(head -c 4 "${TMP_DIR}/probe.pdf" 2>/dev/null || true)"
  if [[ "${pdf_code}" == "200" ]] && ([[ "${pdf_header}" == *"application/pdf"* ]] || [[ "${pdf_magic}" == "%PDF" ]]); then
    record_pass "Generacion/descarga de PDF valida (${SMOKE_PDF_URL})"
  else
    record_fail "Validacion PDF fallo (codigo=${pdf_code}, content-type=${pdf_header:-n/a})"
  fi
else
  manual_question \
    "Generacion de PDF" \
    "Genera un reporte PDF y valida descarga/apertura; o define SMOKE_PDF_URL."
fi

print_header "D) Worker / Jobs"

if contains_item "web" "${running_services[@]-}"; then
  job_id="$(
    compose exec -T web python manage.py shell -c "
from tramites.services import jobs
j = jobs.enqueue_job(job_type='healthcheck', payload={'source': 'smoke_test'})
print(j.pk)
" 2>/dev/null | tr -d '\r' | tail -n1
  )"

  if [[ "${job_id}" =~ ^[0-9]+$ ]]; then
    if compose exec -T web python manage.py run_async_jobs --limit 5 --worker-name smoke-test >/dev/null; then
      if compose exec -T web python manage.py shell -c "
from tramites.models import AsyncJob
import sys
j = AsyncJob.objects.filter(pk=${job_id}).first()
ok = bool(j and j.estado == 'exitoso')
print(j.estado if j else 'missing')
sys.exit(0 if ok else 1)
" >/dev/null; then
        record_pass "Worker/logica de jobs proceso 1 job healthcheck (job_id=${job_id})"
      else
        record_fail "Job healthcheck no quedo en estado exitoso (job_id=${job_id})"
      fi
    else
      record_fail "Ejecucion run_async_jobs fallo"
    fi
  else
    record_fail "No se pudo encolar job de smoke test"
  fi
else
  record_fail "No se puede validar jobs: servicio web no esta running"
fi

print_header "E) Persistencia"

PERSIST_JOB_ID=""
PERSIST_TOKEN="persist-$(date +%s)-${RANDOM}"
if contains_item "web" "${running_services[@]-}"; then
  PERSIST_JOB_ID="$(
    compose exec -T web python manage.py shell -c "
from tramites.services import jobs
j = jobs.enqueue_job(job_type='healthcheck', payload={'persist_probe': '${PERSIST_TOKEN}'})
print(j.pk)
" 2>/dev/null | tr -d '\r' | tail -n1
  )"
fi

if [[ "${RUN_RESTART}" -eq 1 ]]; then
  if compose restart >/dev/null; then
    record_pass "docker compose restart ejecutado"
  else
    record_fail "docker compose restart fallo"
  fi

  sleep 6

  media_after_code="$(curl -sS -o "${TMP_DIR}/media_after_restart.txt" -w '%{http_code}' "$(to_url "${MEDIA_PROBE_URL}")" || true)"
  if [[ "${media_after_code}" == "200" ]] && grep -q "${SMOKE_MARKER}" "${TMP_DIR}/media_after_restart.txt"; then
    record_pass "Persistencia media validada tras restart"
  else
    record_fail "Persistencia media fallo tras restart"
  fi

  if [[ "${PERSIST_JOB_ID}" =~ ^[0-9]+$ ]]; then
    if compose exec -T web python manage.py shell -c "
from tramites.models import AsyncJob
import sys
ok = AsyncJob.objects.filter(pk=${PERSIST_JOB_ID}, payload__persist_probe='${PERSIST_TOKEN}').exists()
sys.exit(0 if ok else 1)
" >/dev/null; then
      record_pass "Persistencia DB validada tras restart (job_id=${PERSIST_JOB_ID})"
    else
      record_fail "Persistencia DB fallo tras restart"
    fi
  else
    record_warn "No se pudo preparar probe de persistencia DB"
  fi
else
  record_warn "Se omitio validacion de persistencia por restart (--skip-restart)"
fi

print_header "F) Backup / Restore"

if [[ -n "${SMOKE_BACKUP_CMD}" ]]; then
  mkdir -p "${BACKUP_DIR}" >/dev/null 2>&1 || true
  before_count="$(find "${BACKUP_DIR}" -maxdepth 1 -type f 2>/dev/null | wc -l | tr -d ' ')"
  if bash -lc "${SMOKE_BACKUP_CMD}"; then
    after_count="$(find "${BACKUP_DIR}" -maxdepth 1 -type f 2>/dev/null | wc -l | tr -d ' ')"
    if [[ "${after_count}" -gt "${before_count}" ]]; then
      record_pass "Backup generado en ${BACKUP_DIR}"
    else
      record_fail "Comando backup corrio pero no genero nuevos archivos en ${BACKUP_DIR}"
    fi
  else
    record_fail "Comando backup fallo: ${SMOKE_BACKUP_CMD}"
  fi
else
  manual_question \
    "Backup (DB + media)" \
    "Define SMOKE_BACKUP_CMD para validacion automatica o ejecuta backup manual."
fi

if [[ "${RUN_RESTORE}" -eq 1 ]]; then
  if [[ -n "${SMOKE_RESTORE_CMD}" ]]; then
    if bash -lc "${SMOKE_RESTORE_CMD}"; then
      record_pass "Restore ejecutado sin error de comando"
    else
      record_fail "Restore fallo: ${SMOKE_RESTORE_CMD}"
    fi
  else
    record_fail "Se solicito --run-restore pero SMOKE_RESTORE_CMD esta vacio"
  fi
else
  manual_question \
    "Restore en entorno de prueba" \
    "Ejecuta restore en ambiente de prueba o usa --run-restore con SMOKE_RESTORE_CMD."
fi

print_header "G) Logs"

if compose logs --no-color --tail "${LOG_LINES}" > "${TMP_DIR}/compose_logs.txt" 2>/dev/null; then
  if command -v rg >/dev/null 2>&1; then
    if rg -n "${LOG_ERROR_PATTERN}" "${TMP_DIR}/compose_logs.txt" >/dev/null; then
      record_fail "Logs contienen patrones criticos (${LOG_ERROR_PATTERN})"
    else
      record_pass "Sin patrones criticos en ultimas ${LOG_LINES} lineas de logs"
    fi
  else
    if grep -En "${LOG_ERROR_PATTERN}" "${TMP_DIR}/compose_logs.txt" >/dev/null; then
      record_fail "Logs contienen patrones criticos (${LOG_ERROR_PATTERN})"
    else
      record_pass "Sin patrones criticos en ultimas ${LOG_LINES} lineas de logs"
    fi
  fi
else
  record_warn "No se pudieron recolectar logs de compose"
fi

print_header "H) Static / Media via HTTP"

static_code="$(curl -sS -o /dev/null -w '%{http_code}' "$(to_url "${STATIC_PROBE_URL}")" || true)"
if [[ "${static_code}" == "200" ]]; then
  record_pass "Static servido correctamente (${STATIC_PROBE_URL})"
else
  record_fail "Static no accesible (${STATIC_PROBE_URL}) codigo=${static_code}"
fi

media_final_code="$(curl -sS -o /dev/null -w '%{http_code}' "$(to_url "${MEDIA_PROBE_URL}")" || true)"
if [[ "${media_final_code}" == "200" ]]; then
  record_pass "Media servido correctamente (${MEDIA_PROBE_URL})"
else
  record_fail "Media no accesible (${MEDIA_PROBE_URL}) codigo=${media_final_code}"
fi

{
  echo "# Reporte Smoke Test"
  echo ""
  echo "- Fecha: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "- Compose file: ${COMPOSE_FILE}"
  echo "- Base URL: ${BASE_URL}"
  echo "- Servicios esperados: ${EXPECTED_SERVICES_RAW}"
  echo ""
  echo "## Resumen"
  echo ""
  echo "- PASS: ${#PASS_ITEMS[@]}"
  echo "- FAIL: ${#FAIL_ITEMS[@]}"
  echo "- WARN: ${#WARN_ITEMS[@]}"
  echo ""
  echo "## PASS"
  for item in "${PASS_ITEMS[@]}"; do
    echo "- ${item}"
  done
  echo ""
  echo "## FAIL"
  if [[ ${#FAIL_ITEMS[@]} -eq 0 ]]; then
    echo "- Ninguno"
  else
    for item in "${FAIL_ITEMS[@]}"; do
      echo "- ${item}"
    done
  fi
  echo ""
  echo "## WARN"
  if [[ ${#WARN_ITEMS[@]} -eq 0 ]]; then
    echo "- Ninguno"
  else
    for item in "${WARN_ITEMS[@]}"; do
      echo "- ${item}"
    done
  fi
} > "${REPORT_FILE}"

print_header "Resumen Final"
echo "PASS: ${#PASS_ITEMS[@]}"
echo "FAIL: ${#FAIL_ITEMS[@]}"
echo "WARN: ${#WARN_ITEMS[@]}"
echo "Reporte: ${REPORT_FILE}"

if [[ ${#FAIL_ITEMS[@]} -gt 0 ]]; then
  exit 1
fi

if [[ "${STRICT}" -eq 1 && ${#WARN_ITEMS[@]} -gt 0 ]]; then
  exit 2
fi

exit 0

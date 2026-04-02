#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="/Applications/Docker.app/Contents/Resources/bin:${PATH}"

case "${1:-}" in
  up)
    cd "${ROOT_DIR}"
    docker compose up -d
    ;;
  down)
    cd "${ROOT_DIR}"
    docker compose down
    ;;
  init-db)
    docker exec odoo19-web odoo --db_host=db --db_user=odoo --db_password=odoo db init AI_Employee_Business --country US --language en_US --username admin --password admin
    ;;
  install-account)
    docker exec odoo19-web odoo --db_host=db --db_user=odoo --db_password=odoo module install account --database AI_Employee_Business
    ;;
  logs)
    cd "${ROOT_DIR}"
    docker compose logs -f web
    ;;
  *)
    echo "Usage: $0 {up|down|init-db|install-account|logs}"
    exit 1
    ;;
esac

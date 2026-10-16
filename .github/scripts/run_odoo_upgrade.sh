#!/usr/bin/env bash
# Install modules from an older checkout of the repository, upgrade them to this one, and fail on an ERROR,
# CRITICAL or WARNING line of the upgrade. The database is dropped at the end.
#
#   run_odoo_upgrade.sh <database> <older checkout> <modules to install>
#
# Environment as run_odoo_tests.sh: ODOO_PATH, PYTHON, PGHOST, PGPORT, PGUSER, PGPASSWORD, LOG_DIR.
set -uo pipefail

db=${1:?database}
old=$(cd "${2:?older checkout}" && pwd)
modules=${3:?modules to install}
repo=$(cd "$(dirname "$0")/../.." && pwd)
odoo=${ODOO_PATH:-$repo/../odoo}
python=${PYTHON:-python3}
log_dir=${LOG_DIR:-$(mktemp -d)}
mkdir -p "$log_dir"

conf() {
    local file
    file=$(mktemp)
    cat > "$file" <<CONF
[options]
addons_path = $odoo/addons,$odoo/odoo/addons,$1
db_host = ${PGHOST:-localhost}
db_port = ${PGPORT:-5432}
db_user = ${PGUSER:-odoo}
db_password = ${PGPASSWORD:-odoo}
data_dir = $data_dir
CONF
    echo "$file"
}

data_dir=$(mktemp -d)
old_conf=$(conf "$old")
new_conf=$(conf "$repo")
drop() { dropdb --if-exists "$db" >/dev/null 2>&1; rm -f "$old_conf" "$new_conf"; }
trap drop EXIT
dropdb --if-exists "$db" >/dev/null 2>&1
# as Odoo creates its databases: its parent paths are compared with the C sort order
createdb --encoding=UTF8 --lc-collate=C --template=template0 "$db" || exit 1

echo "Installing $modules from $(git -C "$old" log -1 --format='%h %s' 2>/dev/null || echo "$old")"
"$python" "$odoo/odoo-bin" -c "$old_conf" -d "$db" -i "$modules" --with-demo --stop-after-init \
    --http-port "${HTTP_PORT:-8069}" > "$log_dir/$db-install.log" 2>&1 || { echo "FAILED: the older install"; exit 1; }

echo "Upgrading to $(git -C "$repo" log -1 --format='%h %s' 2>/dev/null || echo "$repo")"
"$python" "$odoo/odoo-bin" -c "$new_conf" -d "$db" -u all --stop-after-init --http-port "${HTTP_PORT:-8069}" \
    > "$log_dir/$db-upgrade.log" 2>&1
status=$?
problems=$(grep -E ' (WARNING|ERROR|CRITICAL) ' "$log_dir/$db-upgrade.log")
if [ -n "$problems" ]; then
    echo "Log problems:"
    echo "$problems" | cut -c1-400
fi
if [ $status -ne 0 ] || [ -n "$problems" ]; then
    echo "FAILED: see $log_dir/$db-upgrade.log"
    exit 1
fi
echo "Passed"

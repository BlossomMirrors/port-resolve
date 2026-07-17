#!/bin/bash
#export BMD_RESOLVE_LUT_DIR=
#export BMD_RESOLVE_SUPPORT_DIR
export BMD_RESOLVE_CONFIG_DIR="${XDG_CONFIG_HOME}"
export BMD_RESOLVE_LICENSE_DIR="${XDG_DATA_HOME}/license"
export BMD_RESOLVE_LOGS_DIR="${XDG_DATA_HOME}/logs"
export QT_LOGGING_RULES="*.debug=true"
export QT_DEBUG_PLUGINS=1

mkdir -p "${BMD_RESOLVE_LOGS_DIR}"
LOG="${BMD_RESOLVE_LOGS_DIR}/resolve-$(date +%Y%m%d-%H%M%S).log"
cd "${BMD_RESOLVE_LOGS_DIR}"

# "Arc Compat": surfaces a notification when Resolve logs an unsupported-codec
# error, since those otherwise fail completely silently. Tied to this
# process's lifetime.
/app/bin/arc-compat-watcher &
ARC_COMPAT_PID=$!
trap 'kill "${ARC_COMPAT_PID}" 2>/dev/null' EXIT

/app/bin/resolve "$@" 2>&1 | tee "$LOG"

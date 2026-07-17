#!/bin/bash
####
# "Arc Compat" runs inside the Flatpak sandbox alongside DaVinci Resolve.
# Tails Resolve's own debug log and surfaces a desktop notification (via the
# Flatpak Notification portal, so it works on any desktop environment, not
# just one) the moment Resolve logs an unsupported-codec error. These
# otherwise fail completely silently: the clip just vanishes from the
# timeline, with no preview and no playback, and no indication why. The
# notification's "Open Docs" button opens the BlossomOS help page for this.
#
# Launched automatically by resolve.sh; install path: /app/bin/arc-compat-watcher
####
LOG="${BMD_RESOLVE_LOGS_DIR:-${XDG_DATA_HOME}/logs}/ResolveDebug.txt"
DOC="https://help.blossomos.org/help/user/resolve"
CONVERT="/app/bin/convert-for-resolve"

if [ ! -e "$LOG" ]; then
    while [ ! -e "$LOG" ]; do sleep 1; done
fi

# Escape a string for embedding in a GVariant double-quoted string literal
# (filenames can contain ", \, etc.).
gv_escape() {
    sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' <<< "$1"
}

notify_seq=0

notify() {
    local title body id
    title="$(gv_escape "$1")"
    body="$(gv_escape "$2")"
    notify_seq=$((notify_seq + 1))
    id="arc-compat-${notify_seq}"
    gdbus call --session --dest org.freedesktop.portal.Desktop \
        --object-path /org/freedesktop/portal/desktop \
        --method org.freedesktop.portal.Notification.AddNotification \
        "$id" \
        "{\"title\": <\"${title}\">, \"body\": <\"${body}\">, \"buttons\": <[{\"label\": <\"Open Docs\">, \"action\": <\"open-docs\">}]>}" \
        > /dev/null 2>&1
}

# Listen for the "Open Docs" button across every notification this script sends.
gdbus monitor --session --dest org.freedesktop.portal.Desktop \
    --object-path /org/freedesktop/portal/desktop 2>/dev/null |
while IFS= read -r line; do
    [[ "$line" == *"ActionInvoked"* && "$line" == *"open-docs"* ]] || continue
    xdg-open "$DOC" > /dev/null 2>&1 &
done &

last_video=""
last_audio=""

tail -n0 -F "$LOG" 2>/dev/null | while IFS= read -r line; do
    if [[ "$line" =~ Codec\ \(([a-zA-Z0-9_]+)\)\ not\ Found\ in\ Repository ]]; then
        codec="${BASH_REMATCH[1]}"
        [ "$codec" = "$last_video" ] && continue
        last_video="$codec"
        notify "DaVinci Resolve: unsupported video codec" \
            "Codec '${codec}' can't be decoded by this version. Fix: ${CONVERT}"
    elif [[ "$line" == *"Failed to decode the audio samples"* ]]; then
        clip=$(grep -oP '(?<=Failed to decode clip <)[^>]+' <<< "$line")
        [ "$clip" = "$last_audio" ] && continue
        last_audio="$clip"
        notify "DaVinci Resolve: unsupported audio codec" \
            "Can't decode audio in '${clip##*/}'. Fix: ${CONVERT}"
    fi
done

#!/bin/bash
####
# Build, export and install the free x264/x265/ProRes + VAAPI encode IOPlugins
# (manifests in ioplugins/) as Flatpak extensions of the given Resolve app.
#
# Usage: ./build_ioplugins.sh [com.blackmagic.Resolve|com.blackmagic.ResolveStudio]
####
set -e

APP_ID="${1:-com.blackmagic.Resolve}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT}/.ioplugin-build-dir"
REPO="${ROOT}/.ioplugin-repo"

shopt -s nullglob
manifests=("${ROOT}/ioplugins/${APP_ID}.ioplugin."*.yaml)
if [ ${#manifests[@]} -eq 0 ]; then
    echo "No IOPlugin manifests found for ${APP_ID}" >&2
    exit 1
fi

refs=()
for manifest in "${manifests[@]}"; do
    echo "==> Building $(basename "$manifest")"
    rm -rf "$BUILD_DIR"
    flatpak-builder --install-deps-from=flathub --disable-rofiles-fuse --force-clean \
        "$BUILD_DIR" "$manifest"
    sed -Ei 's/name=(.+)_dvcp_bundle/name=\1.dvcp.bundle/g' "$BUILD_DIR/metadata"
    flatpak build-export --arch=x86_64 --update-appstream \
        --exclude='/lib/debug/*' --include=/lib/debug/app \
        --exclude='/share/runtime/locale/*/*' \
        "$REPO" "$BUILD_DIR" 1.0
    refs+=("$(grep -m1 '^name=' "$BUILD_DIR/metadata" | cut -d= -f2-)")
done
rm -rf "$BUILD_DIR"

flatpak remote-add --user --no-gpg-verify --if-not-exists resolve-ioplugin-repo "$REPO"
flatpak install --user -y --or-update resolve-ioplugin-repo "${refs[@]}"

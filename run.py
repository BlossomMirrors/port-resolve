#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.pop("LD_LIBRARY_PATH", None)  # Zed flatpak leaks its libs into the shell

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT / "python"))

STUDIO = "--studio" in sys.argv
MANIFEST = ROOT / (
    "com.blackmagic.ResolveStudio.yaml" if STUDIO else "com.blackmagic.Resolve.yaml"
)
APP_ID = "com.blackmagic.ResolveStudio" if STUDIO else "com.blackmagic.Resolve"
REPO = ROOT / ".repo"
BUILD_DIR = ROOT / "build-dir"


def run(*args):
    subprocess.run(args, check=True)


def ensure_requests():
    try:
        import requests  # noqa: F401

        return
    except ImportError:
        pass
    venv = ROOT / ".dlenv"
    if not venv.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        subprocess.run(
            [str(venv / "bin" / "pip"), "install", "-q", "requests"], check=True
        )
    python = str(venv / "bin" / "python3")
    os.execv(python, [python] + sys.argv)


run(
    "flatpak",
    "remote-add",
    "--user",
    "--if-not-exists",
    "flathub",
    "https://dl.flathub.org/repo/flathub.flatpakrepo",
)

result = subprocess.run(["flatpak", "list", "--user"], capture_output=True, text=True)
if "org.flatpak.Builder" not in result.stdout:
    run("flatpak", "install", "--user", "-y", "flathub", "org.flatpak.Builder")

if not (ROOT / "shared-modules" / "glu" / "glu-9.json").exists():
    run("git", "submodule", "update", "--init", "--recursive")

if not (ROOT / "resolve.zip").exists():
    ensure_requests()
    from resolve_download import (  # type: ignore
        download_using_id,
        get_latest_version_information,
    )

    app_tag = "davinci-resolve-studio" if STUDIO else "davinci-resolve"
    print(f"Downloading {app_tag}...")
    os.chdir(ROOT)
    _, _, download_id = get_latest_version_information(
        app_tag=app_tag,
        refer_id="77ef91f67a9e411bbbe299e595b4cfcc",
        stable=True,
    )
    download_using_id(download_id)

if BUILD_DIR.exists():
    shutil.rmtree(BUILD_DIR)

run(
    "flatpak",
    "run",
    "--user",
    "org.flatpak.Builder",
    "--install-deps-from=flathub",
    f"--repo={REPO}",
    str(BUILD_DIR),
    str(MANIFEST),
)

result = subprocess.run(
    ["flatpak", "remote-list", "--user"], capture_output=True, text=True
)
if "resolve-repo" in result.stdout:
    run("flatpak", "remote-modify", "--user", f"--url=file://{REPO}", "resolve-repo")
else:
    run("flatpak", "remote-add", "--user", "--no-gpg-verify", "resolve-repo", str(REPO))
run("flatpak", "install", "--user", "-y", "--or-update", "resolve-repo", APP_ID)

run(
    "flatpak",
    "run",
    "--user",
    "--env=RUSTICL_ENABLE=radeonsi",
    "--env=QT_LOGGING_RULES=*.debug=true",
    "--env=QT_DEBUG_PLUGINS=1",
    APP_ID,
)

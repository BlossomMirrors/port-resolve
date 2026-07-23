#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT / "python"))
os.chdir(ROOT)

REPO = "/srv/repos/flatpak"
REFER_ID = "77ef91f67a9e411bbbe299e595b4cfcc"


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


def gpg_key_id():
    out = subprocess.run(
        ["gpg", "--list-secret-keys", "--keyid-format", "LONG"],
        check=True, capture_output=True, text=True,
    ).stdout
    for line in out.splitlines():
        if line.strip().startswith("sec"):
            return line.split()[1].split("/")[1]
    raise RuntimeError("No secret GPG key found")


def ensure_zip(studio: bool):
    cached = ROOT / ("resolve-studio.zip" if studio else "resolve-free.zip")
    if not cached.exists():
        ensure_requests()
        from resolve_download import download_using_id, get_latest_version_information

        app_tag = "davinci-resolve-studio" if studio else "davinci-resolve"
        print(f"Downloading {app_tag}...")
        _, _, download_id = get_latest_version_information(
            app_tag=app_tag, refer_id=REFER_ID, stable=True,
        )
        target = ROOT / "resolve.zip"
        target.unlink(missing_ok=True)
        download_using_id(download_id)
        target.rename(cached)

    shutil.copyfile(cached, ROOT / "resolve.zip")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--studio", action="store_true")
    group.add_argument("--free", action="store_true")
    studio = parser.parse_args().studio

    if not (ROOT / "shared-modules" / "glu" / "glu-9.json").exists():
        run("git", "submodule", "update", "--init", "--recursive")

    ensure_zip(studio)

    manifest = ROOT / (
        "com.blackmagic.ResolveStudio.yaml" if studio else "com.blackmagic.Resolve.yaml"
    )
    run(
        "flatpak-builder",
        "--install-deps-from=flathub",
        "--force-clean",
        f"--gpg-sign={gpg_key_id()}",
        f"--repo={REPO}",
        "build-dir",
        str(manifest),
    )


if __name__ == "__main__":
    main()

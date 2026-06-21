import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/rlatjd1f/household/releases/latest"


@dataclass
class UpdateInfo:
    version: str
    tag_name: str
    asset_name: str
    download_url: str
    release_url: str


def normalize_version(version):
    version = version.strip().lstrip("v")
    parts = []
    for part in version.split("."):
        number = ""
        for char in part:
            if char.isdigit():
                number += char
            else:
                break
        parts.append(int(number or 0))
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer_version(latest_version, current_version):
    return normalize_version(latest_version) > normalize_version(current_version)


def get_platform_asset_name():
    if sys.platform == "win32":
        return "HouseholdManager-Windows.exe"
    if sys.platform == "darwin":
        return "HouseholdManager-macOS.zip"
    return None


def request_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "HouseholdManager-Updater",
        },
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def check_for_update(current_version):
    asset_name = get_platform_asset_name()
    if not asset_name:
        return None

    release = request_json(GITHUB_LATEST_RELEASE_URL)
    tag_name = release.get("tag_name", "")
    latest_version = tag_name.lstrip("v")
    if not latest_version or not is_newer_version(latest_version, current_version):
        return None

    for asset in release.get("assets", []):
        if asset.get("name") == asset_name:
            return UpdateInfo(
                version=latest_version,
                tag_name=tag_name,
                asset_name=asset_name,
                download_url=asset["browser_download_url"],
                release_url=release.get("html_url", ""),
            )
    return None


def download_asset(update_info, progress_callback=None):
    target_dir = Path(tempfile.mkdtemp(prefix="household-update-"))
    target_path = target_dir / update_info.asset_name
    request = urllib.request.Request(
        update_info.download_url,
        headers={"User-Agent": "HouseholdManager-Updater"},
    )
    if progress_callback:
        progress_callback("업데이트 파일을 다운로드하고 있습니다.", 0)
    with urllib.request.urlopen(request, timeout=60) as response:
        total_size = int(response.headers.get("Content-Length") or 0)
        downloaded_size = 0
        with target_path.open("wb") as output:
            while True:
                chunk = response.read(1024 * 512)
                if not chunk:
                    break
                output.write(chunk)
                downloaded_size += len(chunk)
                if progress_callback and total_size:
                    downloaded_mb = downloaded_size // 1024 // 1024
                    total_mb = total_size // 1024 // 1024
                    progress_callback(
                        f"???? ??? ?????? ????. ({downloaded_mb}MB / {total_mb}MB)",
                        min(99, int(downloaded_size * 100 / total_size)),
                    )
    if progress_callback:
        progress_callback("다운로드가 완료되었습니다. 업데이트를 준비하고 있습니다.", 100)
    return target_path


def install_update(update_info, progress_callback=None):
    if not getattr(sys, "frozen", False):
        raise RuntimeError("자동 업데이트는 배포된 실행 파일에서만 사용할 수 있습니다.")

    downloaded_path = download_asset(update_info, progress_callback)
    if sys.platform == "win32":
        if progress_callback:
            progress_callback("프로그램을 교체하기 위한 업데이트 스크립트를 준비하고 있습니다.", 100)
        launch_windows_updater(downloaded_path)
        return
    if sys.platform == "darwin":
        if progress_callback:
            progress_callback("업데이트 패키지를 압축 해제하고 있습니다.", 100)
        launch_macos_updater(downloaded_path)
        return
    raise RuntimeError("지원하지 않는 운영체제입니다.")


def launch_windows_updater(downloaded_path):
    current_exe = Path(sys.executable).resolve()
    script_path = downloaded_path.with_suffix(".bat")
    script_path.write_text(
        "\n".join(
            [
                "@echo off",
                "chcp 65001 >nul",
                ":wait_app_exit",
                f'copy /Y "{downloaded_path}" "{current_exe}"',
                "if errorlevel 1 (",
                "  timeout /t 1 /nobreak >nul",
                "  goto wait_app_exit",
                ")",
                f'start "" "{current_exe}"',
                f'del "{downloaded_path}"',
                'del "%~f0"',
            ]
        ),
        encoding="utf-8",
    )
    subprocess.Popen(
        ["cmd", "/c", str(script_path)],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    )


def get_current_app_bundle():
    executable = Path(sys.executable).resolve()
    for parent in [executable, *executable.parents]:
        if parent.suffix == ".app":
            return parent
    raise RuntimeError("?? macOS app bundle ??? ?? ?????.")


def launch_macos_updater(downloaded_path):
    app_bundle = get_current_app_bundle()
    update_dir = downloaded_path.parent / "extracted"
    with zipfile.ZipFile(downloaded_path) as zip_file:
        zip_file.extractall(update_dir)

    new_app = update_dir / app_bundle.name
    if not new_app.exists():
        candidates = list(update_dir.glob("*.app"))
        if not candidates:
            raise RuntimeError("???? ????? app bundle? ?? ?????.")
        new_app = candidates[0]

    script_path = downloaded_path.with_suffix(".sh")
    script_path.write_text(
        "\n".join(
            [
                "#!/bin/sh",
                "sleep 2",
                f'rm -rf "{app_bundle}"',
                f'ditto "{new_app}" "{app_bundle}"',
                f'open "{app_bundle}"',
                f'rm -rf "{downloaded_path.parent}"',
            ]
        ),
        encoding="utf-8",
    )
    os.chmod(script_path, 0o755)
    subprocess.Popen(["/bin/sh", str(script_path)])

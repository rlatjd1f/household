import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import urllib.request
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
    sha256: str = ""


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
                sha256=parse_sha256_digest(asset.get("digest")),
            )
    return None


def parse_sha256_digest(digest):
    if digest and digest.startswith("sha256:"):
        return digest.split(":", 1)[1].lower()
    return ""


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
        hasher = hashlib.sha256()
        with target_path.open("wb") as output:
            while True:
                chunk = response.read(1024 * 512)
                if not chunk:
                    break
                output.write(chunk)
                hasher.update(chunk)
                downloaded_size += len(chunk)
                if progress_callback and total_size:
                    downloaded_mb = downloaded_size // 1024 // 1024
                    total_mb = total_size // 1024 // 1024
                    progress_callback(
                        f"업데이트 파일을 다운로드하고 있습니다. ({downloaded_mb}MB / {total_mb}MB)",
                        min(99, int(downloaded_size * 100 / total_size)),
                    )
    # GitHub이 제공하는 SHA-256 digest가 있으면 다운로드 파일 무결성 확인
    if update_info.sha256 and hasher.hexdigest() != update_info.sha256:
        target_path.unlink(missing_ok=True)
        raise RuntimeError("다운로드한 업데이트 파일의 무결성 검증에 실패했습니다.")
    if progress_callback:
        progress_callback("다운로드가 완료되었습니다. 업데이트를 준비하고 있습니다.", 100)
    return target_path


def install_update(update_info, progress_callback=None):
    if not getattr(sys, "frozen", False):
        raise RuntimeError("자동 업데이트는 배포된 실행 파일에서만 사용할 수 있습니다.")

    downloaded_path = download_asset(update_info, progress_callback)
    if sys.platform == "win32":
        if progress_callback:
            progress_callback("프로그램을 종료한 뒤 업데이트를 적용하고 재시작합니다.", 100)
        launch_windows_updater(downloaded_path)
        return
    if sys.platform == "darwin":
        if progress_callback:
            progress_callback("업데이트 패키지를 압축 해제하고 있습니다.", 100)
        launch_macos_updater(downloaded_path)
        return
    raise RuntimeError("지원하지 않는 운영체제입니다.")


def get_update_log_path():
    if sys.platform == "win32":
        base_dir = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Application Support"
    else:
        base_dir = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    log_dir = base_dir / "HouseholdManager" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "updater.log"


def powershell_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def launch_windows_updater(downloaded_path):
    current_exe = Path(sys.executable).resolve()
    current_pid = os.getpid()
    log_path = get_update_log_path()
    script_path = downloaded_path.with_suffix(".ps1")
    script_path.write_text(
        "\n".join(
            [
                "$ErrorActionPreference = 'Stop'",
                f"$LogPath = {powershell_quote(log_path)}",
                "function Write-UpdateLog($Message) { Add-Content -LiteralPath $LogPath -Value ((Get-Date -Format o) + ' ' + $Message) }",
                f"$ProcessIdToWait = {current_pid}",
                f"$DownloadedPath = {powershell_quote(downloaded_path)}",
                f"$TargetPath = {powershell_quote(current_exe)}",
                "Write-UpdateLog \"updater started. pid=$ProcessIdToWait target=$TargetPath source=$DownloadedPath\"",
                "try {",
                "  Wait-Process -Id $ProcessIdToWait -Timeout 60 -ErrorAction SilentlyContinue",
                "} catch {",
                "  Write-UpdateLog \"wait failed: $($_.Exception.Message)\"",
                "}",
                "for ($Attempt = 1; $Attempt -le 60; $Attempt++) {",
                "  try {",
                "    Copy-Item -LiteralPath $DownloadedPath -Destination $TargetPath -Force",
                "    Write-UpdateLog \"copy succeeded\"",
                "    Start-Process -FilePath $TargetPath",
                "    Write-UpdateLog \"restart launched\"",
                "    Remove-Item -LiteralPath $DownloadedPath -Force -ErrorAction SilentlyContinue",
                "    Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue",
                "    exit 0",
                "  } catch {",
                "    Write-UpdateLog \"copy retry $Attempt failed: $($_.Exception.Message)\"",
                "    Start-Sleep -Seconds 1",
                "  }",
                "}",
                "Write-UpdateLog \"copy failed after retries\"",
                "exit 1",
            ]
        ),
        encoding="utf-8",
    )
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creation_flags |= subprocess.CREATE_NO_WINDOW
    subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
        ],
        creationflags=creation_flags,
    )


def get_current_app_bundle():
    executable = Path(sys.executable).resolve()
    for parent in [executable, *executable.parents]:
        if parent.suffix == ".app":
            return parent
    raise RuntimeError("현재 macOS 앱 번들 경로를 찾을 수 없습니다.")


def launch_macos_updater(downloaded_path):
    app_bundle = get_current_app_bundle()
    update_dir = downloaded_path.parent / "extracted"
    # zipfile은 실행 권한과 심볼릭 링크를 보존하지 않으므로 ditto로 압축 해제
    subprocess.run(["ditto", "-x", "-k", str(downloaded_path), str(update_dir)], check=True)

    new_app = update_dir / app_bundle.name
    if not new_app.exists():
        candidates = list(update_dir.glob("*.app"))
        if not candidates:
            raise RuntimeError("업데이트 패키지에서 앱 번들을 찾을 수 없습니다.")
        new_app = candidates[0]

    staged_app = app_bundle.with_name(app_bundle.name + ".new")
    backup_app = app_bundle.with_name(app_bundle.name + ".old")
    log_path = get_update_log_path()
    q = shlex.quote
    script_path = downloaded_path.with_suffix(".sh")
    script_path.write_text(
        "\n".join(
            [
                "#!/bin/sh",
                f"LOG={q(str(log_path))}",
                'log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $1" >> "$LOG"; }',
                f"log {q(f'updater started. pid={os.getpid()} target={app_bundle}')}",
                f"while kill -0 {os.getpid()} 2>/dev/null; do sleep 0.5; done",
                f"rm -rf {q(str(staged_app))} {q(str(backup_app))}",
                f"if ! ditto {q(str(new_app))} {q(str(staged_app))}; then log 'copy failed'; exit 1; fi",
                f"if ! mv {q(str(app_bundle))} {q(str(backup_app))}; then log 'backup failed'; rm -rf {q(str(staged_app))}; exit 1; fi",
                f"if ! mv {q(str(staged_app))} {q(str(app_bundle))}; then",
                f"  log 'swap failed, restoring'; mv {q(str(backup_app))} {q(str(app_bundle))}; exit 1",
                "fi",
                f"rm -rf {q(str(backup_app))}",
                "log 'update applied'",
                f"open {q(str(app_bundle))}",
                f"rm -rf {q(str(downloaded_path.parent))}",
            ]
        ),
        encoding="utf-8",
    )
    os.chmod(script_path, 0o755)
    subprocess.Popen(["/bin/sh", str(script_path)], start_new_session=True)

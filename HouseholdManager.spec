# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all

# Matplotlib 의존성 자동 수집
datas, binaries, hiddenimports = collect_all('matplotlib')
datas += [('assets', 'assets')]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == 'darwin':
    # macOS: App Bundle (.app) 형태로 빌드하여 시스템 호환성 확보
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='HouseholdManager',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity='-', # Ad-hoc 서명
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='HouseholdManager',
    )
    app = BUNDLE(
        coll,
        name='HouseholdManager.app',
        icon='assets/icon/app.icns',
        bundle_identifier='com.household.manager',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'CFBundleAllowMixedLocalizations': True,
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.13.0',
        }
    )
else:
    # Windows: 배포 편의를 위해 단일 파일 (.exe) 형태로 빌드
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='HouseholdManager',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='assets/icon/app.ico',
    )

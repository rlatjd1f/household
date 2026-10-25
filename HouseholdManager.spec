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
    # 앱에서 쓰지 않는 Tk (Tcl/Tk 데이터 파일이 많아 단일 exe 시작 시 압축 해제가 느려짐)
    excludes=['tkinter', '_tkinter', 'PIL.ImageTk'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

if sys.platform == 'win32':
    # 단일 exe는 실행할 때마다 전체를 임시 폴더에 풀기 때문에, 사용하지 않는 대용량 파일을 빼서 시작 속도를 줄임
    # (소프트웨어 OpenGL, PDF 이미지 플러그인, AVIF 이미지, Qt 번역 파일, macOS 아이콘)
    def _is_unused(dest):
        d = dest.replace('\\', '/').lower()
        return (d.endswith('opengl32sw.dll') or d.endswith('qt6pdf.dll') or 'imageformats/qpdf' in d
                or '/_avif' in d or 'pyqt6/qt6/translations/' in d or d.endswith('app.icns'))
    a.binaries = [b for b in a.binaries if not _is_unused(b[0])]
    a.datas = [d for d in a.datas if not _is_unused(d[0])]

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

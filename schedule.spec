# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for School Schedule Manager
# Build with:  pyinstaller schedule.spec

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # PySide6 modules not always auto-detected by the hook
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtSvg",
        "PySide6.QtXml",
        "PySide6.QtSql",
        # Application packages
        "db",
        "db.database",
        "models",
        "models.models",
        "scheduler",
        "scheduler.engine",
        "ui",
        "ui.main_window",
        "ui.teachers_form",
        "ui.rooms_form",
        "ui.sections_form",
        "ui.subjects_form",
        "ui.schedule_view",
        # seed_data is imported at runtime by main._seed_if_empty()
        "seed_data",
    ],
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ScheduleManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # windowed – no terminal window on launch
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
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
    name="ScheduleManager",
)

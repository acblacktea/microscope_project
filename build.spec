# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for 荣宇藻类AI智慧分析
#
# 使用方法（在 Windows 上执行）：
#   pip install pyinstaller
#   pyinstaller build.spec

import os

SDK_DIR = os.path.join('uvchamsdk.20250428', 'python', 'samples')
DLL_DIR = os.path.join('uvchamsdk.20250428', 'x64')

a = Analysis(
    ['src/main_window.py'],
    pathex=[],
    binaries=[
        # 将 x64/uvcham.dll 打包到与 uvcham.py 同目录
        (os.path.join(DLL_DIR, 'uvcham.dll'), '.'),
    ],
    datas=[
        # 将 uvcham.py（Python 封装）打包进去
        (os.path.join(SDK_DIR, 'uvcham.py'), '.'),
    ],
    hiddenimports=[
        'google.genai',
        'google.genai.types',
        'openai',
        'docx',
        'docx.shared',
        'docx.enum.text',
        'docx.enum.table',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='microscope_ai',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 无控制台窗口
    icon=None,      # 可替换为 .ico 图标路径
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='microscope_ai',
)

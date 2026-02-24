# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run.py'],
    pathex=['src'],
    binaries=[],
    datas=[('src/ui/assets', 'ui/assets')],
    hiddenimports=['PySide6', 'PySide6.QtWidgets', 'PySide6.QtCore', 'PySide6.QtGui', 'requests', 'cryptography', 'fitz', 'ui', 'ui.login_dialog', 'ui.main_hub', 'ui.main_window', 'ui.bipro_view', 'ui.gdv_editor_view', 'ui.partner_view', 'ui.archive_view', 'ui.archive_boxes_view', 'ui.settings_dialog', 'ui.user_detail_view', 'ui.styles', 'ui.styles.tokens', 'api', 'api.client', 'api.auth', 'api.documents', 'api.gdv_api', 'api.openrouter', 'api.processing_history', 'api.smartadmin_auth', 'api.vu_connections', 'api.xml_index', 'parser', 'parser.gdv_parser', 'domain', 'domain.models', 'domain.mapper', 'layouts', 'layouts.gdv_layouts', 'services', 'services.document_processor', 'services.atomic_ops', 'services.data_cache', 'config', 'config.certificates', 'config.processing_rules', 'config.smartadmin_endpoints', 'config.vu_endpoints', 'bipro', 'bipro.bipro_connector', 'bipro.transfer_service', 'bipro.categories', 'bipro.rate_limiter', 'i18n', 'i18n.de'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='GDV-Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['src\\ui\\assets\\icon.ico'],
)

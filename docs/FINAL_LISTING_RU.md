# Финальный листинг проекта «Режим киоска»

Актуально на 2026-06-18. Проект выпускается в виде двух независимых загрузчиков без автоматического селектора.

```text
Windows XP SP1-SP3 / Windows Server 2003 x86 -> RezhimKioska-Legacy.exe
Windows 7 SP1-Windows 11                     -> RezhimKioska-Modern.exe
```

## Точки входа и сборка

- `main.py` — CLI и запуск Modern-оболочки.
- `legacy_main.py` — независимый Python 2.7 entry point Legacy-оболочки.
- `RezhimKioska.Modern.spec` — PyInstaller recipe Modern.
- `RezhimKioska.Legacy.spec` — PyInstaller 3.2.1 recipe Legacy PE32/x86.
- `build_modern.ps1` — тесты и воспроизводимая сборка Modern.
- `build_legacy.cmd` — тесты и сборка Legacy из локального wheelhouse.
- `build_release.ps1` — упаковка двух готовых EXE, исходников и SHA-256-манифеста.
- `requirements-modern-build.txt` — зафиксированные зависимости Modern.
- `requirements-legacy-build.txt` — зафиксированные зависимости Legacy.

## Modern

- `python_kiosk/config.py` — чтение и проверка `config/kiosk.json`, включая UTF-8 BOM.
- `python_kiosk/launcher.py` — запуск оболочки и watchdog разрешённого приложения.
- `python_kiosk/shell_ui.py` — русская полноэкранная оболочка, админ-диалог и управление свёрнутым приложением.
- `python_kiosk/process_watchdog.py` — контроль одного разрешённого EXE без массового завершения процессов.
- `python_kiosk/window_control.py` — поиск, активация, восстановление и позиционирование окна разрешённого ПО.
- `python_kiosk/windows_key_filter.py` — фильтрация системных комбинаций только в операторском режиме; Win+L пропускается.
- `python_kiosk/local_admin_auth.py` — локальная проверка Windows-администратора без сохранения пароля.
- `python_kiosk/admin_session.py` — временная административная сессия с таймаутом.
- `python_kiosk/session_lockdown.py` — ограничение desktop-элементов только текущей операторской сессии.
- `python_kiosk/configurator.py` — dry-run/apply установка с проверкой повышенных прав.
- `python_kiosk/restore_tool.py` — независимый Restore/Undo.
- `python_kiosk/policy_engine.py` — выбор профиля Windows и построение обратимых операций.
- `python_kiosk/system_backend.py` — операторские registry/shell операции; службы, драйверы и автозагрузка не изменяются.
- `python_kiosk/backup_store.py` — резервная копия до применения политик.
- `python_kiosk/logging_service.py` — JSONL-журнал с ротацией и удалением чувствительных полей.
- `python_kiosk/platform_detect.py` — граница Modern: Windows 7 SP1-Windows 11.

## Legacy

- `legacy_kiosk/config.py` — Python 2.7-совместимая конфигурация.
- `legacy_kiosk/platform_guard.py` — допуск только XP SP1-SP3 и Server 2003 x86.
- `legacy_kiosk/shell.py` — русская Tk-оболочка со статусом приложения и кнопкой разблокировки.
- `legacy_kiosk/watchdog.py` — один процесс, задержка перезапуска и принятие уже работающего точного пути.
- `legacy_kiosk/window_control.py` — Win32-управление окном разрешённого приложения.
- `legacy_kiosk/keyboard_filter.py` — блокировка Win/Alt+Tab/Ctrl+Alt+Tab и других обходов с сохранением обычного ввода.
- `legacy_kiosk/auth.py` — `LogonUserW`, проверка группы Administrators и закрытие token handles.
- `legacy_kiosk/admin_session.py` — ограниченная по времени сессия с impersonation только для защищённых записей.
- `legacy_kiosk/policy_engine.py` — обратимые HKU/HKCU legacy-политики.
- `legacy_kiosk/backup.py` — точный снимок shell, значений политик и DACL.
- `legacy_kiosk/installer.py` — shell записывается последним; при ошибке выполняется обратный rollback.
- `legacy_kiosk/logging_service.py` — XP-совместимый журнал с ротацией и редактированием секретов.

## Общие контракты и конфигурация

- `config/kiosk.json` — рабочая конфигурация разрешённого Win32-приложения.
- `config/kiosk.default.json` — шаблон Modern.
- `config/kiosk.legacy.json` — шаблон Legacy.
- `config/policy-profiles.json` — профили `xp_legacy`, `win7_srp`, `win10_applocker`, `win10_shelllauncher`, `home_fallback`.
- `contracts/kiosk-config-v1.json` — общий контракт конфигурации без учётных данных.
- `contracts/backup-metadata-v1.json` — общие поля backup.
- `contracts/ui-labels-v1.json` — общие русские подписи интерфейса.

## Скрипты и документация

- `scripts/install.ps1` — установка Modern.
- `scripts/restore.ps1` — восстановление Modern.
- `scripts/create-operator-user.ps1` — создание отдельной неадминистративной операторской УЗ.
- `scripts/test-lab-setup.ps1` — безопасная подготовка тестовой среды.
- `README.md` — ручной выбор одного из двух EXE.
- `docs/INSTALL.md` — dry-run, install, repair и test-mode.
- `docs/RESTORE.md` — restore, uninstall и recover-desktop.
- `docs/TESTING.md` — тестирование только отдельной операторской УЗ.
- `docs/LEGACY-TESTING.md` — обязательная snapshot-VM матрица XP/Server 2003.
- `docs/SECURITY.md` — границы доверия, хранение паролей и EOL-риски Legacy.
- `docs/COMPATIBILITY.md` — честный статус каждой Windows-версии и редакции.

## Итоговая проверка

- 196 Modern unit/regression-тестов: успешно.
- 84 Legacy-теста под Python 2.7 x86: успешно.
- `RezhimKioska-Modern.exe`: PE32/x86.
- `RezhimKioska-Legacy.exe`: PE32/x86.
- Legacy wrong-platform smoke на Windows 11: код 3, shell не изменён, остаточных процессов нет.
- GitHub ZIP: оба EXE, конфигурация, исходники, документация и SHA-256-манифест; временные каталоги исключены.

Полный diff ветки формируется рядом с релизным архивом как `FULL-DIFF.patch`, а полный перечень отслеживаемых исходников — как `SOURCE-FILES.txt`.

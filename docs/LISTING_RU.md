# Листинг с комментариями

> Этот документ относится к предыдущим выпускам. Для версии 2.1 используем [инструкцию по установке и откату](../README.md) и [протокол испытаний в VMware](VMWARE-2.1.md).

Проект называется **«Режим киоска»**. Ниже перечислены основные файлы и назначение ключевых частей.

## main.py

- `DEFAULT_CONFIG_PATH` — основной путь к `kiosk_config.json`.
- `resolve_default_config_path()` — ищет конфиг в исходниках, рядом с exe и внутри PyInstaller bundle.
- `build_parser()` — команды `init`, `plan`, `restore-plan`, `install`, `restore`, `check-password`, `launch`, `set-app`, `change-password`, `status`.
- `main()` — точка входа. Без аргументов PyCharm RUN запускает `launch`.

## python_kiosk/config.py

- `KioskConfig` — app path, оператор, соль/hash пароля, профиль политики, задержка watchdog.
- `validate()` — проверяет обязательные поля.
- `load_config()` и `save_config()` — чтение и сохранение JSON.

## python_kiosk/security.py

- `hash_password()` — PBKDF2-HMAC-SHA256 с солью.
- `verify_password()` — проверка без открытого пароля.
- `_pbkdf2_fallback()` — совместимый fallback для старых Python.
- `FailedAttemptLimiter` — задержка после неверных попыток входа.

## python_kiosk/local_admin_auth.py

- `parse_windows_account_name()` — форматы `Админ`, `.\Админ`, `ПК\Админ`.
- `AuthResult` — структурированный результат: success, bad credentials, not admin или Windows/API error.
- `WindowsAuthError` — ошибка Win32 API с кодом.
- `WindowsAuthBackend.logon_user()` — проверка через `LogonUserW`.
- `WindowsAuthBackend.is_local_admin()` — проверка членства в локальных администраторах.
- `LocalAdminAuthenticator.authenticate_result()` — единая проверка логина/пароля администратора Windows без хранения пароля.
- `LocalAdminAuthenticator.authenticate()` — совместимый bool-wrapper.

## python_kiosk/admin_session.py

- `AdminSession` — ограниченная по времени административная сессия после успешной Windows-admin авторизации.
- `start()` — открывает сессию и задает `expires_at`.
- `is_active()` — проверяет таймаут и логирует возврат в киоск.
- `mark_desktop_unlocked()` — отмечает временную разблокировку рабочего стола.
- `close()` — закрывает admin-сессию и возвращает режим киоска.

## python_kiosk/launcher.py

- `KioskLauncher` — связывает конфиг, проверку администратора и watchdog.
- `create_watchdog()` — проверяет существование `.exe`, создает watchdog и не открывает второй экземпляр, если процесс уже запущен.
- `run()` — headless-надзор.

## python_kiosk/process_watchdog.py

- `windows_process_name_running()` — проверка процесса через `tasklist`.
- `ProcessWatchdog.tick()` — запуск, контроль и перезапуск разрешенного приложения.
- `logger` — пишет события `watchdog.started` и `watchdog.restarted`.

## python_kiosk/window_control.py

- `AppWindowController` — проверяет свернуто ли приложение, разворачивает его и выводит поверх оболочки.
- `ensure_foreground()` — разворачивает разрешенное приложение, кратко ставит его поверх KioskLauncher и снимает постоянный topmost.
- `WindowsWindowBackend` — использует `tasklist`, `EnumWindows`, `IsIconic`, `ShowWindow`, `SetWindowPos`, `SetForegroundWindow`.

## python_kiosk/shell_ui.py

- `build_shell_layout()` — макет оболочки «Режим киоска».
- `combine_windows_account_name()` — legacy-helper сохранен для обратной совместимости, но новое окно разблокировки его не использует.
- `ShellWindow` — полноэкранная фоновая оболочка, admin-сессия, watchdog tick, отображение `Свернуто`.
- `StyledAdminLoginDialog` — окно локального логина и пароля администратора Windows без поля домена/компьютера.
- `WindowsHotkeyListener` — удален; разблокировка доступна только кнопкой `Разблокировать`.
- `WindowsKeyFilter` — ограничивает Win/Alt/Ctrl обходы, включая Win+D/M/Tab, но сохраняет `Win+L`.
- `handle_unlock_desktop()` — запускает `explorer.exe` только внутри активной admin-сессии.
- `handle_stop_watchdog()` — временно останавливает watchdog разрешенного приложения для admin-сессии.
- `handle_return_to_kiosk()` — закрывает admin-сессию и возвращает блокировку.

## python_kiosk/platform_detect.py

- `WindowsInfo` — версия, build, редакция.
- `detect_windows_info()` — определение Windows через `platform` и `wmic`.
- `select_policy_profile()` — выбор `xp_legacy`, `win7_srp`, `win10_applocker`, `win10_shelllauncher`, `home_fallback`.

## python_kiosk/policy_engine.py

- `PolicyOperation` — одна обратимая операция.
- `PolicyExecutionPlan` — install/restore-план с режимом `dry-run` или `apply`.
- `PolicyEngine.load_profiles()` — читает `config/policy-profiles.json`.
- `build_install_plan()` — план: backup, операторская УЗ, shell, HKCU policies, фиксированный `.exe`, запрет трогать службы/драйверы/автозагрузку.
- `build_restore_plan()` — план возврата `explorer.exe` и отката политик PythonKiosk.

## python_kiosk/configurator.py

- `Configurator.install()` — проверяет права администратора при `apply`, создает backup, логирует план, применяет операции через backend.
- `_attempt_safe_rollback()` — при ошибке apply запускает restore-план.

## python_kiosk/restore_tool.py

- `RestoreTool.restore()` — dry-run или apply восстановления, не зависит от запущенного launcher.

## python_kiosk/backup_store.py

- `BackupStore.create_backup()` — сохраняет JSON backup с оператором, app path, shell `explorer.exe` и планом операций.
- `default_state_dir()` — `%PROGRAMDATA%\PythonKiosk` или домашний каталог.

## python_kiosk/logging_service.py

- `KioskLogger` — JSON Lines журнал.
- `default_log_path()` — `%PROGRAMDATA%\PythonKiosk\logs\kiosk.log`.
- `fallback_log_path()` — домашний каталог пользователя, если основной путь недоступен.

## python_kiosk/admin_actions.py

- `set_allowed_app_path()` — меняет фиксированный путь только на существующий `.exe`.
- `change_kiosk_admin_password()` — пересоздает salt/hash пароля.

## python_kiosk/system_backend.py

- `WindowsSystemBackend.is_admin()` — проверка прав администратора.
- `apply_operation()` — безопасная точка применения; запрещает stop/kill/clear startup операции.

## config

- `kiosk.default.json` — шаблон конфигурации.
- `policy-profiles.json` — описания профилей совместимости.

## scripts

- `install.ps1` — вызывает `python main.py install`, dry-run по умолчанию.
- `restore.ps1` — вызывает `python main.py restore`, dry-run по умолчанию.
- `create-operator-user.ps1` — создает/проверяет отдельную неадминскую УЗ.
- `test-lab-setup.ps1` — чек-лист безопасной проверки.

## build_release.ps1

- Собирает `RezhimKioska.exe` через PyInstaller.
- Кладет exe в `dist` и `release`.
- Готовит `release\PythonKiosk-GitHub.zip` с кодом, тестами, docs, config, scripts и src.

## Дополнение к листингу 2026-06-16

- `AllowedApplicationConfig.single_instance` — запрещает повторный запуск разрешенного `.exe`, если он уже найден по полному пути.
- `AllowedApplicationConfig.bring_existing_to_front` — при найденном существующем процессе выводит его окно поверх фоновой оболочки вместо запуска второго экземпляра.
- `AllowedApplicationConfig.restart_delay_ms` — задает задержку watchdog в миллисекундах.
- `windows_process_ids_for_path()` — получает PID только для процесса с совпадающим полным путем `ExecutablePath`.
- `windows_process_path_running()` — проверяет, запущен ли именно разрешенный `.exe`, а не одноименный файл из другой папки.
- `ProcessWatchdog.single_instance` — управляет запретом дублей; при `false` допускает второй запуск по конфигурации.
- `ProcessWatchdog.bring_existing_to_front` — callback для восстановления/активации уже открытого разрешенного приложения.
- `WindowsWindowBackend._process_ids_for_executable()` — использует полный путь процесса для поиска окна через `EnumWindows`.
- `ShellWindow._suspend_keyboard_filter_for_admin_session()` — временно останавливает keyboard hook после успешной Windows-admin авторизации.
- `ShellWindow._watchdog_tick()` — при истечении admin-сессии возвращает ограничения keyboard hook и снова включает операторский режим.
- `WindowsKeyFilter` — явно блокирует `Alt+Tab` и `Ctrl+Alt+Tab`, но пропускает обычный ввод текста и клавиши полей авторизации через `CallNextHookEx`.
- `KioskLogger._rotate_if_needed()` — выполняет простую ротацию JSONL-логов и не роняет оболочку, если запись в лог недоступна.





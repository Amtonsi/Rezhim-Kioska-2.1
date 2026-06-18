# Финальный листинг проекта Режим киоска

Сгенерировано автоматически из текущих исходных файлов проекта после исправлений 2026-06-17.

## .gitignore

```text
__pycache__/
*.py[cod]
build/
dist/
release/
.venv/
.idea/
*.log
```

## build_release.ps1

```powershell
$ErrorActionPreference = "Stop"

# Builds "Режим киоска" into an exe and prepares a GitHub archive.
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ReleaseDir = Join-Path $ProjectRoot "release"
$StageDir = Join-Path $ReleaseDir "github"
$ArchivePath = Join-Path $ReleaseDir "PythonKiosk-GitHub.zip"
$ResolvedProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$ResolvedReleaseDir = [System.IO.Path]::GetFullPath($ReleaseDir)
$ResolvedStageDir = [System.IO.Path]::GetFullPath($StageDir)

if (-not $ResolvedReleaseDir.StartsWith($ResolvedProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The release directory must stay inside the project."
}
if (-not $ResolvedStageDir.StartsWith($ResolvedReleaseDir, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The staging directory must stay inside release."
}

Set-Location $ProjectRoot

python -m PyInstaller --noconfirm --clean "$ProjectRoot\RezhimKioska.spec"

if (Test-Path $ReleaseDir) {
    Remove-Item -LiteralPath $ReleaseDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
New-Item -ItemType Directory -Force -Path $StageDir | Out-Null

Copy-Item -LiteralPath "$ProjectRoot\dist\RezhimKioska.exe" -Destination "$ReleaseDir\RezhimKioska.exe" -Force
New-Item -ItemType Directory -Force -Path "$ReleaseDir\config" | Out-Null
Copy-Item -LiteralPath "$ProjectRoot\config\kiosk.json" -Destination "$ReleaseDir\config\kiosk.json" -Force

$ArchiveFiles = @(
    "main.py",
    "RezhimKioska.spec",
    "requirements-build.txt",
    "README.md",
    "build_release.ps1"
)

foreach ($Item in $ArchiveFiles) {
    Copy-Item -LiteralPath "$ProjectRoot\$Item" -Destination "$StageDir\$Item" -Force
}

foreach ($Dir in @("python_kiosk", "tests", "docs", "config", "scripts", "src")) {
    Copy-Item -LiteralPath "$ProjectRoot\$Dir" -Destination "$StageDir\$Dir" -Recurse -Force
}

New-Item -ItemType Directory -Force -Path "$StageDir\dist" | Out-Null
Copy-Item -LiteralPath "$ProjectRoot\dist\RezhimKioska.exe" -Destination "$StageDir\dist\RezhimKioska.exe" -Force

Get-ChildItem -LiteralPath $StageDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $StageDir -Recurse -File |
    Where-Object { $_.Extension -eq ".pyc" -or $_.Extension -eq ".pyo" } |
    Remove-Item -Force

Compress-Archive -Path "$StageDir\*" -DestinationPath $ArchivePath -Force
Write-Host "Done: $ArchivePath"
```

## config\kiosk.default.json

```json
{
  "allowedApplication": {
    "arguments": "",
    "bringExistingToFront": true,
    "bringToFront": true,
    "path": "C:\\Windows\\System32\\notepad.exe",
    "restartDelayMs": 2000,
    "restartOnExit": true,
    "restoreIfMinimized": false,
    "singleInstance": true,
    "startMaximized": false,
    "workingDirectory": "C:\\Windows\\System32"
  },
  "featureFlags": {},
  "kiosk": {
    "adminSessionTimeoutSeconds": 300,
    "allowWinL": true,
    "blockDesktop": true,
    "blockWinKey": true,
    "disableExplorer": true,
    "disableStartMenu": true
  },
  "logging": {
    "level": "Info",
    "logDirectory": "C:\\ProgramData\\Kiosk\\Logs"
  },
  "operatorUser": "KioskOperator",
  "policyProfile": "auto",
  "restartDelaySeconds": 2,
  "restoreMetadata": {},
  "testing": {
    "requireBackupBeforeTest": true,
    "restoreAfterTest": true,
    "testOnlySeparateOperatorUser": true
  }
}
```

## config\kiosk.json

```json
{
  "allowedApplication": {
    "arguments": "",
    "bringExistingToFront": true,
    "bringToFront": true,
    "path": "C:\\Windows\\System32\\notepad.exe",
    "restartDelayMs": 2000,
    "restartOnExit": true,
    "restoreIfMinimized": false,
    "singleInstance": true,
    "startMaximized": false,
    "workingDirectory": "C:\\Windows\\System32"
  },
  "featureFlags": {},
  "kiosk": {
    "adminSessionTimeoutSeconds": 300,
    "allowWinL": true,
    "blockDesktop": true,
    "blockWinKey": true,
    "disableExplorer": true,
    "disableStartMenu": true
  },
  "logging": {
    "level": "Info",
    "logDirectory": "C:\\ProgramData\\Kiosk\\Logs"
  },
  "operatorUser": "test",
  "policyProfile": "auto",
  "restartDelaySeconds": 2,
  "restoreMetadata": {},
  "testing": {
    "requireBackupBeforeTest": true,
    "restoreAfterTest": true,
    "testOnlySeparateOperatorUser": true
  }
}
```

## config\policy-profiles.json

```json
{
  "home_fallback": {
    "description": "Замена shell и пользовательские ограничения реестра. Для Home-редакций уровень защиты ниже.",
    "mechanisms": ["operator_shell", "hkcu_policies"]
  },
  "win10_applocker": {
    "description": "Замена shell и подготовка AppLocker там, где доступно принудительное применение.",
    "mechanisms": ["operator_shell", "hkcu_policies", "applocker"]
  },
  "win10_shelllauncher": {
    "description": "Замена shell и подготовка Shell Launcher для Enterprise/Education/IoT.",
    "mechanisms": ["operator_shell", "hkcu_policies", "shelllauncher"]
  },
  "win7_srp": {
    "description": "Замена shell и подготовка Software Restriction Policies.",
    "mechanisms": ["operator_shell", "hkcu_policies", "srp"]
  },
  "xp_legacy": {
    "description": "Совместимая с XP замена shell и legacy-ограничения реестра.",
    "mechanisms": ["operator_shell", "hkcu_policies"]
  }
}
```

## docs\AUDIT.md

```markdown
# Аудит проекта

## Найдено при первичном аудите

- Критично: структура не соответствовала требуемым `/src`, `/config`, `/scripts`, `/docs`.
- Критично: отсутствовали отдельные `Configurator`, `PolicyEngine`, `RestoreTool`, backup-store и локальный JSONL-журнал.
- Безопасность: пароль администратора киоска хранился безопасно, но не было задержки после неверных попыток.
- Совместимость: выбор профиля Windows был только в коде, без внешнего `policy-profiles.json`.
- Права администратора: не было отдельного install/restore apply-процесса с проверкой прав.
- Восстановление: restore был текстовым планом, без отдельного инструмента и backup-файла.
- Тестирование: не было тестов на архитектурную структуру, backup, rollback, install/restore CLI и запрет опасных операций.
- Интерфейс: оболочка уже запускала разрешенное приложение, но админ-действия изменения пути и пароля были недоступны через отдельные команды.
- Упаковка: GitHub-архив не включал новые каталоги `config`, `scripts`, `src`.

## Не найдено опасных действий

- Нет `taskkill` или массового завершения процессов.
- Нет остановки или отключения служб Windows.
- Нет отключения драйверов.
- Нет очистки автозагрузки.
- Нет применения настроек к основной учетной записи пользователя.
- Нет скрытия процесса, инъекций, эксплойтов или обхода защитных средств.

## Исправлено

- Добавлены каталоги `src`, `config`, `scripts`, `docs`.
- Добавлены `PolicyEngine`, `Configurator`, `RestoreTool`, `BackupStore`, `KioskLogger`, `AdminActions`.
- Добавлены профили `xp_legacy`, `win7_srp`, `win10_applocker`, `win10_shelllauncher`, `home_fallback`.
- Добавлены команды `install`, `restore`, `set-app`, `change-password`, `status`.
- `install/restore` по умолчанию работают в dry-run.
- `--apply` требует права администратора.
- Перед установкой создается backup.
- При сбое apply выполняется safe rollback-план.
- Watchdog логирует запуск и перезапуск разрешенного приложения.
- Неверные попытки входа администратора получают задержку.
- Локальный журнал имеет fallback в домашний каталог.
- Backend явно запрещает операции остановки служб, драйверов, процессов и очистки автозагрузки.
- Документация обновлена под безопасную установку и rollback.
- Архив GitHub теперь включает `config`, `scripts`, `src`.
- Windows-admin авторизация теперь возвращает структурированную причину результата: success, неверные учетные данные, учетная запись не администратор или Windows/API ошибка.
- Окно авторизации содержит только логин локальной УЗ и пароль; поле домена/компьютера удалено.
- После успешной авторизации открывается admin-сессия с таймаутом; `explorer.exe` запускается только отдельным действием администратора.
- Разрешенное приложение разворачивается и кратко выводится поверх фонового KioskLauncher через `ensure_foreground()`, но постоянный topmost не удерживается.
- Configurator и RestoreTool используют единое сообщение отказа при отсутствии elevated admin-прав.

## Оставшиеся ограничения

- Текущая сборка Python 3.14 не совместима с Windows XP как исполняемый файл; для XP нужна отдельная legacy-сборка.
- Home-редакции Windows не дают того же уровня контроля, что Enterprise/Education с Shell Launcher.
- AppLocker и Shell Launcher зависят от редакции и включенности компонентов Windows.
- Реальное elevated apply-тестирование на текущем ноутбуке должно выполняться только из повышенной административной сессии и только для отдельной неадминской операторской УЗ. В неповышенной сессии проверяется отказ без частичных изменений.

## Итог

Проект приведен к безопасной гибридной архитектуре: launcher/watchdog, защищенная разблокировка, dry-run/apply граница, backup, restore, логирование, профили совместимости и документация. Системные службы, драйверы, автозагрузка и основная учетная запись не затрагиваются.
## Срочные исправления 2026-06-16

- Добавлен основной `config/kiosk.json` с nested-схемой `allowedApplication`, `kiosk`, `logging`.
- Исправлен запуск из PyCharm/RUN: при отсутствии конфига создаётся шаблон с Notepad.
- Добавлен `WindowsSessionLockdown`: в тестовом запуске скрывает/закрывает только Explorer-оболочку текущей сессии, не трогает службы, драйверы, автозагрузку и чужие процессы.
- Усилен keyboard hook: блокируются Win, Win+R/E/X/S/D/M/Tab, Ctrl+Esc, Alt+Tab/Esc/F4; Win+L оставлен через `LockWorkStation`.
- Кнопка `Разблокировать` открывает Windows-admin credential dialog и показывает сообщения отказа.
- Админ-сессия получила действие `Изменить приложение`.
- Watchdog учитывает `arguments`, `workingDirectory`, `restartOnExit`, `startMaximized` и ждёт input-idle после запуска процесса.
- Разрешённое окно ожидается, разворачивается и выводится поверх фонового окна киоска; оболочка уходит ниже после foreground-действия и не поднимается поверх админ-окон.
- `set-app` и legacy `change-password` теперь отказывают без elevated Windows admin-прав.

## Очередной аудит 2026-06-16: Alt+Tab, ввод и повторный запуск

Найдено:

- `Ctrl+Alt+Tab` блокировался только косвенно через `Alt+Tab`, без отдельной регрессионной проверки.
- После успешной Windows-admin авторизации keyboard hook оставался активным до отдельного действия `Открыть рабочий стол`; для admin-сессии это мешало временно вернуть обычное поведение Windows.
- Не было явного теста, что обычные клавиши ввода проходят в разрешенное приложение и окно авторизации.
- Проверка уже запущенного разрешенного приложения ориентировалась на имя процесса, что могло спутать одноименные `.exe` из разных каталогов.
- Логгер мог сорвать работу оболочки при отказе доступа к `%PROGRAMDATA%` и недоступном fallback-каталоге.

Исправлено:

- Добавлена явная обработка `Alt+Tab` и `Ctrl+Alt+Tab` в `WindowsKeyFilter`.
- Добавлены регрессионные тесты на `Alt+Tab`, `Ctrl+Alt+Tab`, обычный ввод и ввод в окне авторизации.
- После успешной авторизации администратора Windows keyboard hook временно останавливается; при возврате в киоск или таймауте admin-сессии включается снова.
- В `allowedApplication` добавлены `singleInstance`, `bringExistingToFront`, `restartDelayMs`.
- Watchdog проверяет уже запущенное приложение по полному пути и не запускает второй экземпляр при `singleInstance: true`.
- Управление окном разрешенного приложения тоже ищет процесс по полному пути.
- `KioskLogger` получил отказоустойчивую запись и ротацию логов.

Не выполнялось в этом прогоне:

- Реальное применение shell replacement к операторской учетной записи.
- Реальная проверка после перезагрузки.
- Проверка на Windows XP/Home/Enterprise. Для XP текущая сборка Python 3.14 не является исполняемо совместимой; нужен отдельный legacy build.


## Исправления по тесту пользователя test 2026-06-16

Найдено:

- Кнопка `Разблокировать` могла требовать повторного клика, если окно киоска было неактивным.
- После системных комбинаций могло оставаться внутреннее состояние `win_down`, из-за чего обычный ввод блокировался.
- Окно авторизации содержало лишнее поле домен/компьютер, хотя проверяется только локальная учетная запись.
- В интерфейсе и коде оставался скрытый hotkey разблокировки.

Исправлено:

- Кнопка `Разблокировать` обрабатывает и `<ButtonPress-1>`, и `<Button-1>`, с защитой от двойного открытия окна.
- Перед показом окна авторизации keyboard hook сбрасывает состояние модификаторов.
- `WindowsKeyFilter` восстанавливается после устаревшего состояния Win-клавиши через проверку физического состояния клавиши.
- Поле домен/компьютер удалено из макета и реального Tk-окна; вводятся только локальный логин и пароль.
- Текст hotkey удален из UI, регистрация глобального hotkey отключена, класс `WindowsHotkeyListener` удален.
- Разблокировка доступна только кнопкой.


## Исправления по окну завершения Windows 2026-06-16

Найдено:

- При старте киоска в уже открытой сессии session-lockdown скрывал desktop-окна, но затем отправлял `WM_CLOSE` в `Shell_TrayWnd`.
- На Windows 11 это могло вызвать системное окно `Завершение работы Windows`.

Исправлено:

- `WindowsDesktopBackend.lockdown_current_desktop_shell()` больше не отправляет `WM_CLOSE` в панель задач.
- Session-lockdown только скрывает desktop-элементы Explorer текущей сессии через `ShowWindow(SW_HIDE)`.
- Restore/release возвращает скрытые окна через `ShowWindow(SW_SHOW)`.
- Добавлен регрессионный тест `test_desktop_backend_hides_shell_without_posting_wm_close`.


## Исправления по повторным запускам и восстановлению desktop 2026-06-16

Найдено:

- `RezhimKioska.exe` можно было запустить повторно с той же конфигурацией.
- PyInstaller one-file показывает два служебных процесса на один запуск, поэтому проверять нужно не только количество процессов, но и отсутствие второго окна/второго разрешенного приложения.
- На Windows 11 `C:\Windows\System32\notepad.exe` делегирует запуск в `WindowsApps`, из-за чего точная проверка пути не видела уже открытый Notepad.

Исправлено:

- Добавлен `SingleInstanceGuard` на Windows named mutex для одной активной оболочки на конфигурацию.
- Watchdog сначала проверяет точный путь процесса, затем fallback по image name для delegating exe.
- Поиск окна разрешенного приложения также использует fallback по image name, если точный путь не дал PID.
- Добавлена команда `python main.py recover-desktop`, которая показывает shell-окна текущей сессии и запускает `explorer.exe`.
- `ShellWindow.start()` освобождает ограничения в `finally`, если Tk mainloop завершился штатно.

## Исправления системного применения 2026-06-17

Найдено:

- `WindowsSystemBackend.apply_operation()` был заглушкой и не применял shell/policies.
- `set_operator_shell` в install-плане не получал конкретную команду запуска `KioskLauncher`.
- Не было теста, что отсутствующий оператор или оператор с правами администратора отклоняется до применения киоска.

Исправлено:

- Добавлен реальный backend с безопасным command-runner: `reg add`, `reg delete`, `reg load`, `reg unload`, `wmic`, `net user`, `net localgroup`.
- Shell replacement записывается только в `HKU\<SID>\Software\Microsoft\Windows NT\CurrentVersion\Winlogon\Shell` операторской УЗ.
- Restore записывает `explorer.exe` обратно и удаляет только известные значения политик PythonKiosk.
- HKCU-политики оператора применяются только через точечные значения реестра: Task Manager, Regedit, CMD, Run, Control Panel и Explorer context/taskbar ограничения.
- `Configurator` передаёт в план готовую команду `launch --config`.
- `main.py` строит shell-команду для frozen exe и для запуска из исходников.
- Добавлены тесты `tests/test_system_backend.py` на shell replacement, restore policies, запрет опасных операций, отсутствующего оператора и оператора-администратора.

Проверено:

- `python -m unittest discover -s tests` — 141 тест, OK.
- `python main.py install --config config\kiosk.json` — dry-run с backup.
- `python main.py restore --config config\kiosk.json` — dry-run restore.
- `python main.py install --config config\kiosk.json --apply` без elevated-прав — отказ до изменений.
- `python main.py restore --config config\kiosk.json --apply` без elevated-прав — отказ до изменений.

## Исправления диагностического логирования 2026-06-17

Найдено:

- `launcher`, `ShellWindow` и `WindowsKeyFilter` могли создавать разные экземпляры logger-а, из-за чего события одного теста было трудно связать.
- Лог не имел обязательного `session_id` и `process_id`.
- Не было CLI-команды, которая сразу показывает, какой файл лога читать при тестировании.
- Keyboard hook не логировал факт блокировки системных комбинаций.

Исправлено:

- `KioskLogger` добавляет `session_id` и `process_id` в каждую JSONL-строку.
- Добавлена маскировка чувствительных полей: `password`, `secret`, `token`, `credential`, `hash`, `salt`.
- `KioskLauncher` использует `logging.logDirectory` из `config/kiosk.json`.
- `run_shell()` передает один logger в shell window и keyboard filter.
- Добавлена команда `python main.py log-path --config .\config\kiosk.json`, которая печатает путь и Session, а также пишет `diagnostic.log_ready`.
- Keyboard hook пишет только события блокировки системных комбинаций (`keyboard_filter.blocked_shortcut`), не записывая обычный ввод текста.
- При сворачивании/возврате разрешенного приложения пишется `shell.app_status_changed`.
- Watchdog больше не пишет полную командную строку приложения в лог; сохраняются только `executable` и `argument_count`.

Проверено:

- `python -m unittest discover -s tests -v` — 146 тестов, OK.
- `python main.py log-path --config config\kiosk.json` — создан/обновлен `C:\ProgramData\Kiosk\Logs\kiosk.log`.
- Живой headless-прогон `python main.py launch --config config\kiosk.json --headless`: создан один новый Notepad, записаны `launcher.initialized`, `launcher.watchdog_created`, `watchdog.started`; после проверки остановлены только созданные PID, выполнен `recover-desktop`, в сессии остался только `explorer.exe`.

## Исправления ввода и сворачивания 2026-06-17

Найдено:

- Keyboard hook блокировал `keyup` некоторых запрещенных сочетаний. Это могло оставлять Windows в состоянии залипшего модификатора и мешать обычному вводу.
- При ошибке проверки физического состояния Win/Alt/Ctrl фильтр работал слишком жестко и мог считать модификаторы нажатыми.
- Кнопка `Разблокировать` была привязана одновременно к `<ButtonPress-1>` и `<Button-1>`, из-за чего модальное окно могло открываться нестабильно.
- Проверка свернутого приложения смотрела только первый найденный hwnd процесса.
- Dry-run install без elevated-прав мог упасть на создании backup в `%PROGRAMDATA%`.
- Во время открытого окна авторизации watchdog продолжал фокусировать разрешенное приложение через `ensure_foreground()`. Из-за этого окно логина/пароля теряло фокус, и ввод выглядел неработающим.
- Если приложение уже было помечено как `minimized`, следующий тик мог вернуть статус в `running` и снова вывести приложение наверх без нажатия кнопки.

Исправлено:

- `WindowsKeyFilter` блокирует только `keydown` запрещенных системных сочетаний; `keyup` пропускается дальше через hook-цепочку.
- Если состояние физической клавиши недоступно, фильтр работает fail-open для обычного ввода и сбрасывает залипший Win-state.
- `Разблокировать` теперь срабатывает по одному `<Button-1>`.
- `AppWindowController.is_minimized()` проверяет все окна разрешенного процесса, чтобы корректно показать `Приложение свернуто` и кнопку `Развернуть приложение`.
- `BackupStore` для dry-run использует fallback-каталоги `%LOCALAPPDATA%`, `%TEMP%`, home, если основной state-dir недоступен. Для реального `--apply` fallback отключен.
- Пока открыто окно авторизации администратора, `_watchdog_tick()` больше не вызывает `_update_allowed_app_window()` и не уводит фокус с полей ввода.
- Состояние `minimized` сохраняется до ручного нажатия `Развернуть приложение`; автоматический возврат возможен только если включен `restoreIfMinimized` или watchdog реально перезапустил приложение.

Проверено:

- Точечные regression-тесты keyboard hook/canvas/window state/dry-run backup — OK.
- `python -m unittest discover -s tests` — 153 теста, OK.
- `python main.py recover-desktop` — рабочий стол текущей сессии восстановлен.
- PyInstaller успел собрать свежий `dist\RezhimKioska.exe`, затем стандартный `build_release.ps1` остановился на удалении занятого `release\RezhimKioska.exe`, потому что этот файл используется старой сессией `test`.
- Свежая сборка скопирована отдельно как `release\RezhimKioska-fixed.exe`; для GitHub подготовлен отдельный fixed-архив до остановки старой сессии.
- Дополнительно выявлено в живой сессии `test`: старый `release\RezhimKioska.exe` остается запущенным в Session 9 вместе с обычным `explorer.exe`, `StartMenuExperienceHost.exe` и `SearchHost.exe`. Текущий терминал `impal` не elevated, поэтому Windows отказала в `install --apply`, чтении HKU `test`, остановке старого `RezhimKioska` и `logoff 9`. Для применения фикса нужен запуск `scripts\apply-test-kiosk.ps1` от администратора Windows.

## Исправления изоляции тестовых логов 2026-06-17

Найдено:

- Юнит-тесты создавали обычные `KioskLogger()` и писали события в рабочий `C:\ProgramData\PythonKiosk\logs\kiosk.log`.
- CLI/launcher-тесты создавали `KioskConfig()` с дефолтным `logging.logDirectory`, из-за чего тестовые события `launcher.initialized` попадали в `C:\ProgramData\Kiosk\Logs\kiosk.log`.
- Из-за этого анализ живой сессии `test` смешивался с искусственными событиями `unit-tests`.

Исправлено:

- Добавлен override `PYTHONKIOSK_LOG_PATH` для `default_log_path()` и `configured_log_path()`.
- Добавлен тестовый bootstrap `tests/_test_environment.py`, который направляет все дефолтные тестовые логи в `%TEMP%\python-kiosk-tests\kiosk.log`.
- Все `test_*.py` подключают bootstrap до импортов кода приложения; это работает и для `python -m unittest tests...`, и для `python -m unittest discover -s tests`.
- Тесты лаунчера используют временный `logging.logDirectory`, а не рабочий `C:\ProgramData\Kiosk\Logs`.

Проверено:

- `python -m unittest tests.test_logging_service` — 7 тестов, OK.
- `python -m unittest discover -s tests` — 155 тестов, OK.
- До и после полного прогона `LastWriteTimeUtc` у `C:\ProgramData\PythonKiosk\logs\kiosk.log` и `C:\ProgramData\Kiosk\Logs\kiosk.log` не изменился; тестовые события пишутся в `%TEMP%\python-kiosk-tests\kiosk.log`.
- `python -m PyInstaller --noconfirm --clean RezhimKioska.spec` — сборка OK.
- Обновлены `release\RezhimKioska-fixed.exe` и `release\PythonKiosk-GitHub-fixed.zip`.
- `python main.py recover-desktop` — рабочий стол текущей сессии `impal` восстановлен; HKCU shell override у `impal` отсутствует, HKLM shell равен `explorer.exe`.

Ограничение текущего прогона:

- Реальная сессия `test` остается запущенной/отключенной со старым exe в Session 9. Текущий процесс не elevated (`BUILTIN\Администраторы` в токене `deny only`), поэтому live-замена shell и logoff Session 9 требуют запуска от имени администратора Windows.

## Исправления ввода после повторной проверки 2026-06-17

Найдено:

- `WindowsKeyFilter` восстанавливал залипшее состояние только для Win-клавиши. Если low-level hook не получал `keyup` для Alt или Ctrl, внутренние `alt_down`/`ctrl_down` могли оставаться активными и продолжать блокировать системные клавиши.
- В Session 9 одновременно оказались запущены два `RezhimKioska-fixed.exe`. Два fullscreen-слоя и два keyboard hook-а могут конкурировать за фокус и создавать эффект, что ввод в Notepad или окно авторизации не проходит.
- `SingleInstanceGuard` был привязан к пути config-файла. При разных строках config-path один и тот же оператор мог получить два независимых mutex-а и запустить второй KioskLauncher.

Исправлено:

- `WindowsKeyFilter` теперь синхронизирует stale-состояние Alt/Ctrl/Shift с физическим состоянием клавиатуры и сбрасывает флаги, если модификаторы уже не нажаты.
- Добавлены регрессионные тесты на stale Alt/Ctrl, обычный ввод после фильтра и сохранение блокировки Alt+Tab/Ctrl+Alt+Tab.
- `SingleInstanceGuard.for_operator()` ограничивает один экземпляр KioskLauncher для одного оператора в текущей Windows-сессии независимо от пути config-файла.
- Команда `launch` теперь использует operator-scoped guard, поэтому повторный запуск для `test` должен завершаться без второго окна/hook-а.
- Подготовлен новый незанятый exe `release\RezhimKioska-inputfix.exe`; `scripts\apply-test-kiosk.ps1` переключен на него.

Проверено:

- Точечные тесты keyboard hook stale-state — OK.
- Точечные тесты operator-scoped single-instance — OK.
- `python -m unittest discover -s tests` — 158 тестов, OK.
- `python -m PyInstaller --noconfirm --clean RezhimKioska.spec` — сборка OK.
- Обновлены `dist\RezhimKioska.exe`, `release\RezhimKioska.exe`, `release\RezhimKioska-inputfix.exe`.

Ограничение текущего прогона:

- Два уже запущенных `RezhimKioska-fixed.exe` в Session 9 не удалось завершить из неповышенного токена: `taskkill` вернул `Access is denied`.
- Elevated helper был запущен через UAC, но Windows вернула `The operation was canceled by the user`; `apply-test-kiosk.log` не создан.
- Для живой проверки ввода нужно подтвердить UAC или вручную запустить `scripts\apply-test-kiosk.ps1` в PowerShell от имени администратора, затем снова войти в `test`.
```

## docs\INSTALL.md

```markdown
# Установка

Установка должна выполняться только из обычной административной учетной записи Windows. Основную учетную запись пользователя не используйте как оператора.

## 1. Создать оператора

Dry-run:

```powershell
.\scripts\create-operator-user.ps1 -UserName "KioskOperator"
```

Применение:

```powershell
.\scripts\create-operator-user.ps1 -UserName "KioskOperator" -Apply
```

Скрипт создает или проверяет локальную учетную запись и удаляет ее из группы `Administrators`. На legacy-системах, где нет `New-LocalUser`, пользователя нужно создать через Computer Management или `net user`, затем проверить, что он не является администратором.

## 2. Создать конфиг

```powershell
python main.py init --app-path "C:\Path\App.exe" --operator "KioskOperator" --password "ПарольАдминистратораКиоска" --config kiosk_config.json
```

`--app-path` должен указывать на обычный `.exe`. UWP/Store-приложения проект не использует.

## 3. Проверить статус

```powershell
python main.py status --config kiosk_config.json
```

Команда показывает оператора, фиксированный путь приложения, определенную Windows-редакцию и выбранный профиль политики.

## 4. Проверить план установки

```powershell
.\scripts\install.ps1 -Config .\kiosk_config.json
```

Без `-Apply` это dry-run: shell, политики, службы, драйверы, процессы и автозагрузка не меняются.
Для лабораторной проверки можно указать отдельный каталог состояния:

```powershell
.\scripts\install.ps1 -Config .\kiosk_config.json -StateDir .\.kiosk-state
```

## 5. Проверить план восстановления

```powershell
.\scripts\restore.ps1 -Config .\kiosk_config.json
```

До реального применения должен быть понятный restore-план, возвращающий `explorer.exe` как shell оператора.

## 6. Применить

```powershell
.\scripts\install.ps1 -Config .\kiosk_config.json -Apply
```

При `--apply` программа требует права администратора, создает backup-файл, затем применяет только операции профиля киоска. Если операция падает, Configurator пытается выполнить safe rollback-план.

В текущей реализации `--apply` выполняет точечные изменения только для операторской УЗ:

- проверяет, что операторская УЗ существует и не входит в локальную группу Administrators;
- записывает `Shell` в `HKU\<SID>\Software\Microsoft\Windows NT\CurrentVersion\Winlogon`;
- если hive оператора не загружен, временно подключает `NTUSER.DAT`, применяет значения и выгружает hive;
- применяет HKCU-политики оператора для Task Manager, CMD, Regedit, Run, Control Panel и контекстных меню Explorer;
- не выполняет `taskkill`, `net stop`, `sc`, отключение драйверов и очистку автозагрузки.

Если команда запущена без повышенных прав, она должна завершиться до любых изменений сообщением `Отказано в доступе. Для выполнения действия требуются права администратора Windows.`

## Профили

- Windows XP: `xp_legacy`, только legacy shell replacement и registry policies.
- Windows 7/8/8.1: `win7_srp`, shell replacement и SRP там, где возможно.
- Windows 10/11 Home: `home_fallback`, ограниченный режим без Enterprise-гарантий.
- Windows 10/11 Professional: `win10_applocker`, AppLocker-подготовка там, где редакция поддерживает enforcement.
- Windows 10/11 Enterprise/Education/IoT: `win10_shelllauncher`, Shell Launcher там, где компонент доступен.

Home-редакции честно считаются менее защищенными: оболочка и политики снижают риск обхода, но не равны Enterprise-механизмам.
## Актуальная схема конфигурации

Основной файл конфигурации: `config/kiosk.json`. Если он отсутствует, `main.py launch` создаёт шаблон с `C:\Windows\System32\notepad.exe`.

Перед реальным применением проверьте:

```powershell
python main.py status --config .\config\kiosk.json
.\scripts\install.ps1 -Config .\config\kiosk.json
.\scripts\restore.ps1 -Config .\config\kiosk.json
```

Реальный `-Apply` выполняется только из повышенной административной сессии Windows и только для отдельной операторской УЗ. Основную УЗ пользователя не указывайте оператором.

При отсутствии прав должно быть показано:

```text
Отказано в доступе. Для выполнения действия требуются права администратора Windows.
```
```

## docs\LISTING_RU.md

```markdown
# Листинг с комментариями

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




```

## docs\RESTORE.md

```markdown
# Восстановление

Restore выполняется из обычной административной учетной записи Windows. Не нужно входить в операторскую учетную запись и не нужно, чтобы KioskLauncher был запущен.

## Dry-run

```powershell
.\scripts\restore.ps1 -Config .\kiosk_config.json
```

Dry-run показывает план, но не меняет Windows.
Для проверки без записи в `%PROGRAMDATA%` можно указать локальный каталог состояния:

```powershell
.\scripts\restore.ps1 -Config .\kiosk_config.json -StateDir .\.kiosk-state
```

## Применение

```powershell
.\scripts\restore.ps1 -Config .\kiosk_config.json -Apply
```

RestoreTool должен:

- вернуть `explorer.exe` как shell для операторской учетной записи;
- откатить только политики, созданные PythonKiosk;
- использовать backup-метаданные;
- не трогать службы, драйверы, системные процессы и существующую автозагрузку;
- записать действия в локальный журнал.

## Если оператор застрял в киоске

1. Нажмите `Win+L`.
2. Войдите в обычную административную учетную запись.
3. Запустите `.\scripts\restore.ps1 -Apply`.
4. После restore войдите в операторскую учетную запись и проверьте, что обычный рабочий стол вернулся.

## Чего restore не делает

- не удаляет учетную запись оператора;
- не очищает автозагрузку Windows;
- не останавливает службы;
- не завершает системные процессы;
- не меняет основную учетную запись пользователя.
## Актуальный restore

Restore запускается из обычной административной УЗ Windows, не из операторской. Используйте новый конфиг:

```powershell
.\scripts\restore.ps1 -Config .\config\kiosk.json
.\scripts\restore.ps1 -Config .\config\kiosk.json -Apply
```

Restore должен вернуть `explorer.exe` как shell операторской УЗ и откатить только политики киоска. Службы, драйверы, системные процессы и автозагрузка не входят в область restore.

Реальный `-Apply` выполняет точечный откат в hive операторской УЗ:

- записывает `explorer.exe` в `HKU\<SID>\Software\Microsoft\Windows NT\CurrentVersion\Winlogon\Shell`;
- удаляет только значения политик, которые создаёт PythonKiosk;
- при необходимости временно подключает `NTUSER.DAT` операторского профиля и затем выгружает его;
- не завершает процессы, не останавливает службы, не меняет драйверы и не чистит автозагрузку.

Без elevated-прав действие должно завершиться отказом:

```text
Отказано в доступе. Для выполнения действия требуются права администратора Windows.
```
```

## docs\SECURITY.md

```markdown
# Безопасность

## Границы проекта

KioskLauncher — административная оболочка для контролируемой операторской учетной записи. Это не скрытое ПО и не средство обхода защиты Windows.

Проект запрещает:

- массово завершать процессы;
- останавливать или отключать службы;
- отключать драйверы;
- очищать существующую автозагрузку;
- внедряться в чужие процессы;
- скрываться от администратора;
- применять настройки к основной учетной записи без явного выбора.

## Пароль администратора киоска

Пароль киоска не хранится в открытом виде. Используется:

- соль 16 байт;
- PBKDF2-HMAC-SHA256;
- 200000 итераций по умолчанию;
- fallback-реализация PBKDF2 для старых Python без `hashlib.pbkdf2_hmac`;
- constant-time сравнение, если доступно.

После нескольких неверных попыток `FailedAttemptLimiter` добавляет задержку. Успешный вход сбрасывает счетчик.

## Разблокировка и admin-сессия

Рабочий стол не разблокируется отдельным паролем киоска. Для admin-сессии используются системные учетные данные локального администратора Windows:

- `Администратор`;
- `.\Администратор`;
- `ИМЯ-ПК\Администратор`.

Окно входа содержит только поле локального пользователя и поле пароля. Поле домена/имени компьютера убрано. Проверка выполняется локально через Windows API `LogonUserW`, затем токен проверяется на членство в локальной группе `Administrators`. Handle токена закрывается после каждой попытки.

Результат проверки различает:

- неверное имя пользователя или пароль;
- корректные учетные данные без членства в `Administrators`;
- ошибку Windows/API с кодом, если он доступен.

Пароль Windows не сохраняется в конфиг, лог, реестр, файл или временный файл. В лог попадают только имя пользователя, код результата и код API-ошибки без token/secret data.

После успешной проверки открывается ограниченная admin-сессия с таймаутом. В этой сессии администратор может открыть рабочий стол через `explorer.exe`, остановить watchdog или вернуться в киоск. Если сессия истекла, режим киоска снова блокирует доступ к рабочему столу, если киоск явно не отключен.

Ввод учетных данных администратора Windows не повышает права уже запущенного процесса. Поэтому `Configurator` и `RestoreTool` для реального `--apply` дополнительно требуют, чтобы процесс был запущен с повышенными правами администратора Windows.

## Ограничение клавиш

В режиме оболочки блокируются обходные комбинации вроде `Alt+Tab`, `Alt+F4`, `Ctrl+Esc`, `Ctrl+Shift+Esc`, `Win+D`, `Win+M`, `Win+Tab` и Win-комбинации запуска/поиска. `Win+L` сохраняется: оболочка вызывает блокировку сеанса Windows и не препятствует смене пользователя.

## Логи

Локальный журнал пишется в JSON Lines:

```text
%PROGRAMDATA%\PythonKiosk\logs\kiosk.log
```

Если `%PROGRAMDATA%` недоступен, используется домашний каталог текущего пользователя. В лог не записываются пароли.

Логируются попытка открытия admin-окна, успешная авторизация Windows-администратора, отказ по неверному паролю, отказ по отсутствию прав администратора, ошибки Windows API, запуск `explorer.exe`, временная разблокировка рабочего стола, возврат в киоск, запуск и перезапуск разрешенного приложения.

Диагностический журнал пишется в JSONL с `session_id` и `process_id`; путь берется из `config/kiosk.json` (`logging.logDirectory`). Команда `python main.py log-path --config .\config\kiosk.json` создает маркер тестовой сессии и печатает путь/Session. Поля с `password`, `secret`, `token`, `credential`, `hash`, `salt` маскируются как `***REDACTED***`. Обычный ввод текста и пароли администратора Windows не записываются. Keyboard hook логирует только факт блокировки системной комбинации, например `Alt+Tab`, без записи вводимого текста. Watchdog не пишет полную командную строку разрешенного приложения; в журнал попадают только путь executable и количество аргументов.

## Backup и rollback

Перед применением Configurator создает backup-файл в state-dir. При ошибке в apply-режиме выполняется safe rollback-план: восстановление shell `explorer.exe` и откат только политик PythonKiosk.

Системный backend применяет только адресные операции реестра операторского профиля. Shell replacement пишется в `HKU\<SID>\Software\Microsoft\Windows NT\CurrentVersion\Winlogon`, а политики — в HKCU-ветки оператора. Если hive не загружен, backend временно подключает `NTUSER.DAT` оператора через `reg load` и выгружает через `reg unload`.

Запрещённые операции `stop_services`, `disable_services`, `clear_startup`, `kill_processes`, `terminate_processes`, `disable_drivers` отклоняются. Код применения не использует `taskkill`, `net stop`, `sc`, отключение драйверов или очистку автозагрузки.

## Ограничения редакций Windows

На Home-редакциях нет равной Enterprise-защиты. Проект использует fallback: shell replacement и пользовательские политики. Это снижает риск выхода оператора, но не равно Shell Launcher или полноценно enforced AppLocker.

Windows XP поддерживается как legacy-цель архитектуры, но текущая сборка Python 3.14 не запускается на XP. Для XP нужна отдельная legacy-сборка.
## Срочные исправления блокировки

- `config/kiosk.json` не хранит пароль администратора Windows.
- Разблокировка использует Windows API: `LogonUser`, токен пользователя и проверку членства в Administrators.
- Неверные учётные данные и не-администратор различаются сообщениями отказа.
- Keyboard hook работает только в операторском режиме, не записывает ввод и блокирует только системные комбинации обхода.
- `Win+L` оставлен доступным через `LockWorkStation`.
- Session lockdown скрывает только desktop-элементы Explorer текущей интерактивной сессии; `WM_CLOSE` в панель задач не отправляется. Служб, драйверов, автозагрузки и чужих процессов он не касается.
- Разрешённое приложение выводится поверх фонового KioskLauncher через Win32 `EnumWindows`, `ShowWindow`, `SetWindowPos`, `SetForegroundWindow`; постоянный topmost не удерживается, чтобы не перекрывать диалоги и админ-окна.

## Дополнение 2026-06-16: keyboard hook и защита ввода

Keyboard hook используется только в операторском режиме и не является keylogger. Он не сохраняет, не логирует и не передает введенный текст. Запрещенные комбинации обрабатываются точечно: `Win`, опасные `Win+...`, `Ctrl+Esc`, `Ctrl+Shift+Esc`, `Alt+Tab`, `Ctrl+Alt+Tab`, `Alt+Esc`, `Alt+F4`. Разрешенные клавиши передаются дальше через `CallNextHookEx`.

Обычный ввод в разрешенном приложении и в окне авторизации администратора должен работать: буквы, цифры, пробел, `Backspace`, `Delete`, `Enter` и обычный `Tab` не блокируются. `Win+L` остается доступным.

После успешной проверки Windows-администратора hook временно останавливается на время admin-сессии. При возврате в киоск или после таймаута admin-сессии hook запускается снова. После Restore/Undo hook не должен быть активен.

Watchdog и поиск окна разрешенного приложения используют полный путь к `.exe`. Это снижает риск спутать разрешенное приложение с одноименным файлом в другой папке. На legacy-системах, где Windows не может вернуть полный путь процесса, это место считается ограничением совместимости и требует ручной проверки.

Логирование устойчиво к отказу доступа к `%PROGRAMDATA%`: при ошибке используется пользовательский fallback-каталог, а если недоступен и он, киоск продолжает работу без падения. Логи ротируются и не содержат пароли или вводимые символы.


```

## docs\superpowers\plans\2026-06-15-python-kiosk-implementation.md

```markdown
# PythonKiosk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safe Python kiosk skeleton that can supervise one fixed Win32 executable, protect admin configuration with a password, and generate reversible Windows policy plans without accidentally locking the development machine.

**Architecture:** The app is split into focused Python modules: configuration, password security, Windows profile detection, policy planning, process supervision, and launcher/admin unlock. `main.py` is only the CLI entry point. Real policy writes are not performed by default.

**Tech Stack:** Python standard library only (`argparse`, `json`, `hashlib`, `hmac`, `subprocess`, `tkinter`, `ctypes`, `unittest`).

---

## File Structure

- `main.py`: CLI entry point for init, plan, launch, password check, and restore-plan commands.
- `python_kiosk/config.py`: JSON config model, validation, load/save helpers.
- `python_kiosk/security.py`: password hashing, salt generation, verification, lockout delay.
- `python_kiosk/platform_detect.py`: Windows version/edition model and policy-profile selection.
- `python_kiosk/policy_plan.py`: dry-run install/restore policy steps.
- `python_kiosk/process_watchdog.py`: process supervisor that restarts the allowed app.
- `python_kiosk/launcher.py`: launcher orchestration and optional Tkinter admin unlock prompt.
- `tests/test_config.py`: config validation tests.
- `tests/test_security.py`: password hash tests.
- `tests/test_platform_detect.py`: profile selection tests.
- `tests/test_watchdog.py`: restart decision tests.
- `tests/test_policy_plan.py`: dry-run plan tests.

### Task 1: Configuration

**Files:**
- Create: `python_kiosk/config.py`
- Test: `tests/test_config.py`

- [ ] Write tests for default config creation, validation, and round-trip JSON save/load.
- [ ] Implement `KioskConfig` with `to_dict`, `from_dict`, `validate`, `load_config`, and `save_config`.
- [ ] Run `python -m unittest tests.test_config -v`.

### Task 2: Password Security

**Files:**
- Create: `python_kiosk/security.py`
- Test: `tests/test_security.py`

- [ ] Write tests proving a password verifies, a wrong password fails, and hashes use different salts.
- [ ] Implement PBKDF2-HMAC-SHA256 with a pure-Python PBKDF2 fallback for old runtimes.
- [ ] Run `python -m unittest tests.test_security -v`.

### Task 3: Platform Detection

**Files:**
- Create: `python_kiosk/platform_detect.py`
- Test: `tests/test_platform_detect.py`

- [ ] Write tests for XP, Windows 7 Pro, Windows 10 Home, Windows 10 Pro, and Windows 10 Enterprise profile choices.
- [ ] Implement `WindowsInfo`, `detect_windows_info`, and `select_policy_profile`.
- [ ] Run `python -m unittest tests.test_platform_detect -v`.

### Task 4: Policy Plan

**Files:**
- Create: `python_kiosk/policy_plan.py`
- Test: `tests/test_policy_plan.py`

- [ ] Write tests proving generated install and restore plans are dry-run text operations.
- [ ] Implement policy plan objects for shell replacement, UI restrictions, AppLocker/SRP/Shell Launcher notes, and restore steps.
- [ ] Run `python -m unittest tests.test_policy_plan -v`.

### Task 5: Watchdog

**Files:**
- Create: `python_kiosk/process_watchdog.py`
- Test: `tests/test_watchdog.py`

- [ ] Write tests for restart decisions without launching real programs.
- [ ] Implement `ProcessWatchdog` with injectable process factory and a single-step `tick` method for testing.
- [ ] Run `python -m unittest tests.test_watchdog -v`.

### Task 6: Launcher and CLI

**Files:**
- Create: `python_kiosk/launcher.py`
- Modify: `main.py`

- [ ] Implement launcher orchestration that loads config, verifies app path, starts watchdog, and offers an admin password prompt.
- [ ] Implement CLI commands: `init`, `plan`, `restore-plan`, `launch`, `check-password`.
- [ ] Ensure `python main.py` with no arguments prints help and does not apply policies.

### Task 7: Full Verification

**Files:**
- All project files

- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run `python main.py --help`.
- [ ] Run `python main.py init --app-path <python.exe> --operator Operator --password change-me --config work-kiosk.json`.
- [ ] Run `python main.py plan --config work-kiosk.json`.
- [ ] Delete only temporary test config files created in the project root.

## Self-Review

- Spec coverage: configuration, password protection, watchdog restart, policy profile selection, dry-run safety, restore planning, and `Win+L` non-blocking are covered.
- Placeholder scan: no `TBD` or unspecified implementation steps remain.
- Type consistency: modules share `KioskConfig`, `WindowsInfo`, `PolicyPlan`, and `ProcessWatchdog` names consistently.
```

## docs\superpowers\plans\2026-06-16-urgent-kiosk-lockdown.md

```markdown
# Urgent Kiosk Lockdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair operator lockdown, Windows-admin unlock, allowed-app foreground behavior, and the required `config/kiosk.json` configuration model.

**Architecture:** Keep the current Python/Tkinter/Win32 structure. Add focused services for configuration normalization and current-session desktop lockdown, then connect them through `KioskLauncher` and `ShellWindow`.

**Tech Stack:** Python stdlib, Tkinter, ctypes Win32 API, PowerShell wrapper scripts, unittest, PyInstaller.

---

### Task 1: Configuration Model

**Files:**
- Modify: `python_kiosk/config.py`
- Modify: `main.py`
- Create: `config/kiosk.json`
- Test: `tests/test_config.py`
- Test: `tests/test_cli.py`

- [x] Write failing tests that `ensure_default_config()` creates `config/kiosk.json` with `allowedApplication.path`, `operatorUser`, `kiosk.adminSessionTimeoutSeconds`, and no Windows password.
- [x] Write failing tests that `load_config()` reads the new nested model and still reads the old flat model.
- [x] Implement `AllowedApplicationConfig`, nested parsing, default creation, and save normalization.
- [x] Update default CLI config path to `config/kiosk.json`.
- [x] Run `python -m unittest tests.test_config tests.test_cli -v`.

### Task 2: Allowed App Watchdog

**Files:**
- Modify: `python_kiosk/launcher.py`
- Modify: `python_kiosk/process_watchdog.py`
- Test: `tests/test_launcher.py`
- Test: `tests/test_watchdog.py`

- [x] Write failing tests for arguments, working directory, restartOnExit false, and missing exe denial.
- [x] Implement watchdog command creation from nested allowed app config.
- [x] Add launch logging and process start error handling.
- [x] Run `python -m unittest tests.test_launcher tests.test_watchdog -v`.

### Task 3: Operator Session Lockdown

**Files:**
- Create: `python_kiosk/session_lockdown.py`
- Modify: `python_kiosk/shell_ui.py`
- Test: `tests/test_session_lockdown.py`
- Test: `tests/test_shell_ui.py`

- [x] Write failing tests that only `explorer.exe` shell in the current session is targeted and services/startup are never touched.
- [x] Implement `WindowsSessionLockdown.activate_operator_mode()` and `release_operator_mode()`.
- [x] Wire it into `ShellWindow.configure_window()` and admin release.
- [x] Run `python -m unittest tests.test_session_lockdown tests.test_shell_ui -v`.

### Task 4: Keyboard Filter

**Files:**
- Modify: `python_kiosk/shell_ui.py`
- Test: `tests/test_shell_ui.py`

- [x] Write failing tests for Win, Win+R, Win+E, Win+X, Win+S, Ctrl+Esc, Alt+Tab, Alt+Esc, Alt+F4 blocked and Win+L lock path allowed.
- [x] Implement explicit blocked shortcut decisions without key logging.
- [x] Run `python -m unittest tests.test_shell_ui -v`.

### Task 5: Foreground Window Control

**Files:**
- Modify: `python_kiosk/window_control.py`
- Modify: `python_kiosk/process_watchdog.py`
- Test: `tests/test_window_control.py`
- Test: `tests/test_watchdog.py`

- [x] Write failing tests for WaitForInputIdle, restore/maximize, foreground, and safe fast-restart behavior.
- [x] Implement `ensure_foreground(executable_path, start_maximized=False)`.
- [x] Add launch wait in watchdog when possible.
- [x] Run `python -m unittest tests.test_window_control tests.test_watchdog -v`.

### Task 6: Admin Unlock Actions

**Files:**
- Modify: `python_kiosk/shell_ui.py`
- Modify: `python_kiosk/admin_actions.py`
- Test: `tests/test_shell_ui.py`
- Test: `tests/test_admin_actions.py`

- [x] Write failing tests that unlock opens the credential dialog, shows denial messages, starts admin session on success, and can change the allowed app path.
- [x] Implement admin-session UI action hooks without storing Windows passwords.
- [x] Run `python -m unittest tests.test_shell_ui tests.test_admin_actions -v`.

### Task 7: Documentation, Listing, Build

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL.md`
- Modify: `docs/RESTORE.md`
- Modify: `docs/TESTING.md`
- Modify: `docs/SECURITY.md`
- Modify: `docs/FINAL_LISTING_RU.md`
- Modify: `build_release.ps1`

- [x] Update docs with `config/kiosk.json`, operator-only shell replacement, current-session Explorer shutdown boundary, and manual test checklist.
- [x] Regenerate final listing or full diff.
- [x] Run all tests.
- [x] Run safe dry-run install/restore scripts only.
- [x] Rebuild `release/RezhimKioska.exe` and `release/PythonKiosk-GitHub.zip`.
```

## docs\superpowers\plans\2026-06-16-windows-admin-session.md

```markdown
# Windows Admin Session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add structured Windows administrator authentication, foreground allowed-app behavior, time-limited admin session controls, and stricter admin-right denial behavior.

**Architecture:** Keep the existing Python modules and add small focused APIs. `local_admin_auth.py` returns structured authentication results; `shell_ui.py` owns the kiosk/admin session state; `window_control.py` guarantees allowed-app topmost behavior; Configurator/RestoreTool share a Russian access-denied message.

**Tech Stack:** Python 3, Tkinter, Win32 API through `ctypes`, `unittest`, PyInstaller.

---

### Task 1: Structured Windows Admin Authentication

**Files:**
- Modify: `python_kiosk/local_admin_auth.py`
- Modify: `python_kiosk/launcher.py`
- Test: `tests/test_local_admin_auth.py`

- [x] Write failing tests for `success`, `bad_credentials`, `not_admin`, `windows_error`, and handle close.
- [x] Run `python -m unittest tests.test_local_admin_auth -v` and verify expected failure.
- [x] Add `AuthResult` and result-code constants.
- [x] Make `LocalAdminAuthenticator.authenticate_result()` return structured results and keep `authenticate()` as a bool wrapper.
- [x] Run the auth tests until green.

### Task 2: Kiosk Shell Window Layering

**Files:**
- Modify: `python_kiosk/window_control.py`
- Modify: `python_kiosk/shell_ui.py`
- Test: `tests/test_window_control.py`
- Test: `tests/test_shell_ui.py`

- [x] Write failing tests that allowed app is restored/topmost above KioskLauncher and shell does not apply topmost to itself.
- [x] Run targeted tests and verify failures.
- [x] Add `ensure_foreground()` in `AppWindowController`.
- [x] Use `ensure_foreground()` on every watchdog tick.
- [x] Run targeted tests until green.

### Task 3: Admin Session

**Files:**
- Create: `python_kiosk/admin_session.py`
- Modify: `python_kiosk/shell_ui.py`
- Test: `tests/test_admin_session.py`
- Test: `tests/test_shell_ui.py`

- [x] Write failing tests for session timeout, unlock, explorer launch, watchdog stop, and return-to-kiosk.
- [x] Run targeted tests and verify failures.
- [x] Add `AdminSession` with timeout tracking and action methods.
- [x] Wire `ShellWindow.handle_admin_unlock()` to open the session after successful Windows admin authentication.
- [x] Keep passwords out of logs.
- [x] Run targeted tests until green.

### Task 4: Admin Rights Denial

**Files:**
- Modify: `python_kiosk/configurator.py`
- Modify: `python_kiosk/restore_tool.py`
- Test: `tests/test_configurator_restore.py`

- [x] Write failing tests for the exact denial message and no partial operation.
- [x] Run tests and verify failure.
- [x] Add shared denial constant.
- [x] Run tests until green.

### Task 5: Documentation, Listing, Build

**Files:**
- Modify: `README.md`
- Modify: `docs/SECURITY.md`
- Modify: `docs/TESTING.md`
- Modify: `docs/LISTING_RU.md`
- Modify: `docs/FINAL_LISTING_RU.md`

- [x] Update docs with Windows admin unlock, group membership check, window layering, session timeout, and remaining limitations.
- [x] Run `python -m unittest discover -s tests -v`.
- [x] Run safe dry-run scripts.
- [x] Rebuild with `.\build_release.ps1`.
- [x] Verify `release\PythonKiosk-GitHub.zip` contains docs/config/scripts/src.
```

## docs\superpowers\specs\2026-06-15-python-kiosk-design.md

```markdown
# PythonKiosk Design

## Goal

Build a Python-based Windows kiosk project that prepares files and tools for
locking a dedicated operator account to one fixed Win32 executable. The project
must not apply changes to the developer laptop unless an administrator
explicitly runs the installer/configurator on a target machine.

The operator must not get a normal Windows desktop. The kiosk application must
start before Explorer in the operator account, keep the allowed application
running, and restart it if it closes or crashes. Windows services, drivers,
system processes, and existing startup services must not be stopped or removed.

## Supported Windows Range

The project targets the broadest practical Windows range: Windows XP and newer.
Because kiosk capabilities differ by Windows version and edition, the project
uses a layered compatibility model instead of one mechanism for every system.

Supported policy profiles:

- `xp_legacy`: custom user shell, HKCU/HKLM registry policies, interface
  restrictions, and best-effort process supervision.
- `win7_srp`: legacy shell mode plus Software Restriction Policies when
  available.
- `win10_applocker`: legacy shell mode plus AppLocker when available.
- `win10_shelllauncher`: Shell Launcher enhancement on Enterprise, Education,
  and IoT editions where supported.
- `home_fallback`: custom shell and registry-policy fallback for Home editions,
  with reduced security guarantees.

## Security Model

The locked account must be a standard Windows user. The administrator account is
used only for installation, configuration, and recovery. A Windows administrator
can always recover the machine; the project is designed to restrict the
operator, not to defend against local administrators.

Allowed operator action:

- Use the single configured desktop executable.
- Lock the session or switch user with `Win+L`.

Blocked or restricted operator actions:

- Explorer desktop, Start menu, taskbar, Run dialog, Control Panel, Settings,
  Task Manager, command prompt, PowerShell where available, Registry Editor,
  and common Windows shell escape paths.
- Closing the allowed application as a way to reach the desktop.
- Changing kiosk configuration without the kiosk administrator password.

## Components

### Kiosk Launcher

`KioskLauncher` is the shell process for the operator account. It replaces
`explorer.exe` for that user. On sign-in it starts first, launches the configured
allowed application, watches its process, and restarts it when it exits.

The launcher stays resident while the operator session is active. If the
allowed application exits normally, crashes, or is closed by the user, the
launcher restarts it after a short configurable delay.

### Configuration Store

Configuration is stored in a local JSON file protected by Windows file
permissions where possible. It contains:

- path to the allowed executable;
- operator username or SID;
- selected policy profile;
- restart delay;
- admin password hash and salt;
- emergency restore metadata;
- feature flags for version-specific policy layers.

The password is never stored in plaintext. Modern systems use a strong
hashing/KDF option available in Python. Older Windows compatibility may require
a conservative hash fallback documented in the implementation.

### Admin Unlock

The launcher exposes a hidden administrator unlock prompt through a configurable
hotkey. After successful password entry, an administrator can:

- temporarily unlock the desktop and start `explorer.exe`;
- change the allowed executable path;
- enable or disable kiosk mode for the operator account;
- change the kiosk administrator password;
- restore the previous shell and policy configuration;
- view current status and logs.

Failed unlock attempts are delayed and logged to slow password guessing.

### Policy Engine

The policy engine detects Windows version, edition, architecture, and available
policy features. It then applies the strongest supported non-destructive policy
profile for the target machine.

Policy application must be reversible. Before writing registry or policy
settings, the tool saves the previous values needed for rollback.

### Restore Tool

The restore path must work outside the kiosk launcher from a Windows
administrator account. It restores the original shell, removes or reverts kiosk
policy values created by this project, and leaves unrelated services and startup
entries untouched.

## Safety Rules

- Never stop, disable, or delete existing services.
- Never remove existing startup entries.
- Never apply policies to all users unless the selected policy mechanism
  requires a machine-level setting and the effect is clearly documented.
- Prefer per-user settings for the operator account.
- Always create backups before changing shell or policy values.
- Always provide a restore command that can be run from an administrator
  account.
- Do not block `Win+L`.

## First Implementation Scope

The first Python version should implement a safe local project skeleton:

- launcher/watchdog logic;
- JSON configuration;
- password hashing and admin unlock flow;
- dry-run policy detection;
- generated install/restore plan;
- Windows registry writing only behind an explicit administrator command.

Actual policy application should be separated from normal launcher execution so
running `main.py` in PyCharm cannot accidentally lock the current laptop.

## Testing

Tests should cover:

- config load/save and validation;
- password hashing and verification;
- process restart decision logic;
- Windows version/profile selection from mocked system information;
- restore metadata generation;
- dry-run policy plan output.

Manual testing of real policy application must be done on a dedicated test
machine or virtual machine, not on the development laptop.
```

## docs\superpowers\specs\2026-06-16-urgent-kiosk-lockdown-design.md

```markdown
# Urgent Kiosk Lockdown Fix Design

## Goal

Fix the tested kiosk shell so the operator session cannot reach the Windows desktop, Start menu, Run, Explorer, task switching, Task Manager shortcuts, command shells, or arbitrary applications, while still leaving Windows services, drivers, system processes, existing startup items, and the main user account untouched.

## Root Causes Found

- The launcher still uses the old flat `kiosk_config.json` by default instead of the required `config/kiosk.json` shape.
- The test/run shell can be launched inside an existing Windows desktop session, but it does not remove the current operator's desktop Explorer window first, so Start and taskbar remain visible.
- The keyboard filter blocks raw Win key presses, but `Win+L` is simulated through `LockWorkStation`; this is acceptable as a fallback but should be explicit and should block Win combinations without logging keystrokes.
- The allowed application foreground control exists, but the watchdog starts the process without waiting for its input window and without start options from config.
- The admin unlock dialog and Windows admin credential check exist, but the UI needs clearer modal behavior and admin actions for changing the allowed app path from the kiosk session.

## Design

`config/kiosk.json` becomes the primary configuration file. If it is missing, startup creates a default template that runs `C:\Windows\System32\notepad.exe`. The loader keeps backwards compatibility with the old flat config while normalizing to the new nested model: `operatorUser`, `allowedApplication`, `kiosk`, and `logging`.

`KioskLauncher` validates the allowed exe path before launch and creates a watchdog command using the configured path, arguments, working directory, restart behavior, foreground behavior, and maximized setting. It never stores Windows admin credentials.

`ShellWindow` is a fullscreen background layer, not a topmost foreground owner. During operator-mode startup it starts `WindowsSessionLockdown`, which is allowed to close only the current user's desktop Explorer shell during a test launch. It does not touch services, drivers, foreign processes, or startup. After successful admin authentication, restrictions can be released and `explorer.exe` can be started temporarily.

`WindowsKeyFilter` blocks Win, Win+R, Win+E, Win+X, Win+S, Ctrl+Esc, Alt+Tab, Alt+Esc, and Alt+F4 inside operator mode only. It does not record or log keystrokes. `Win+L` remains available by calling `LockWorkStation` when the hook consumes the Win chord.

`AppWindowController` waits for the allowed app window, restores it if minimized, optionally maximizes it, sets it topmost briefly, brings it foreground, and releases shell topmost state. The kiosk window remains fullscreen background and must not cover the app.

Configurator and Restore continue to require elevated Windows administrator rights for real apply. CLI commands that change allowed app configuration require admin rights when configured to enforce Windows writes, and config writes go through the new model.

## Testing

Add unit tests for:

- creating `config/kiosk.json` default template;
- reading allowed app path from nested config;
- refusing missing allowed exe;
- watchdog command arguments and working directory;
- session lockdown operation boundaries;
- keyboard filter blocking required shortcuts while allowing `Win+L`;
- admin unlock modal flow and admin session actions;
- foreground window restore/maximize path;
- Configurator/Restore denial message.

Manual tests remain limited to a separate non-admin operator account. No real policy/shell changes are applied to the main account during automated verification.
```

## docs\superpowers\specs\2026-06-16-windows-admin-session-design.md

```markdown
# Windows Admin Session Design

## Goal

Strengthen the kiosk shell so the operator cannot reach the Windows desktop until a local Windows administrator successfully authenticates, while keeping the allowed application usable above the kiosk background layer.

## Authentication

Windows administrator unlock uses local Win32 authentication only. The password is passed directly to `LogonUserW`, never stored in config, logs, registry, files, or temporary files. Authentication returns a structured result:

- `success` when credentials are valid and the token belongs to local Administrators;
- `bad_credentials` when Windows rejects the username/password;
- `not_admin` when credentials are valid but the account is not a local administrator;
- `windows_error` when a Win32/API call fails unexpectedly.

Handles are closed after every attempt. API error codes are logged without password, token, or secret data.

## Shell And Window Behavior

`KioskLauncher` starts as the operator shell instead of `explorer.exe`. The kiosk window remains fullscreen and blocks the desktop, Start menu, taskbar and shell escape routes. It does not use topmost over the allowed app. The allowed application window is restored and placed topmost above the kiosk shell on every watchdog tick. If it is minimized, the shell shows a restore button. If it exits or crashes, watchdog restarts it.

## Admin Session

After successful Windows administrator authentication, the kiosk enters a time-limited administrative session. During this session the administrator can unlock the desktop, start `explorer.exe`, stop watchdog, change the allowed application path, run restore/undo, inspect status, or return to kiosk mode. If the session times out, kiosk restrictions are restored unless kiosk mode was explicitly disabled.

## Administrative Rights

Configurator and RestoreTool require the current Windows process to run as an elevated administrator before any apply-mode system action. If the process is not elevated/admin, they return the message:

`Отказано в доступе. Для выполнения действия требуются права администратора Windows.`

No partial install, restore, rollback, shell change, HKLM change, or policy change is allowed after this denial.

## Compatibility

The implementation keeps XP-compatible Win32 mechanisms where possible: `LogonUserW`, token membership check against the Administrators SID, explicit handle close, and fallback error reporting. Modern APIs are not required for authentication.

## Logging

The log records admin dialog open, successful Windows admin authentication, denial reasons, Windows API errors, explorer launch, temporary unlock, return to kiosk mode, allowed application start/restart, and apply/restore denials. The log must never contain passwords, password hashes, full tokens, or secret authentication data.
```

## docs\TESTING.md

```markdown
# Тестирование

Тестирование на ноутбуке разрешено только через отдельную локальную учетную запись оператора без прав администратора. Основную учетную запись не используйте.

## Автотесты

```powershell
python -m unittest discover -s tests -v
```

## Диагностический лог тестирования

Перед ручным тестом создайте маркер диагностической сессии:

```powershell
python main.py log-path --config .\config\kiosk.json
```

Команда печатает путь к JSONL-журналу и `Session`. По умолчанию для текущего конфига это:

```text
C:\ProgramData\Kiosk\Logs\kiosk.log
```

Во время работы киоска туда пишутся события launcher, watchdog, session-lockdown, keyboard-filter, админ-разблокировки, изменения статуса разрешенного приложения и restore/recover. Пароли, token/secret/password/hash/salt-поля и обычный ввод текста не записываются. Для анализа конкретного запуска фильтруйте строки по `session_id`.

Автотесты проверяют:

- CLI и запуск оболочки из PyCharm без аргументов;
- хранение пароля как соль + PBKDF2-HMAC-SHA256;
- структурированную проверку локального администратора Windows через изолированный backend;
- различение неверного пароля, неадминской учетной записи и Windows/API ошибки;
- watchdog, перезапуск приложения и отсутствие второго экземпляра;
- разворачивание разрешенного приложения поверх фонового KioskLauncher;
- time-limited admin-сессию после успешной Windows-admin авторизации;
- блокировку Win/Alt/Ctrl-комбинаций с сохранением `Win+L`;
- уведомление о свернутом приложении и кнопку `Развернуть приложение` при `restoreIfMinimized: false`;
- dry-run install/restore, backup и safe rollback;
- backend `--apply` через fake-runner: shell пишется только в HKU оператора, политики применяются только значениями реестра, оператор-администратор отклоняется;
- диагностический JSONL-лог: session id, PID, путь из конфигурации, ротация, fallback и маскировка чувствительных полей;
- структуру `/src`, `/config`, `/scripts`, `/docs`;
- запрет операций остановки служб, драйверов, процессов и автозагрузки.

## Безопасный ручной порядок

1. `.\scripts\test-lab-setup.ps1 -UserName "KioskOperator"`.
2. `.\scripts\create-operator-user.ps1 -UserName "KioskOperator"` без `-Apply`.
3. `.\scripts\create-operator-user.ps1 -UserName "KioskOperator" -Apply`.
4. `python main.py status --config kiosk_config.json`.
5. `.\scripts\install.ps1 -StateDir .\.kiosk-state` без `-Apply`.
6. `.\scripts\restore.ps1 -StateDir .\.kiosk-state` без `-Apply`.
7. `.\scripts\install.ps1 -Apply`.
8. Войти в `KioskOperator`.
9. Проверить оболочку и разрешенное приложение.
10. Выйти через `Win+L` в административную УЗ.
11. `.\scripts\restore.ps1 -Apply`.
12. После любого прерванного ручного теста выполнить `python main.py recover-desktop`.

## Обязательные кейсы

- операторская учетная запись не входит в `Administrators`;
- KioskLauncher стартует вместо обычного рабочего стола;
- разрешенное приложение открывается первым и поверх оболочки;
- KioskLauncher остается фоновым защитным слоем и не перекрывает разрешенное приложение;
- закрытое или упавшее приложение перезапускается;
- повторный запуск `RezhimKioska.exe` с той же конфигурацией не создает второе окно киоска;
- `C:\Windows\System32\notepad.exe` на Windows 11 не плодит новые экземпляры, даже если фактический процесс открыт из `WindowsApps`;
- при сворачивании приложения появляется уведомление и кнопка `Развернуть приложение`; автоматическое восстановление включается только через `restoreIfMinimized: true`;
- `Win+L` блокирует экран или дает сменить пользователя;
- `Alt+Tab`, `Alt+F4`, `Ctrl+Esc`, `Ctrl+Shift+Esc` ограничены;
- Task Manager, Run, CMD, Regedit, Control Panel и Settings ограничены политиками оператора насколько это возможно в редакции Windows;
- службы Windows не остановлены;
- автозагрузка не очищена;
- ввод локального администратора Windows открывает admin-сессию;
- `explorer.exe` запускается только отдельным действием после успешной авторизации;
- ввод неверного пароля показывает отказ `Неверное имя пользователя или пароль`;
- ввод обычного пользователя показывает отказ `Указанная учётная запись не является администратором Windows`;
- окно разблокировки содержит только локальный логин и пароль без поля домена/компьютера;
- неверные попытки входа дают задержку;
- смена пути разрешенного `.exe` работает через защищенный административный режим или CLI;
- смена пароля киоска создает новый salt/hash;
- Restore возвращает `explorer.exe`;
- запуск без прав администратора не применяет частичные изменения.
- Configurator и RestoreTool без elevated admin-прав показывают `Отказано в доступе. Для выполнения действия требуются права администратора Windows.`
- `ensure_operator_user` отклоняет отсутствующую операторскую УЗ и операторскую УЗ, входящую в локальную группу Administrators.

## Что не проверять на основной УЗ

Не меняйте shell основной учетной записи, не применяйте политики к ней и не тестируйте блокировки клавиш как основной пользователь.
## Срочная ручная проверка

Проверять только на отдельной локальной операторской УЗ без прав администратора.

1. Запустить `python main.py launch --config .\config\kiosk.json`.
2. Убедиться, что `config/kiosk.json` создан, если отсутствовал.
3. Проверить, что `notepad.exe` открыт поверх фонового окна киоска.
4. Нажать `Win`, `Win+R`, `Win+E`, `Win+X`, `Win+S`, `Win+D`, `Win+M`, `Win+Tab`, `Ctrl+Esc`, `Alt+Tab`, `Alt+Esc`, `Alt+F4`: Пуск/Проводник/Выполнить/переключение не должны открываться.
5. Нажать `Win+L`: экран должен заблокироваться.
6. Закрыть разрешённое приложение: watchdog должен перезапустить его.
7. Нажать `Разблокировать`: должно открыться окно локального пользователя и пароля.
8. Ввести неверный пароль: должно быть сообщение отказа.
9. Ввести обычного пользователя: должен быть отказ, что УЗ не администратор Windows.
10. Ввести администратора Windows: должна открыться ограниченная админ-сессия.
11. Нажать `Открыть рабочий стол`: только после этого запускается `explorer.exe`.
12. Проверить, что службы Windows не остановлены и автозагрузка не очищена.
13. После теста выполнить `python main.py recover-desktop`.

## Дополнительные обязательные проверки 2026-06-16

Эти проверки выполняются только в отдельной операторской учетной записи без прав администратора. Основную учетную запись не переводить в киоск.

1. В операторском режиме нажать `Alt+Tab`: переключатель окон Windows не должен открыться.
2. В операторском режиме нажать `Ctrl+Alt+Tab`: закрепленный переключатель окон Windows не должен открыться.
3. После блокировки `Alt+Tab` набрать текст в разрешенном приложении: обычный ввод должен работать.
4. Нажать `Разблокировать` и набрать логин локального администратора Windows и пароль: ввод в полях должен работать.
5. Ввести неверный пароль: должен быть отказ без сохранения пароля в логах.
6. Ввести учетную запись без прав администратора: должен быть отказ, что учетная запись не является администратором Windows.
7. Ввести учетную запись из локальной группы `Administrators`: должна открыться admin-сессия, а keyboard hook временно отключиться.
8. В admin-сессии проверить, что `Alt+Tab` и `Ctrl+Alt+Tab` временно разрешены.
9. Нажать `Вернуться в киоск` или дождаться таймаута admin-сессии: блокировка `Alt+Tab` и `Ctrl+Alt+Tab` должна снова включиться.
10. Проверить `Win+L`: блокировка экрана/смена пользователя должна работать всегда.
11. Закрыть разрешенное приложение: watchdog должен запустить только один новый экземпляр.
12. Свернуть разрешенное приложение: оно должно восстановиться на экран без запуска второго экземпляра.
13. Запустить Restore/Undo из административной учетной записи: `explorer.exe`, Пуск, панель задач и обычное поведение `Alt+Tab` должны вернуться.
14. После Restore/Undo проверить, что keyboard hook больше не активен, службы Windows не остановлены, драйверы не изменены, автозагрузка не очищена.



```

## kiosk_config.json

```json
{
  "admin_password_algorithm": "pbkdf2_hmac_sha256",
  "admin_password_hash": "45b368b5750e79458631f0feb28d8875aa6b5afba4e9abafa3df80ad6fa5ec05",
  "admin_password_iterations": 200000,
  "admin_password_salt": "ed1d688a83255fc47036d9ddcf271392",
  "app_path": "C:\\Windows\\System32\\notepad.exe",
  "feature_flags": {},
  "operator_user": "Operator",
  "policy_profile": "auto",
  "restart_delay_seconds": 2,
  "restore_metadata": {}
}
```

## main.py

```python
# -*- coding: utf-8 -*-

import argparse
import os
import sys

from python_kiosk.admin_actions import AdminActions
from python_kiosk.config import (
    DEFAULT_CONFIG_PATH,
    KioskConfig,
    ensure_default_config,
    load_config,
    save_config,
)
from python_kiosk.configurator import Configurator
from python_kiosk.launcher import KioskLauncher
from python_kiosk.platform_detect import detect_windows_info, select_policy_profile
from python_kiosk.policy_plan import build_install_plan, build_restore_plan
from python_kiosk.restore_tool import RestoreTool
from python_kiosk.security import hash_password
from python_kiosk.session_lockdown import recover_current_desktop
from python_kiosk.shell_ui import run_shell
from python_kiosk.single_instance import SingleInstanceGuard
from python_kiosk.logging_service import configured_log_path, create_configured_logger


class _HelpCatchingParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)

    def format_help(self):
        text = argparse.ArgumentParser.format_help(self)
        return (
            text.replace("usage:", "использование:")
            .replace("positional arguments:", "команды:")
            .replace("options:", "параметры:")
            .replace("show this help message and exit", "показать эту справку и выйти")
        )


def build_parser():
    default_config_path = resolve_default_config_path()
    parser = _HelpCatchingParser(
        prog="PythonKiosk",
        add_help=False,
        description=(
            "Подготовка и запуск оболочки киоска Windows. "
            "Без --apply команды работают в dry-run и не меняют политики Windows."
        ),
    )
    parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    subparsers = parser.add_subparsers(dest="command", title="команды")

    init_parser = subparsers.add_parser(
        "init",
        help="создать конфигурацию киоска",
        add_help=False,
    )
    init_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    init_parser.add_argument("--app-path", required=True, metavar="ПУТЬ")
    init_parser.add_argument("--operator", required=True, metavar="ПОЛЬЗОВАТЕЛЬ")
    init_parser.add_argument("--password", required=False, default="", metavar="ПАРОЛЬ")
    init_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")
    init_parser.add_argument("--restart-delay", type=int, default=2, metavar="СЕКУНДЫ")

    plan_parser = subparsers.add_parser(
        "plan",
        help="показать пробный план установки",
        add_help=False,
    )
    plan_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    plan_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")

    restore_parser = subparsers.add_parser(
        "restore-plan",
        help="показать пробный план восстановления",
        add_help=False,
    )
    restore_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    restore_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")

    install_parser = subparsers.add_parser(
        "install",
        help="подготовить или применить установку киоска",
        add_help=False,
    )
    install_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    install_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")
    install_parser.add_argument("--state-dir", default=None, metavar="КАТАЛОГ")
    install_parser.add_argument(
        "--apply",
        action="store_true",
        help="применить изменения Windows; без флага выполняется dry-run",
    )

    restore_apply_parser = subparsers.add_parser(
        "restore",
        help="подготовить или применить восстановление киоска",
        add_help=False,
    )
    restore_apply_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    restore_apply_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")
    restore_apply_parser.add_argument("--state-dir", default=None, metavar="КАТАЛОГ")
    restore_apply_parser.add_argument(
        "--apply",
        action="store_true",
        help="восстановить shell и политики; без флага выполняется dry-run",
    )

    check_parser = subparsers.add_parser(
        "check-password",
        help="проверить legacy-пароль администратора киоска",
        add_help=False,
    )
    check_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    check_parser.add_argument("--password", required=True, metavar="ПАРОЛЬ")
    check_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")

    launch_parser = subparsers.add_parser(
        "launch",
        help="запустить оболочку киоска",
        add_help=False,
    )
    launch_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    launch_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")
    launch_parser.add_argument(
        "--headless",
        action="store_true",
        help="запустить надзор без окна оболочки Tkinter",
    )

    recover_parser = subparsers.add_parser(
        "recover-desktop",
        help="показать рабочий стол текущей сессии после теста",
        add_help=False,
    )
    recover_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")

    log_path_parser = subparsers.add_parser(
        "log-path",
        help="показать путь диагностического журнала и записать тестовый маркер",
        add_help=False,
    )
    log_path_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    log_path_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")

    set_app_parser = subparsers.add_parser(
        "set-app",
        help="изменить путь к разрешённому приложению",
        add_help=False,
    )
    set_app_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    set_app_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")
    set_app_parser.add_argument("--app-path", required=True, metavar="ПУТЬ")

    change_password_parser = subparsers.add_parser(
        "change-password",
        help="сменить legacy-пароль администратора киоска",
        add_help=False,
    )
    change_password_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    change_password_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")
    change_password_parser.add_argument("--password", required=True, metavar="ПАРОЛЬ")

    status_parser = subparsers.add_parser(
        "status",
        help="показать текущую конфигурацию и выбранный профиль",
        add_help=False,
    )
    status_parser.add_argument("-h", "--help", action="help", help="показать эту справку и выйти")
    status_parser.add_argument("--config", default=default_config_path, metavar="ФАЙЛ")

    return parser


def resolve_default_config_path():
    if os.path.isabs(DEFAULT_CONFIG_PATH):
        return DEFAULT_CONFIG_PATH

    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidates = [os.path.join(exe_dir, DEFAULT_CONFIG_PATH)]
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            candidates.append(os.path.join(bundle_dir, DEFAULT_CONFIG_PATH))
        candidates.append(os.path.abspath(DEFAULT_CONFIG_PATH))
    else:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.abspath(DEFAULT_CONFIG_PATH),
            os.path.join(project_dir, DEFAULT_CONFIG_PATH),
        ]

    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def build_launcher_shell_command(config_path):
    config_path = os.path.abspath(config_path)
    if getattr(sys, "frozen", False):
        return '"{0}" launch --config "{1}"'.format(
            os.path.abspath(sys.executable),
            config_path,
        )
    return '"{0}" "{1}" launch --config "{2}"'.format(
        os.path.abspath(sys.executable),
        os.path.abspath(__file__),
        config_path,
    )


def _emit(stdout, text):
    stdout(text)


def _create_config(args):
    if args.password:
        password = hash_password(args.password)
        return KioskConfig(
            app_path=args.app_path,
            operator_user=args.operator,
            admin_password_hash=password["hash"],
            admin_password_salt=password["salt"],
            admin_password_algorithm=password["algorithm"],
            admin_password_iterations=password["iterations"],
            restart_delay_seconds=args.restart_delay,
        )
    return KioskConfig(
        app_path=args.app_path,
        operator_user=args.operator,
        restart_delay_seconds=args.restart_delay,
    )


def _load_config_for_command(path):
    return load_config(path, create_if_missing=True)


def main(argv=None, stdout=None, shell_runner=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    stdout = stdout or print
    shell_runner = shell_runner or run_shell
    parser = build_parser()

    if not argv:
        argv = ["launch"]

    try:
        args = parser.parse_args(argv)
    except ValueError as error:
        _emit(stdout, str(error))
        _emit(stdout, parser.format_help())
        return 2

    if args.command == "init":
        config = _create_config(args)
        save_config(config, args.config)
        _emit(stdout, "Конфигурация сохранена: {0}".format(args.config))
        return 0

    if args.command == "plan":
        config = _load_config_for_command(args.config)
        plan = build_install_plan(config, detect_windows_info())
        _emit(stdout, plan.to_text())
        return 0

    if args.command == "restore-plan":
        config = _load_config_for_command(args.config)
        plan = build_restore_plan(config)
        _emit(stdout, plan.to_text())
        return 0

    if args.command == "install":
        config = _load_config_for_command(args.config)
        try:
            result = Configurator(
                state_dir=args.state_dir,
                launcher_command=build_launcher_shell_command(args.config),
            ).install(
                config,
                apply=args.apply,
            )
        except PermissionError as error:
            _emit(stdout, str(error))
            return 1
        _emit(stdout, result.plan.to_text())
        _emit(stdout, "Backup: {0}".format(result.backup_path))
        return 0

    if args.command == "restore":
        config = _load_config_for_command(args.config)
        try:
            result = RestoreTool(state_dir=args.state_dir).restore(
                config,
                apply=args.apply,
            )
        except PermissionError as error:
            _emit(stdout, str(error))
            return 1
        _emit(stdout, result.plan.to_text())
        return 0

    if args.command == "check-password":
        config = _load_config_for_command(args.config)
        launcher = KioskLauncher(config)
        if launcher.verify_admin_password(args.password):
            _emit(stdout, "Пароль принят")
            return 0
        _emit(stdout, "Пароль отклонён")
        return 1

    if args.command == "launch":
        ensure_default_config(args.config)
        config = load_config(args.config)
        guard = SingleInstanceGuard.for_operator(config.operator_user)
        with guard:
            if not guard.acquired:
                _emit(stdout, "Киоск уже запущен для этой конфигурации.")
                return 0
            launcher = KioskLauncher(config, config_path=args.config)
            if args.headless:
                launcher.run()
            else:
                shell_runner(launcher)
        return 0

    if args.command == "recover-desktop":
        result = recover_current_desktop()
        _emit(stdout, "Рабочий стол текущей сессии восстановлен.")
        _emit(stdout, "Explorer: {0}".format("started" if result.get("started_explorer") else "not-started"))
        return 0

    if args.command == "log-path":
        config = _load_config_for_command(args.config)
        logger = create_configured_logger(config)
        log_path = configured_log_path(config)
        logger.info(
            "diagnostic.log_ready",
            operator=config.operator_user,
            app_path=config.app_path,
            config_path=os.path.abspath(args.config),
            log_path=log_path,
        )
        _emit(stdout, "Log: {0}".format(log_path))
        _emit(stdout, "Session: {0}".format(logger.session_id))
        return 0

    if args.command == "set-app":
        try:
            AdminActions(args.config).set_allowed_app_path(args.app_path)
        except (PermissionError, ValueError) as error:
            _emit(stdout, str(error))
            return 1
        _emit(stdout, "Путь разрешённого приложения сохранён: {0}".format(args.app_path))
        return 0

    if args.command == "change-password":
        try:
            AdminActions(args.config).change_kiosk_admin_password(args.password)
        except (PermissionError, ValueError) as error:
            _emit(stdout, str(error))
            return 1
        _emit(stdout, "Legacy-пароль администратора киоска изменён")
        return 0

    if args.command == "status":
        config = _load_config_for_command(args.config)
        windows_info = detect_windows_info()
        profile = (
            config.policy_profile
            if config.policy_profile != "auto"
            else select_policy_profile(windows_info)
        )
        _emit(stdout, "Оператор: {0}".format(config.operator_user))
        _emit(stdout, "Разрешённое приложение: {0}".format(config.app_path))
        _emit(stdout, "Профиль политики: {0}".format(profile))
        _emit(stdout, "Windows: {0}".format(windows_info.product_name or "не определено"))
        return 0

    _emit(stdout, parser.format_help())
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## python_kiosk\__init__.py

```python
"""PythonKiosk package."""

```

## python_kiosk\admin_actions.py

```python
# -*- coding: utf-8 -*-

import os

from python_kiosk.config import load_config, save_config
from python_kiosk.logging_service import KioskLogger
from python_kiosk.security import hash_password
from python_kiosk.system_backend import (
    ADMIN_RIGHTS_REQUIRED_MESSAGE,
    WindowsSystemBackend,
)


class AdminActions(object):
    def __init__(self, config_path, logger=None, backend=None):
        self.config_path = config_path
        self.logger = logger or KioskLogger()
        self.backend = backend or WindowsSystemBackend()

    def _require_admin(self, action):
        if not self.backend.is_admin():
            self.logger.warning("admin.action_denied", action=action)
            raise PermissionError(ADMIN_RIGHTS_REQUIRED_MESSAGE)

    def set_allowed_app_path(self, app_path):
        self._require_admin("set_allowed_app_path")
        if not os.path.isfile(app_path):
            raise ValueError(
                "Разрешённое приложение не найдено: {0}".format(app_path)
            )
        config = load_config(self.config_path)
        previous = config.app_path
        config.app_path = app_path
        save_config(config, self.config_path)
        self.logger.info("admin.set_app_path", previous=previous, current=app_path)

    def change_kiosk_admin_password(self, new_password):
        self._require_admin("change_kiosk_admin_password")
        if not new_password:
            raise ValueError("Новый пароль обязателен.")
        config = load_config(self.config_path)
        record = hash_password(new_password)
        config.admin_password_hash = record["hash"]
        config.admin_password_salt = record["salt"]
        config.admin_password_algorithm = record["algorithm"]
        config.admin_password_iterations = record["iterations"]
        save_config(config, self.config_path)
        self.logger.info("admin.change_password")
```

## python_kiosk\admin_session.py

```python
# -*- coding: utf-8 -*-

import time

from python_kiosk.logging_service import KioskLogger


DEFAULT_ADMIN_SESSION_TIMEOUT_SECONDS = 300


class AdminSession(object):
    def __init__(
        self,
        timeout_seconds=DEFAULT_ADMIN_SESSION_TIMEOUT_SECONDS,
        time_func=None,
        logger=None,
    ):
        self.timeout_seconds = int(timeout_seconds)
        self.time_func = time_func or time.time
        self.logger = logger or KioskLogger()
        self.active = False
        self.username = ""
        self.expires_at = None
        self.desktop_unlocked = False
        self.kiosk_disabled = False
        self._timeout_logged = False

    def start(self, username):
        self.active = True
        self.username = username
        self.expires_at = self.time_func() + self.timeout_seconds
        self.desktop_unlocked = False
        self.kiosk_disabled = False
        self._timeout_logged = False
        self.logger.info("admin.session_started", **self.to_log_data())

    def is_active(self):
        if not self.active:
            return False
        if self.kiosk_disabled:
            return True
        if self.time_func() <= self.expires_at:
            return True
        self.active = False
        if not self._timeout_logged:
            self.logger.warning("admin.session_timeout", **self.to_log_data())
            self._timeout_logged = True
        return False

    def close(self, reason="manual"):
        was_active = self.active
        self.active = False
        self.desktop_unlocked = False
        if was_active:
            self.logger.info("admin.session_closed", reason=reason, **self.to_log_data())

    def mark_desktop_unlocked(self):
        self.desktop_unlocked = True
        self.logger.info("admin.desktop_unlocked", **self.to_log_data())

    def disable_kiosk(self):
        self.kiosk_disabled = True
        self.logger.warning("admin.kiosk_disabled", **self.to_log_data())

    def to_log_data(self):
        return {
            "username": self.username,
            "expires_at": self.expires_at,
            "desktop_unlocked": self.desktop_unlocked,
            "kiosk_disabled": self.kiosk_disabled,
        }
```

## python_kiosk\backup_store.py

```python
# -*- coding: utf-8 -*-

import json
import os
import time


class BackupStore(object):
    def __init__(self, state_dir):
        self.state_dir = state_dir

    def create_backup(self, config, plan, allow_user_fallback=True):
        state_dirs = [self.state_dir]
        if allow_user_fallback:
            for fallback_dir in user_state_dirs():
                if _normalized_path(fallback_dir) not in [
                    _normalized_path(path) for path in state_dirs
                ]:
                    state_dirs.append(fallback_dir)

        last_error = None
        for state_dir in state_dirs:
            try:
                return self._write_backup(state_dir, config, plan)
            except PermissionError as error:
                last_error = error
                continue
        if last_error is not None:
            raise last_error
        return self._write_backup(self.state_dir, config, plan)

    def _write_backup(self, state_dir, config, plan):
        directory = os.path.join(state_dir, "backups")
        if not os.path.isdir(directory):
            os.makedirs(directory)
        filename = "backup-{0}.json".format(time.strftime("%Y%m%d-%H%M%S"))
        path = os.path.join(directory, filename)
        data = {
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "operator_user": config.operator_user,
            "app_path": config.app_path,
            "restore_shell": "explorer.exe",
            "plan": plan.to_dict(),
        }
        with open(path, "w", encoding="utf-8") as backup_file:
            json.dump(data, backup_file, indent=2, ensure_ascii=False, sort_keys=True)
            backup_file.write("\n")
        return path


def default_state_dir():
    base = os.environ.get("PROGRAMDATA") or os.path.expanduser("~")
    return os.path.join(base, "PythonKiosk")


def user_state_dirs():
    bases = [
        os.environ.get("LOCALAPPDATA"),
        os.environ.get("TEMP"),
        os.path.expanduser("~"),
    ]
    return [os.path.join(base, "PythonKiosk") for base in bases if base]


def _normalized_path(path):
    return os.path.normcase(os.path.abspath(path or ""))
```

## python_kiosk\config.py

```python
# -*- coding: utf-8 -*-

import json
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "kiosk.json")
DEFAULT_ALLOWED_APP_PATH = r"C:\Windows\System32\notepad.exe"
DEFAULT_OPERATOR_USER = "KioskOperator"
DEFAULT_POLICY_PROFILE = "auto"
DEFAULT_RESTART_DELAY_SECONDS = 2
DEFAULT_PASSWORD_ALGORITHM = "pbkdf2_hmac_sha256"
DEFAULT_PASSWORD_ITERATIONS = 200000
DEFAULT_LOG_DIRECTORY = r"C:\ProgramData\Kiosk\Logs"


class AllowedApplicationConfig(object):
    def __init__(
        self,
        path=DEFAULT_ALLOWED_APP_PATH,
        arguments="",
        working_directory=r"C:\Windows\System32",
        restart_on_exit=True,
        bring_to_front=True,
        bring_existing_to_front=True,
        single_instance=True,
        restore_if_minimized=False,
        start_maximized=False,
        restart_delay_ms=2000,
    ):
        self.path = path
        self.arguments = arguments or ""
        self.working_directory = working_directory or ""
        self.restart_on_exit = bool(restart_on_exit)
        self.bring_to_front = bool(bring_to_front)
        self.bring_existing_to_front = bool(bring_existing_to_front)
        self.single_instance = bool(single_instance)
        self.restore_if_minimized = bool(restore_if_minimized)
        self.start_maximized = bool(start_maximized)
        self.restart_delay_ms = int(restart_delay_ms)

    def to_dict(self):
        return {
            "path": self.path,
            "arguments": self.arguments,
            "workingDirectory": self.working_directory,
            "restartOnExit": self.restart_on_exit,
            "bringToFront": self.bring_to_front,
            "bringExistingToFront": self.bring_existing_to_front,
            "singleInstance": self.single_instance,
            "restoreIfMinimized": self.restore_if_minimized,
            "startMaximized": self.start_maximized,
            "restartDelayMs": self.restart_delay_ms,
        }

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            path=data.get("path", DEFAULT_ALLOWED_APP_PATH),
            arguments=data.get("arguments", ""),
            working_directory=data.get("workingDirectory", data.get("working_directory", "")),
            restart_on_exit=data.get("restartOnExit", data.get("restart_on_exit", True)),
            bring_to_front=data.get("bringToFront", data.get("bring_to_front", True)),
            bring_existing_to_front=data.get(
                "bringExistingToFront",
                data.get("bring_existing_to_front", True),
            ),
            single_instance=data.get("singleInstance", data.get("single_instance", True)),
            restore_if_minimized=data.get(
                "restoreIfMinimized",
                data.get("restore_if_minimized", False),
            ),
            start_maximized=data.get("startMaximized", data.get("start_maximized", False)),
            restart_delay_ms=data.get("restartDelayMs", data.get("restart_delay_ms", 2000)),
        )

    def command(self):
        command = [self.path]
        if self.arguments:
            command.extend(_split_windows_arguments(self.arguments))
        return command


def _split_windows_arguments(arguments):
    try:
        import shlex

        return shlex.split(arguments, posix=False)
    except ValueError:
        return [arguments]


class KioskConfig(object):
    def __init__(
        self,
        app_path=None,
        operator_user=DEFAULT_OPERATOR_USER,
        admin_password_hash="",
        admin_password_salt="",
        admin_password_algorithm=DEFAULT_PASSWORD_ALGORITHM,
        admin_password_iterations=DEFAULT_PASSWORD_ITERATIONS,
        policy_profile=DEFAULT_POLICY_PROFILE,
        restart_delay_seconds=DEFAULT_RESTART_DELAY_SECONDS,
        restore_metadata=None,
        feature_flags=None,
        allowed_application=None,
        kiosk=None,
        testing=None,
        logging=None,
    ):
        self.allowed_application = allowed_application or AllowedApplicationConfig(
            path=app_path or DEFAULT_ALLOWED_APP_PATH
        )
        if app_path is not None:
            self.allowed_application.path = app_path
        self.operator_user = operator_user or DEFAULT_OPERATOR_USER
        self.admin_password_hash = admin_password_hash or ""
        self.admin_password_salt = admin_password_salt or ""
        self.admin_password_algorithm = admin_password_algorithm or DEFAULT_PASSWORD_ALGORITHM
        self.admin_password_iterations = int(
            admin_password_iterations or DEFAULT_PASSWORD_ITERATIONS
        )
        self.policy_profile = policy_profile or DEFAULT_POLICY_PROFILE
        if restart_delay_seconds is None:
            restart_delay_seconds = DEFAULT_RESTART_DELAY_SECONDS
        self.restart_delay_seconds = int(restart_delay_seconds)
        self.restore_metadata = restore_metadata or {}
        self.feature_flags = feature_flags or {}
        self.kiosk = _default_kiosk()
        self.kiosk.update(kiosk or {})
        self.testing = _default_testing()
        self.testing.update(testing or {})
        self.logging = _default_logging()
        self.logging.update(logging or {})

    @property
    def app_path(self):
        return self.allowed_application.path

    @app_path.setter
    def app_path(self, value):
        self.allowed_application.path = value

    def validate(self, require_existing_app=False):
        if not self.app_path:
            raise ValueError("app_path обязателен")
        if not self.operator_user:
            raise ValueError("operator_user обязателен")
        if int(self.restart_delay_seconds) <= 0:
            raise ValueError("restart_delay_seconds должен быть положительным")
        if int(self.kiosk.get("adminSessionTimeoutSeconds", 0)) <= 0:
            raise ValueError("adminSessionTimeoutSeconds должен быть положительным")
        if require_existing_app and not os.path.isfile(self.app_path):
            raise ValueError(
                "Разрешённое приложение не найдено: {0}".format(self.app_path)
            )

    def to_dict(self):
        data = {
            "operatorUser": self.operator_user,
            "allowedApplication": self.allowed_application.to_dict(),
            "kiosk": self.kiosk,
            "testing": self.testing,
            "logging": self.logging,
            "policyProfile": self.policy_profile,
            "restartDelaySeconds": int(self.restart_delay_seconds),
            "restoreMetadata": self.restore_metadata,
            "featureFlags": self.feature_flags,
        }
        if self.admin_password_hash or self.admin_password_salt:
            data.update(
                {
                    "admin_password_hash": self.admin_password_hash,
                    "admin_password_salt": self.admin_password_salt,
                    "admin_password_algorithm": self.admin_password_algorithm,
                    "admin_password_iterations": int(self.admin_password_iterations),
                }
            )
        return data

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        if "allowedApplication" in data:
            return cls(
                operator_user=data.get("operatorUser", data.get("operator_user", DEFAULT_OPERATOR_USER)),
                allowed_application=AllowedApplicationConfig.from_dict(
                    data.get("allowedApplication")
                ),
                kiosk=data.get("kiosk") or {},
                testing=data.get("testing") or {},
                logging=data.get("logging") or {},
                policy_profile=data.get("policyProfile", data.get("policy_profile", DEFAULT_POLICY_PROFILE)),
                restart_delay_seconds=data.get(
                    "restartDelaySeconds",
                    data.get("restart_delay_seconds", DEFAULT_RESTART_DELAY_SECONDS),
                ),
                restore_metadata=data.get("restoreMetadata", data.get("restore_metadata") or {}),
                feature_flags=data.get("featureFlags", data.get("feature_flags") or {}),
                admin_password_hash=data.get("admin_password_hash", ""),
                admin_password_salt=data.get("admin_password_salt", ""),
                admin_password_algorithm=data.get(
                    "admin_password_algorithm", DEFAULT_PASSWORD_ALGORITHM
                ),
                admin_password_iterations=data.get(
                    "admin_password_iterations", DEFAULT_PASSWORD_ITERATIONS
                ),
            )
        return cls(
            app_path=data.get("app_path", DEFAULT_ALLOWED_APP_PATH),
            operator_user=data.get("operator_user", DEFAULT_OPERATOR_USER),
            admin_password_hash=data.get("admin_password_hash", ""),
            admin_password_salt=data.get("admin_password_salt", ""),
            admin_password_algorithm=data.get(
                "admin_password_algorithm", DEFAULT_PASSWORD_ALGORITHM
            ),
            admin_password_iterations=data.get(
                "admin_password_iterations", DEFAULT_PASSWORD_ITERATIONS
            ),
            policy_profile=data.get("policy_profile", DEFAULT_POLICY_PROFILE),
            restart_delay_seconds=data.get(
                "restart_delay_seconds", DEFAULT_RESTART_DELAY_SECONDS
            ),
            restore_metadata=data.get("restore_metadata") or {},
            feature_flags=data.get("feature_flags") or {},
        )


def _default_kiosk():
    return {
        "blockDesktop": True,
        "disableStartMenu": True,
        "disableExplorer": True,
        "allowWinL": True,
        "blockWinKey": True,
        "adminSessionTimeoutSeconds": 300,
    }


def _default_testing():
    return {
        "requireBackupBeforeTest": True,
        "restoreAfterTest": True,
        "testOnlySeparateOperatorUser": True,
    }


def _default_logging():
    return {
        "logDirectory": DEFAULT_LOG_DIRECTORY,
        "level": "Info",
    }


def build_default_config():
    return KioskConfig(
        app_path=DEFAULT_ALLOWED_APP_PATH,
        operator_user=DEFAULT_OPERATOR_USER,
        allowed_application=AllowedApplicationConfig(),
        kiosk=_default_kiosk(),
        testing=_default_testing(),
        logging=_default_logging(),
    )


def ensure_default_config(path=DEFAULT_CONFIG_PATH):
    if os.path.exists(path):
        return path
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    save_config(build_default_config(), path)
    return path


def load_config(path, create_if_missing=False):
    if create_if_missing:
        ensure_default_config(path)
    with open(path, "r", encoding="utf-8") as config_file:
        data = json.load(config_file)
    config = KioskConfig.from_dict(data)
    config.validate()
    return config


def save_config(config, path):
    config.validate()
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8") as config_file:
        json.dump(config.to_dict(), config_file, ensure_ascii=False, indent=2, sort_keys=True)
        config_file.write("\n")
```

## python_kiosk\configurator.py

```python
# -*- coding: utf-8 -*-

from python_kiosk.backup_store import BackupStore, default_state_dir
from python_kiosk.logging_service import KioskLogger
from python_kiosk.platform_detect import detect_windows_info
from python_kiosk.policy_engine import PolicyEngine
from python_kiosk.system_backend import (
    ADMIN_RIGHTS_REQUIRED_MESSAGE,
    WindowsSystemBackend,
)


class ConfigurationResult(object):
    def __init__(self, plan, backup_path, applied):
        self.plan = plan
        self.backup_path = backup_path
        self.applied = bool(applied)


class Configurator(object):
    def __init__(
        self,
        backend=None,
        state_dir=None,
        logger=None,
        policy_engine=None,
        windows_info=None,
        launcher_command=None,
    ):
        self.backend = backend or WindowsSystemBackend()
        self.state_dir = state_dir or default_state_dir()
        self.logger = logger or KioskLogger()
        self.policy_engine = policy_engine or PolicyEngine()
        self.windows_info = windows_info
        self.launcher_command = launcher_command

    def install(self, config, apply=False):
        config.validate()
        if apply and not self.backend.is_admin():
            self.logger.error("install.denied", reason="admin rights required")
            raise PermissionError(ADMIN_RIGHTS_REQUIRED_MESSAGE)

        windows_info = self.windows_info or detect_windows_info()
        plan = self.policy_engine.build_install_plan(
            config,
            windows_info,
            dry_run=not apply,
            launcher_command=self.launcher_command,
        )
        backup_path = BackupStore(self.state_dir).create_backup(
            config,
            plan,
            allow_user_fallback=not apply,
        )
        self.logger.info(
            "install.plan",
            operator=config.operator_user,
            profile=plan.profile,
            dry_run=not apply,
            backup_path=backup_path,
        )

        if apply:
            try:
                for operation in plan.operations:
                    self.backend.apply_operation(operation)
                    self.logger.info("install.operation", operation=operation.name)
            except Exception as error:
                self.logger.error(
                    "install.failed",
                    operation=getattr(operation, "name", "unknown"),
                    error=str(error),
                )
                self._attempt_safe_rollback(config)
                raise

        return ConfigurationResult(plan, backup_path, applied=apply)

    def _attempt_safe_rollback(self, config):
        rollback_plan = self.policy_engine.build_restore_plan(config, dry_run=False)
        for operation in rollback_plan.operations:
            self.backend.apply_operation(operation)
            self.logger.warning("install.rollback_operation", operation=operation.name)
```

## python_kiosk\launcher.py

```python
# -*- coding: utf-8 -*-

import getpass
import inspect
import os

from python_kiosk.config import save_config
from python_kiosk.local_admin_auth import (
    AUTH_BAD_CREDENTIALS,
    AUTH_SUCCESS,
    AuthResult,
    LocalAdminAuthenticator,
    MESSAGE_BAD_CREDENTIALS,
)
from python_kiosk.logging_service import create_configured_logger
from python_kiosk.process_watchdog import ProcessWatchdog, windows_allowed_process_running
from python_kiosk.window_control import AppWindowController
from python_kiosk.security import verify_password


class KioskLauncher(object):
    def __init__(
        self,
        config,
        config_path=None,
        watchdog_class=ProcessWatchdog,
        admin_authenticator=None,
        logger=None,
    ):
        self.config = config
        self.config_path = config_path
        self.watchdog_class = watchdog_class
        self.admin_authenticator = admin_authenticator or LocalAdminAuthenticator()
        self.logger = logger or create_configured_logger(config)
        self.app_window_controller = AppWindowController()
        self.logger.info(
            "launcher.initialized",
            operator=config.operator_user,
            app_path=config.app_path,
            config_path=config_path or "",
        )

    def _password_record(self):
        return {
            "algorithm": self.config.admin_password_algorithm,
            "iterations": self.config.admin_password_iterations,
            "salt": self.config.admin_password_salt,
            "hash": self.config.admin_password_hash,
        }

    def verify_admin_password(self, password):
        if not self.config.admin_password_hash or not self.config.admin_password_salt:
            return False
        return verify_password(password, self._password_record())

    def verify_admin_credentials(self, username, password):
        return self.verify_admin_credentials_result(username, password).success

    def verify_admin_credentials_result(self, username, password):
        if hasattr(self.admin_authenticator, "authenticate_result"):
            return self.admin_authenticator.authenticate_result(username, password)
        if self.admin_authenticator.authenticate(username, password):
            return AuthResult(
                AUTH_SUCCESS,
                username=username,
                domain="",
                message="Доступ разрешён.",
            )
        return AuthResult(
            AUTH_BAD_CREDENTIALS,
            username=username,
            domain="",
            message=MESSAGE_BAD_CREDENTIALS,
        )

    def create_watchdog(self):
        if not os.path.isfile(self.config.app_path):
            self.logger.error("launcher.allowed_app_missing", app_path=self.config.app_path)
            raise ValueError(
                "Разрешенное приложение не найдено: {0}".format(
                    self.config.app_path
                )
            )
        allowed_app = self.config.allowed_application
        restart_delay_seconds = float(
            getattr(allowed_app, "restart_delay_ms", self.config.restart_delay_seconds * 1000)
        ) / 1000.0
        kwargs = {
            "restart_delay_seconds": restart_delay_seconds,
            "process_running": lambda: windows_allowed_process_running(self.config.app_path),
            "working_directory": allowed_app.working_directory or None,
            "restart_on_exit": allowed_app.restart_on_exit,
            "wait_for_input_idle": True,
            "start_maximized": allowed_app.start_maximized,
            "single_instance": allowed_app.single_instance,
            "bring_existing_to_front": (
                lambda: self.app_window_controller.ensure_foreground(
                    self.config.app_path,
                    wait=False,
                    start_maximized=allowed_app.start_maximized,
                )
                if allowed_app.bring_existing_to_front
                else False
            ),
        }
        if self._watchdog_accepts_logger():
            kwargs["logger"] = self.logger
        self.logger.info(
            "launcher.watchdog_created",
            app_path=self.config.app_path,
            restart_on_exit=allowed_app.restart_on_exit,
            single_instance=allowed_app.single_instance,
            restore_if_minimized=allowed_app.restore_if_minimized,
        )
        return self.watchdog_class(allowed_app.command(), **kwargs)

    def set_allowed_application_path(self, app_path):
        if not os.path.isfile(app_path):
            raise ValueError(
                "Р Р°Р·СЂРµС€РµРЅРЅРѕРµ РїСЂРёР»РѕР¶РµРЅРёРµ РЅРµ РЅР°Р№РґРµРЅРѕ: {0}".format(
                    app_path
                )
            )
        previous = self.config.app_path
        self.config.app_path = app_path
        if self.config_path:
            save_config(self.config, self.config_path)
        self.logger.info("admin.set_app_path", previous=previous, current=app_path)
        return True

    def _watchdog_accepts_logger(self):
        try:
            parameters = inspect.signature(self.watchdog_class).parameters.values()
        except (TypeError, ValueError):
            return False
        for parameter in parameters:
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                return True
            if parameter.name == "logger":
                return True
        return False

    def run(self):
        self.logger.info("launcher.run_forever_started")
        watchdog = self.create_watchdog()
        try:
            watchdog.run_forever()
        finally:
            self.logger.info("launcher.run_forever_stopped")


def prompt_admin_unlock(launcher, prompt="Kiosk admin password: "):
    password = getpass.getpass(prompt)
    return launcher.verify_admin_password(password)
```

## python_kiosk\local_admin_auth.py

```python
# -*- coding: utf-8 -*-

import os


AUTH_SUCCESS = "success"
AUTH_BAD_CREDENTIALS = "bad_credentials"
AUTH_NOT_ADMIN = "not_admin"
AUTH_WINDOWS_ERROR = "windows_error"

ERROR_LOGON_FAILURE = 1326
ERROR_ACCOUNT_RESTRICTION = 1327
ERROR_INVALID_LOGON_HOURS = 1328
ERROR_INVALID_WORKSTATION = 1329
ERROR_PASSWORD_EXPIRED = 1330
ERROR_ACCOUNT_DISABLED = 1331
ERROR_ACCOUNT_EXPIRED = 1793
ERROR_ACCOUNT_LOCKED_OUT = 1909
LOGON_DENIED_ERRORS = set(
    [
        ERROR_LOGON_FAILURE,
        ERROR_ACCOUNT_RESTRICTION,
        ERROR_INVALID_LOGON_HOURS,
        ERROR_INVALID_WORKSTATION,
        ERROR_PASSWORD_EXPIRED,
        ERROR_ACCOUNT_DISABLED,
        ERROR_ACCOUNT_EXPIRED,
        ERROR_ACCOUNT_LOCKED_OUT,
    ]
)

MESSAGE_BAD_CREDENTIALS = "Отказано в доступе. Неверное имя пользователя или пароль."
MESSAGE_NOT_ADMIN = (
    "Отказано в доступе. Указанная учётная запись не является администратором Windows."
)
MESSAGE_WINDOWS_ERROR = "Отказано в доступе. ошибка Windows/API: {0}"


class WindowsAuthError(Exception):
    def __init__(self, api_name, error_code=None, message=None):
        self.api_name = api_name
        self.error_code = error_code
        text = message or "{0} failed".format(api_name)
        if error_code is not None:
            text = "{0} failed with code {1}".format(api_name, error_code)
        Exception.__init__(self, text)


class AuthResult(object):
    def __init__(self, code, username="", domain="", message="", error_code=None):
        self.code = code
        self.username = username
        self.domain = domain
        self.message = message
        self.error_code = error_code

    @property
    def success(self):
        return self.code == AUTH_SUCCESS

    def to_log_data(self):
        data = {
            "code": self.code,
            "username": self.username,
            "domain": self.domain,
        }
        if self.error_code is not None:
            data["error_code"] = self.error_code
        return data


def parse_windows_account_name(account_name):
    account_name = (account_name or "").strip()
    if "\\" in account_name:
        domain, username = account_name.split("\\", 1)
        return domain or ".", username.strip()
    return ".", account_name


class WindowsAuthBackend(object):
    LOGON32_LOGON_INTERACTIVE = 2
    LOGON32_PROVIDER_DEFAULT = 0
    SECURITY_BUILTIN_DOMAIN_RID = 0x00000020
    DOMAIN_ALIAS_RID_ADMINS = 0x00000220

    def logon_user(self, username, domain, password):
        if os.name != "nt":
            return None

        import ctypes
        from ctypes import wintypes

        token = wintypes.HANDLE()
        ok = ctypes.windll.advapi32.LogonUserW(
            username,
            domain,
            password,
            self.LOGON32_LOGON_INTERACTIVE,
            self.LOGON32_PROVIDER_DEFAULT,
            ctypes.byref(token),
        )
        if not ok:
            error_code = ctypes.GetLastError()
            if error_code in LOGON_DENIED_ERRORS:
                return None
            raise WindowsAuthError("LogonUserW", error_code)
        return token

    def is_local_admin(self, token):
        if os.name != "nt" or not token:
            return False

        import ctypes
        from ctypes import wintypes

        class SID_IDENTIFIER_AUTHORITY(ctypes.Structure):
            _fields_ = [("Value", ctypes.c_ubyte * 6)]

        nt_authority = SID_IDENTIFIER_AUTHORITY((0, 0, 0, 0, 0, 5))
        admin_sid = ctypes.c_void_p()
        ok = ctypes.windll.advapi32.AllocateAndInitializeSid(
            ctypes.byref(nt_authority),
            2,
            self.SECURITY_BUILTIN_DOMAIN_RID,
            self.DOMAIN_ALIAS_RID_ADMINS,
            0,
            0,
            0,
            0,
            0,
            0,
            ctypes.byref(admin_sid),
        )
        if not ok:
            raise WindowsAuthError("AllocateAndInitializeSid", ctypes.GetLastError())

        try:
            is_member = wintypes.BOOL()
            ok = ctypes.windll.advapi32.CheckTokenMembership(
                token,
                admin_sid,
                ctypes.byref(is_member),
            )
            if not ok:
                raise WindowsAuthError("CheckTokenMembership", ctypes.GetLastError())
            return bool(is_member.value)
        finally:
            ctypes.windll.advapi32.FreeSid(admin_sid)

    def close_token(self, token):
        if os.name != "nt" or not token:
            return

        import ctypes

        ctypes.windll.kernel32.CloseHandle(token)


class LocalAdminAuthenticator(object):
    def __init__(self, backend=None):
        self.backend = backend or WindowsAuthBackend()

    def authenticate(self, account_name, password):
        return self.authenticate_result(account_name, password).success

    def authenticate_result(self, account_name, password):
        domain, username = parse_windows_account_name(account_name)
        if not username or not password:
            return AuthResult(
                AUTH_BAD_CREDENTIALS,
                username=username,
                domain=domain,
                message=MESSAGE_BAD_CREDENTIALS,
            )

        try:
            token = self.backend.logon_user(username, domain, password)
        except Exception as error:
            return self._windows_error_result(username, domain, error)
        if not token:
            return AuthResult(
                AUTH_BAD_CREDENTIALS,
                username=username,
                domain=domain,
                message=MESSAGE_BAD_CREDENTIALS,
            )

        try:
            if self.backend.is_local_admin(token):
                return AuthResult(
                    AUTH_SUCCESS,
                    username=username,
                    domain=domain,
                    message="Доступ разрешён.",
                )
            return AuthResult(
                AUTH_NOT_ADMIN,
                username=username,
                domain=domain,
                message=MESSAGE_NOT_ADMIN,
            )
        except Exception as error:
            return self._windows_error_result(username, domain, error)
        finally:
            self.backend.close_token(token)

    def _windows_error_result(self, username, domain, error):
        error_code = getattr(error, "error_code", None)
        details = "код {0}".format(error_code) if error_code is not None else str(error)
        return AuthResult(
            AUTH_WINDOWS_ERROR,
            username=username,
            domain=domain,
            message=MESSAGE_WINDOWS_ERROR.format(details),
            error_code=error_code,
        )
```

## python_kiosk\logging_service.py

```python
# -*- coding: utf-8 -*-

import json
import os
import time
import uuid


SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
    "authorization",
    "hash",
    "salt",
)

REDACTED = "***REDACTED***"


class KioskLogger(object):
    def __init__(
        self,
        log_path=None,
        max_bytes=5 * 1024 * 1024,
        backup_count=5,
        session_id=None,
    ):
        self.log_path = log_path or default_log_path()
        self.max_bytes = int(max_bytes)
        self.backup_count = int(backup_count)
        self.session_id = session_id or os.environ.get("PYTHONKIOSK_SESSION_ID") or uuid.uuid4().hex

    def info(self, event, **data):
        self._write("info", event, data)

    def warning(self, event, **data):
        self._write("warning", event, data)

    def error(self, event, **data):
        self._write("error", event, data)

    def _write(self, level, event, data):
        row = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "session_id": self.session_id,
            "process_id": os.getpid(),
            "level": level,
            "event": event,
            "data": sanitize_log_data(data),
        }
        try:
            self._write_to_path(self.log_path, row)
        except OSError:
            fallback_path = fallback_log_path()
            if os.path.abspath(fallback_path) == os.path.abspath(self.log_path):
                return False
            try:
                self._write_to_path(fallback_path, row)
            except OSError:
                return False
        return True

    def _write_to_path(self, path, row):
        directory = os.path.dirname(os.path.abspath(path))
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)
        self._rotate_if_needed(path)
        with open(os.path.abspath(path), "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            log_file.write("\n")

    def _rotate_if_needed(self, path):
        path = os.path.abspath(path)
        if self.max_bytes <= 0 or self.backup_count <= 0:
            return
        if not os.path.exists(path):
            return
        try:
            if os.path.getsize(path) < self.max_bytes:
                return
            for index in range(self.backup_count - 1, 0, -1):
                source = "{0}.{1}".format(path, index)
                target = "{0}.{1}".format(path, index + 1)
                if os.path.exists(source):
                    if os.path.exists(target):
                        os.remove(target)
                    os.rename(source, target)
            first_backup = "{0}.1".format(path)
            if os.path.exists(first_backup):
                os.remove(first_backup)
            os.rename(path, first_backup)
        except OSError:
            return


def default_log_path():
    override_path = environment_log_path()
    if override_path:
        return override_path
    base = os.environ.get("PROGRAMDATA") or os.path.expanduser("~")
    return os.path.join(base, "PythonKiosk", "logs", "kiosk.log")


def fallback_log_path():
    return os.path.join(os.path.expanduser("~"), "PythonKiosk", "logs", "kiosk.log")


def configured_log_path(config, filename="kiosk.log"):
    override_path = environment_log_path()
    if override_path:
        if filename == os.path.basename(override_path):
            return override_path
        return os.path.join(os.path.dirname(override_path), filename)
    logging_config = getattr(config, "logging", {}) or {}
    directory = logging_config.get("logDirectory") or logging_config.get("log_directory")
    directory = directory or os.path.dirname(default_log_path())
    return os.path.join(os.path.expandvars(directory), filename)


def environment_log_path():
    override_path = os.environ.get("PYTHONKIOSK_LOG_PATH")
    if not override_path:
        return None
    return os.path.expandvars(os.path.expanduser(override_path))


def create_configured_logger(config, session_id=None, filename="kiosk.log"):
    return KioskLogger(
        log_path=configured_log_path(config, filename=filename),
        session_id=session_id,
    )


def sanitize_log_data(value, key_name=""):
    if _is_sensitive_key(key_name):
        return REDACTED
    if isinstance(value, dict):
        return dict(
            (key, sanitize_log_data(item, key))
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return [sanitize_log_data(item, key_name) for item in value]
    return value


def _is_sensitive_key(key_name):
    normalized = str(key_name or "").lower()
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)
```

## python_kiosk\platform_detect.py

```python
import platform
import subprocess


class WindowsInfo(object):
    def __init__(self, major, minor, build, edition, product_name=""):
        self.major = int(major)
        self.minor = int(minor)
        self.build = int(build)
        self.edition = edition or ""
        self.product_name = product_name or ""

    @property
    def edition_lower(self):
        return (self.edition + " " + self.product_name).lower()


def _parse_version(version_text):
    parts = (version_text or "0.0.0").split(".")
    while len(parts) < 3:
        parts.append("0")
    numbers = []
    for part in parts[:3]:
        try:
            numbers.append(int(part))
        except ValueError:
            numbers.append(0)
    return numbers[0], numbers[1], numbers[2]


def _read_windows_caption():
    try:
        process = subprocess.Popen(
            ["wmic", "os", "get", "Caption", "/value"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = process.communicate()
    except (OSError, ValueError):
        return ""
    try:
        text = stdout.decode("utf-8", "ignore")
    except AttributeError:
        text = stdout
    for line in text.splitlines():
        if line.startswith("Caption="):
            return line.split("=", 1)[1].strip()
    return ""


def detect_windows_info():
    version = platform.version()
    major, minor, build = _parse_version(version)
    caption = _read_windows_caption()
    edition = caption.replace("Microsoft Windows", "").strip()
    return WindowsInfo(
        major=major,
        minor=minor,
        build=build,
        edition=edition,
        product_name=caption,
    )


def select_policy_profile(info):
    edition = info.edition_lower

    if info.major <= 5:
        return "xp_legacy"

    if "home" in edition:
        return "home_fallback"

    if info.major == 6 and info.minor <= 1:
        return "win7_srp"

    if info.major >= 10:
        if (
            "enterprise" in edition
            or "education" in edition
            or "iot" in edition
        ):
            return "win10_shelllauncher"
        return "win10_applocker"

    return "win7_srp"
```

## python_kiosk\policy_engine.py

```python
# -*- coding: utf-8 -*-

import json
import os

from python_kiosk.platform_detect import select_policy_profile


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PROFILES_PATH = os.path.join(PROJECT_ROOT, "config", "policy-profiles.json")


class PolicyOperation(object):
    def __init__(self, name, description, reversible=True, data=None):
        self.name = name
        self.description = description
        self.reversible = bool(reversible)
        self.data = data or {}

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "reversible": self.reversible,
            "data": self.data,
        }


class PolicyExecutionPlan(object):
    def __init__(self, title, profile, operations, dry_run=True):
        self.title = title
        self.profile = profile
        self.operations = list(operations)
        self.dry_run = bool(dry_run)

    def to_text(self):
        mode = "dry-run" if self.dry_run else "apply"
        lines = [
            self.title,
            "Профиль: {0}".format(self.profile),
            "Режим: {0}".format(mode),
        ]
        for operation in self.operations:
            lines.append("- {0}: {1}".format(operation.name, operation.description))
        return "\n".join(lines)

    def to_dict(self):
        return {
            "title": self.title,
            "profile": self.profile,
            "dry_run": self.dry_run,
            "operations": [operation.to_dict() for operation in self.operations],
        }


class PolicyEngine(object):
    @staticmethod
    def load_profiles(path=None):
        path = path or DEFAULT_PROFILES_PATH
        with open(path, "r", encoding="utf-8") as profiles_file:
            return json.load(profiles_file)

    def build_install_plan(self, config, windows_info, dry_run=True, launcher_command=None):
        config.validate()
        profile = (
            config.policy_profile
            if config.policy_profile != "auto"
            else select_policy_profile(windows_info)
        )
        operations = [
            PolicyOperation(
                "create_backup",
                "Сохранить текущую shell-оболочку оператора и значения политик перед изменениями.",
                data={"operator_user": config.operator_user},
            ),
            PolicyOperation(
                "ensure_operator_user",
                "Создать или проверить отдельную локальную учетную запись оператора без прав администратора.",
                data={"operator_user": config.operator_user},
            ),
            PolicyOperation(
                "set_operator_shell",
                "Назначить KioskLauncher shell-оболочкой только для учетной записи оператора.",
                data={
                    "operator_user": config.operator_user,
                    "shell_command": launcher_command or "KioskLauncher.exe launch",
                },
            ),
            PolicyOperation(
                "apply_hkcu_operator_policies",
                "Ограничить Run, Task Manager, командные оболочки, Registry Editor, Control Panel и обходные пути Explorer для оператора.",
                data={"operator_user": config.operator_user},
            ),
            PolicyOperation(
                "allow_fixed_executable",
                "Разрешить только настроенный фиксированный путь Win32-приложения в выбранном профиле.",
                data={"app_path": config.app_path},
            ),
            PolicyOperation(
                "preserve_services_drivers_startup",
                "Не останавливать службы, драйверы, системные процессы и существующие записи автозагрузки.",
                reversible=True,
            ),
        ]
        operations.extend(self._profile_operations(profile, config))
        return PolicyExecutionPlan(
            "План установки PythonKiosk",
            profile,
            operations,
            dry_run=dry_run,
        )

    def build_restore_plan(self, config, dry_run=True):
        config.validate()
        operations = [
            PolicyOperation(
                "load_backup",
                "Загрузить backup-метаданные, созданные перед применением политик киоска.",
                data={"operator_user": config.operator_user},
            ),
            PolicyOperation(
                "restore_operator_shell",
                "Вернуть explorer.exe как shell-оболочку учетной записи оператора.",
                data={"shell": "explorer.exe", "operator_user": config.operator_user},
            ),
            PolicyOperation(
                "restore_operator_policies",
                "Откатить только значения политик, созданные PythonKiosk.",
                data={"operator_user": config.operator_user},
            ),
            PolicyOperation(
                "preserve_services_drivers_startup",
                "Оставить службы, драйверы, системные процессы и автозагрузку без изменений.",
            ),
        ]
        return PolicyExecutionPlan(
            "План восстановления PythonKiosk",
            "restore",
            operations,
            dry_run=dry_run,
        )

    def _profile_operations(self, profile, config):
        if profile == "xp_legacy":
            return [
                PolicyOperation(
                    "apply_xp_legacy_registry_policy",
                    "Использовать shell replacement и политики реестра, доступные на Windows XP.",
                )
            ]
        if profile == "win7_srp":
            return [
                PolicyOperation(
                    "prepare_srp_rules",
                    "Подготовить Software Restriction Policies для launcher и фиксированного пути приложения.",
                    data={"app_path": config.app_path},
                )
            ]
        if profile == "win10_applocker":
            return [
                PolicyOperation(
                    "prepare_applocker_rules",
                    "Подготовить правила AppLocker для .exe там, где редакция Windows поддерживает enforcement.",
                    data={"app_path": config.app_path},
                )
            ]
        if profile == "win10_shelllauncher":
            return [
                PolicyOperation(
                    "prepare_shelllauncher_config",
                    "Подготовить конфигурацию Shell Launcher там, где редакция Windows это поддерживает.",
                )
            ]
        return [
            PolicyOperation(
                "apply_home_fallback_policy",
                "Использовать shell replacement и пользовательские политики реестра с пониженной гарантией на Home-редакциях.",
            )
        ]
```

## python_kiosk\policy_plan.py

```python
# -*- coding: utf-8 -*-

from python_kiosk.platform_detect import select_policy_profile


class PolicyStep(object):
    def __init__(self, title, detail):
        self.title = title
        self.detail = detail

    def to_text(self):
        return "- {0}: {1}".format(self.title, self.detail)


class PolicyPlan(object):
    def __init__(self, title, steps, dry_run=True):
        self.title = title
        self.steps = steps
        self.dry_run = dry_run

    def to_text(self):
        lines = [
            self.title,
            "Режим: dry-run" if self.dry_run else "Режим: применение",
        ]
        lines.extend(step.to_text() for step in self.steps)
        return "\n".join(lines)


def _common_install_steps(config, profile):
    return [
        PolicyStep(
            "Сохранить текущую оболочку",
            "Сохранить текущую оболочку и значения политик для {0}".format(
                config.operator_user
            ),
        ),
        PolicyStep(
            "Назначить оболочку {0} на KioskLauncher".format(config.operator_user),
            "KioskLauncher запускается раньше explorer.exe и контролирует {0}".format(
                config.app_path
            ),
        ),
        PolicyStep(
            "Отключить диспетчер задач",
            "Применить пользовательскую политику для учетной записи оператора, где это поддерживается",
        ),
        PolicyStep(
            "Ограничить пути выхода из оболочки",
            "Отключить Выполнить, Панель управления, редактор реестра, командные оболочки и интерфейс Explorer",
        ),
        PolicyStep(
            "Оставить Win+L доступным",
            "Не применять политики, которые блокируют экран блокировки или смену пользователя",
        ),
        PolicyStep(
            "Не отключать службы",
            "Не трогать существующие службы, драйверы и фоновые процессы",
        ),
        PolicyStep(
            "Не удалять элементы автозагрузки",
            "Не трогать существующие элементы автозагрузки",
        ),
        PolicyStep(
            "Выбранный профиль политик",
            profile,
        ),
    ]


def _profile_steps(profile):
    if profile == "xp_legacy":
        return [
            PolicyStep(
                "Legacy-ограничения XP",
                "Использовать только пользовательскую оболочку и совместимые политики реестра",
            )
        ]
    if profile == "win7_srp":
        return [
            PolicyStep(
                "Software Restriction Policies",
                "Добавить разрешающие правила для kiosk launcher и настроенного исполняемого файла",
            )
        ]
    if profile == "win10_applocker":
        return [
            PolicyStep(
                "AppLocker",
                "Подготовить разрешающие правила исполняемых файлов там, где доступно применение AppLocker",
            )
        ]
    if profile == "win10_shelllauncher":
        return [
            PolicyStep(
                "Shell Launcher",
                "Использовать Windows Shell Launcher там, где редакция Windows это поддерживает",
            )
        ]
    return [
        PolicyStep(
            "Fallback для Home",
            "Использовать пользовательскую оболочку и политики реестра с ограниченными гарантиями",
        )
    ]


def build_install_plan(config, windows_info):
    config.validate()
    profile = (
        config.policy_profile
        if config.policy_profile != "auto"
        else select_policy_profile(windows_info)
    )
    steps = _common_install_steps(config, profile)
    steps.extend(_profile_steps(profile))
    return PolicyPlan("План установки PythonKiosk", steps, dry_run=True)


def build_restore_plan(config):
    config.validate()
    steps = [
        PolicyStep(
            "Вернуть оболочку {0} на explorer.exe".format(config.operator_user),
            "Использовать сохраненные данные восстановления, если они доступны",
        ),
        PolicyStep(
            "Удалить ограничения киоска",
            "Откатить значения политик, созданные PythonKiosk для учетной записи оператора",
        ),
        PolicyStep(
            "Не удалять элементы автозагрузки",
            "Элементы автозагрузки не входят в область восстановления киоска",
        ),
        PolicyStep(
            "Не останавливать службы",
            "Службы, драйверы и фоновые процессы остаются нетронутыми",
        ),
    ]
    return PolicyPlan("План восстановления PythonKiosk", steps, dry_run=True)
```

## python_kiosk\process_watchdog.py

```python
import subprocess
import time
import os
import csv


def _normalize_windows_path(path):
    return os.path.normcase(os.path.abspath(os.path.expandvars(path or ""))).rstrip("\\/")


def windows_process_name_running(executable_path, command_runner=None):
    image_name = os.path.basename(executable_path)
    if not image_name:
        return False
    if os.name != "nt" and command_runner is None:
        return False

    runner = command_runner or subprocess.check_output
    try:
        output = runner(
            ["tasklist", "/FI", "IMAGENAME eq {0}".format(image_name), "/NH"],
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return False

    if isinstance(output, bytes):
        output = output.decode("mbcs" if os.name == "nt" else "utf-8", "ignore")
    return image_name.lower() in output.lower()


def windows_process_ids_for_path(executable_path, command_runner=None):
    image_name = os.path.basename(executable_path)
    if not image_name:
        return set()
    if os.name != "nt" and command_runner is None:
        return set()

    runner = command_runner or subprocess.check_output
    try:
        output = runner(
            [
                "wmic",
                "process",
                "where",
                "name='{0}'".format(image_name),
                "get",
                "ProcessId,ExecutablePath",
                "/format:csv",
            ],
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return set()

    if isinstance(output, bytes):
        output = output.decode("mbcs" if os.name == "nt" else "utf-8", "ignore")

    expected_path = _normalize_windows_path(executable_path)
    pids = set()
    rows = [
        row
        for row in csv.reader(output.splitlines())
        if row and any(cell.strip() for cell in row)
    ]
    if not rows:
        return pids
    headers = [cell.strip().lstrip("\ufeff").lower() for cell in rows[0]]
    try:
        path_index = headers.index("executablepath")
        pid_index = headers.index("processid")
    except ValueError:
        return pids

    for row in rows[1:]:
        if len(row) <= max(path_index, pid_index):
            continue
        if _normalize_windows_path(row[path_index]) != expected_path:
            continue
        try:
            pids.add(int(row[pid_index]))
        except ValueError:
            pass
    return pids


def windows_process_ids_for_name(executable_path, command_runner=None):
    image_name = os.path.basename(executable_path)
    if not image_name:
        return set()
    if os.name != "nt" and command_runner is None:
        return set()

    runner = command_runner or subprocess.check_output
    try:
        output = runner(
            [
                "wmic",
                "process",
                "where",
                "name='{0}'".format(image_name),
                "get",
                "ProcessId",
                "/format:csv",
            ],
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return set()

    if isinstance(output, bytes):
        output = output.decode("mbcs" if os.name == "nt" else "utf-8", "ignore")

    pids = set()
    rows = [
        row
        for row in csv.reader(output.splitlines())
        if row and any(cell.strip() for cell in row)
    ]
    if not rows:
        return pids
    headers = [cell.strip().lstrip("\ufeff").lower() for cell in rows[0]]
    try:
        pid_index = headers.index("processid")
    except ValueError:
        return pids

    for row in rows[1:]:
        if len(row) <= pid_index:
            continue
        try:
            pids.add(int(row[pid_index]))
        except ValueError:
            pass
    return pids


def windows_process_path_running(executable_path, command_runner=None):
    return bool(windows_process_ids_for_path(executable_path, command_runner))


def windows_allowed_process_running(
    executable_path,
    path_command_runner=None,
    name_command_runner=None,
):
    if windows_process_path_running(executable_path, path_command_runner):
        return True
    return windows_process_name_running(executable_path, name_command_runner)


class ProcessWatchdog(object):
    def __init__(
        self,
        command,
        restart_delay_seconds=2,
        process_factory=None,
        process_running=None,
        logger=None,
        working_directory=None,
        restart_on_exit=True,
        wait_for_input_idle=True,
        input_idle_waiter=None,
        start_maximized=False,
        single_instance=True,
        bring_existing_to_front=None,
    ):
        self.command = list(command)
        self.restart_delay_seconds = float(restart_delay_seconds)
        self.process_factory = process_factory or subprocess.Popen
        self.process_running = process_running or (lambda: False)
        self.logger = logger
        self.working_directory = working_directory
        self.restart_on_exit = bool(restart_on_exit)
        self.wait_for_input_idle = bool(wait_for_input_idle)
        self.input_idle_waiter = input_idle_waiter or wait_for_process_input_idle
        self.start_maximized = bool(start_maximized)
        self.single_instance = bool(single_instance)
        self.bring_existing_to_front = bring_existing_to_front or (lambda: False)
        self.process = None
        self.stopped = False

    def _start(self):
        kwargs = {}
        if self.working_directory:
            kwargs["cwd"] = self.working_directory
        self.process = self.process_factory(self.command, **kwargs)
        if self.wait_for_input_idle:
            try:
                self.input_idle_waiter(self.process, 5)
            except Exception as error:
                self._log("warning", "watchdog.wait_input_idle_failed", error=str(error))

    def tick(self):
        if self.stopped:
            return "stopped"
        if self.process is None:
            if self.single_instance and self.process_running():
                self._bring_existing_to_front()
                return "running"
            self._start()
            self._log("info", "watchdog.started")
            return "started"

        if self.process.poll() is None:
            return "running"

        if self.single_instance and self.process_running():
            self._bring_existing_to_front()
            return "running"

        if not self.restart_on_exit:
            self._log("warning", "watchdog.exited")
            return "exited"

        self._start()
        self._log("warning", "watchdog.restarted")
        return "restarted"

    def _log(self, level, event, **extra):
        if self.logger is None:
            return
        log_method = getattr(self.logger, level)
        data = {
            "executable": self.command[0] if self.command else "",
            "argument_count": max(0, len(self.command) - 1),
        }
        data.update(extra)
        log_method(event, **data)

    def _bring_existing_to_front(self):
        try:
            self.bring_existing_to_front()
        except Exception as error:
            self._log("warning", "watchdog.bring_existing_failed", error=str(error))

    def run_forever(self):
        while True:
            self.tick()
            time.sleep(self.restart_delay_seconds)

    def stop(self):
        self.stopped = True


def wait_for_process_input_idle(process, timeout_seconds=5):
    if os.name != "nt":
        return False
    handle = getattr(process, "_handle", None)
    if not handle:
        return False
    import ctypes

    timeout_ms = int(float(timeout_seconds) * 1000)
    result = ctypes.windll.user32.WaitForInputIdle(handle, timeout_ms)
    return result == 0
```

## python_kiosk\restore_tool.py

```python
# -*- coding: utf-8 -*-

from python_kiosk.backup_store import default_state_dir
from python_kiosk.logging_service import KioskLogger
from python_kiosk.policy_engine import PolicyEngine
from python_kiosk.system_backend import (
    ADMIN_RIGHTS_REQUIRED_MESSAGE,
    WindowsSystemBackend,
)


class RestoreResult(object):
    def __init__(self, plan, applied):
        self.plan = plan
        self.applied = bool(applied)


class RestoreTool(object):
    def __init__(
        self,
        backend=None,
        state_dir=None,
        logger=None,
        policy_engine=None,
    ):
        self.backend = backend or WindowsSystemBackend()
        self.state_dir = state_dir or default_state_dir()
        self.logger = logger or KioskLogger()
        self.policy_engine = policy_engine or PolicyEngine()

    def restore(self, config, apply=False):
        config.validate()
        if apply and not self.backend.is_admin():
            self.logger.error("restore.denied", reason="admin rights required")
            raise PermissionError(ADMIN_RIGHTS_REQUIRED_MESSAGE)

        plan = self.policy_engine.build_restore_plan(config, dry_run=not apply)
        self.logger.info(
            "restore.plan",
            operator=config.operator_user,
            dry_run=not apply,
            state_dir=self.state_dir,
        )

        if apply:
            for operation in plan.operations:
                self.backend.apply_operation(operation)
                self.logger.info("restore.operation", operation=operation.name)

        return RestoreResult(plan, applied=apply)
```

## python_kiosk\security.py

```python
import binascii
import hashlib
import hmac
import os
import struct


DEFAULT_ITERATIONS = 200000
DEFAULT_ALGORITHM = "sha256"
SALT_BYTES = 16
KEY_BYTES = 32


class FailedAttemptLimiter(object):
    def __init__(
        self,
        threshold=3,
        base_delay_seconds=2,
        max_delay_seconds=30,
    ):
        self.threshold = int(threshold)
        self.base_delay_seconds = int(base_delay_seconds)
        self.max_delay_seconds = int(max_delay_seconds)
        self.failures = 0

    def record_failure(self):
        self.failures += 1
        if self.failures < self.threshold:
            return 0
        delay = self.base_delay_seconds * (self.failures - self.threshold + 1)
        return min(delay, self.max_delay_seconds)

    def record_success(self):
        self.failures = 0


def _to_bytes(value):
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8")


def _constant_time_compare(left, right):
    if hasattr(hmac, "compare_digest"):
        return hmac.compare_digest(left, right)
    if len(left) != len(right):
        return False
    result = 0
    for index in range(len(left)):
        result |= ord(left[index:index + 1]) ^ ord(right[index:index + 1])
    return result == 0


def _pbkdf2_fallback(password_bytes, salt_bytes, iterations, dklen, digest_name):
    digest_size = hashlib.new(digest_name).digest_size
    blocks = []
    block_count = int((dklen + digest_size - 1) / digest_size)
    for block_index in range(1, block_count + 1):
        initial = hmac.new(
            password_bytes,
            salt_bytes + struct.pack(">I", block_index),
            digest_name,
        ).digest()
        block = bytearray(initial)
        previous = initial
        for _ in range(iterations - 1):
            previous = hmac.new(password_bytes, previous, digest_name).digest()
            for offset in range(len(block)):
                block[offset] ^= previous[offset]
        blocks.append(bytes(block))
    return b"".join(blocks)[:dklen]


def derive_key(password, salt, iterations=DEFAULT_ITERATIONS):
    password_bytes = _to_bytes(password)
    salt_bytes = binascii.unhexlify(salt)
    if hasattr(hashlib, "pbkdf2_hmac"):
        return hashlib.pbkdf2_hmac(
            DEFAULT_ALGORITHM,
            password_bytes,
            salt_bytes,
            iterations,
            KEY_BYTES,
        )
    return _pbkdf2_fallback(
        password_bytes,
        salt_bytes,
        iterations,
        KEY_BYTES,
        DEFAULT_ALGORITHM,
    )


def hash_password(password, iterations=DEFAULT_ITERATIONS):
    salt = binascii.hexlify(os.urandom(SALT_BYTES)).decode("ascii")
    key = derive_key(password, salt, iterations)
    return {
        "algorithm": "pbkdf2_hmac_" + DEFAULT_ALGORITHM,
        "iterations": int(iterations),
        "salt": salt,
        "hash": binascii.hexlify(key).decode("ascii"),
    }


def verify_password(password, record):
    try:
        iterations = int(record["iterations"])
        expected_hash = record["hash"]
        actual_key = derive_key(password, record["salt"], iterations)
        actual_hash = binascii.hexlify(actual_key).decode("ascii")
    except (KeyError, TypeError, ValueError, binascii.Error):
        return False
    return _constant_time_compare(actual_hash, expected_hash)
```

## python_kiosk\session_lockdown.py

```python
# -*- coding: utf-8 -*-

import os
import subprocess

from python_kiosk.logging_service import KioskLogger


class WindowsSessionLockdown(object):
    def __init__(self, backend=None, logger=None, enabled=True):
        self.backend = backend or WindowsDesktopBackend()
        self.logger = logger or KioskLogger()
        self.enabled = bool(enabled)
        self.active = False

    def activate_operator_mode(self):
        if not self.enabled:
            return {"disabled": True}
        try:
            result = self.backend.lockdown_current_desktop_shell()
            self.active = True
            self.logger.info("session.lockdown_enabled", **result)
            return result
        except Exception as error:
            self.logger.warning("session.lockdown_failed", error=str(error))
            return {"error": str(error)}

    def release_operator_mode(self):
        if not self.active:
            return {"inactive": True}
        try:
            result = self.backend.restore_current_desktop_shell()
            self.active = False
            self.logger.info("session.lockdown_released", **result)
            return result
        except Exception as error:
            self.logger.warning("session.lockdown_release_failed", error=str(error))
            return {"error": str(error)}


class WindowsDesktopBackend(object):
    SW_HIDE = 0
    SW_SHOW = 5

    SHELL_WINDOW_CLASSES = (
        "Shell_TrayWnd",
        "Progman",
        "WorkerW",
    )

    def __init__(self):
        self.hidden_windows = []

    def lockdown_current_desktop_shell(self):
        if os.name != "nt":
            return {"platform": "non-windows", "hidden_windows": []}
        windows = self._find_shell_windows()
        for hwnd in windows:
            self._show_window(hwnd, self.SW_HIDE)
        shell_window = self._find_window("Shell_TrayWnd")
        self.hidden_windows = windows
        return {
            "shell_window": int(shell_window or 0),
            "hidden_windows": [int(hwnd) for hwnd in windows],
            "closed_explorer": False,
        }

    def restore_current_desktop_shell(self):
        if os.name != "nt":
            return {"platform": "non-windows", "restored_windows": []}
        if not self.hidden_windows:
            self.hidden_windows = self._find_shell_windows()
        restored = []
        for hwnd in self.hidden_windows:
            if self._is_window(hwnd):
                self._show_window(hwnd, self.SW_SHOW)
                restored.append(hwnd)
        self.hidden_windows = []
        return {"restored_windows": [int(hwnd) for hwnd in restored]}

    def _find_shell_windows(self):
        windows = []
        for class_name in self.SHELL_WINDOW_CLASSES:
            windows.extend(self._find_windows_by_class(class_name))
        unique = []
        for hwnd in windows:
            if hwnd and hwnd not in unique:
                unique.append(hwnd)
        return unique

    def _find_window(self, class_name):
        import ctypes

        return ctypes.windll.user32.FindWindowW(class_name, None)

    def _find_windows_by_class(self, class_name):
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        found = []
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def callback(hwnd, l_param):
            buffer = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buffer, 256)
            if buffer.value == class_name:
                found.append(hwnd)
            return True

        user32.EnumWindows(WNDENUMPROC(callback), 0)
        return found

    def _show_window(self, hwnd, command):
        import ctypes

        return bool(ctypes.windll.user32.ShowWindow(hwnd, command))

    def _is_window(self, hwnd):
        import ctypes

        return bool(ctypes.windll.user32.IsWindow(hwnd))


def recover_current_desktop(backend=None, process_factory=None):
    backend = backend or WindowsDesktopBackend()
    result = backend.restore_current_desktop_shell()
    started_explorer = False
    if os.name == "nt":
        factory = process_factory or subprocess.Popen
        try:
            factory(["explorer.exe"])
            started_explorer = True
        except Exception as error:
            result["explorer_error"] = str(error)
    result["started_explorer"] = started_explorer
    return result
```

## python_kiosk\shell_ui.py

```python
# -*- coding: utf-8 -*-

import subprocess
import os
import threading
import time

from python_kiosk.admin_session import AdminSession
from python_kiosk.logging_service import KioskLogger
from python_kiosk.local_admin_auth import (
    AUTH_BAD_CREDENTIALS,
    AUTH_SUCCESS,
    AuthResult,
    MESSAGE_BAD_CREDENTIALS,
)
from python_kiosk.session_lockdown import WindowsSessionLockdown
from python_kiosk.security import FailedAttemptLimiter
from python_kiosk.window_control import AppWindowController


WATCHDOG_INTERVAL_MS = 2000
FOCUS_GUARD_INTERVAL_MS = 500
DESIGN_WIDTH = 1440
DESIGN_HEIGHT = 900
SHELL_THEME = {
    "background": "#050505",
    "panel": "#111418",
    "panel2": "#171b20",
    "muted": "#9ca3af",
    "text": "#f4f6f8",
    "accent": "#38bdf8",
    "ok": "#22c55e",
    "danger": "#ef4444",
    "line": "#2b3138",
    "blue": "#0ea5e9",
}


def _app_name(app_path):
    name = os.path.basename(app_path)
    return name or app_path


def combine_windows_account_name(username, domain):
    username = (username or "").strip()
    domain = (domain or "").strip()
    if "\\" in username or not domain:
        return username
    return "{0}\\{1}".format(domain, username)


def _round_rect(name, x, y, width, height, radius, fill, outline=None, tags=None):
    return {
        "kind": "round_rect",
        "name": name,
        "rect": (x, y, width, height, radius),
        "fill": fill,
        "outline": outline,
        "tags": tuple(tags or ()),
    }


def _text(name, text, x, y, width, height, font, fill, anchor="nw", tags=None):
    return {
        "kind": "text",
        "name": name,
        "text": text,
        "rect": (x, y, width, height),
        "font": font,
        "fill": fill,
        "anchor": anchor,
        "tags": tuple(tags or ()),
    }


def build_shell_layout(app_path, app_status="running", admin_session_active=False):
    theme = SHELL_THEME
    is_minimized = app_status == "minimized"
    status_text = "Свернуто" if is_minimized else "Работает"
    status_color = theme["danger"] if is_minimized else theme["ok"]
    status_fill = "#3a1616" if is_minimized else "#0f2f1f"
    layout = [
        {
            "kind": "background",
            "name": "background",
            "rect": (0, 0, DESIGN_WIDTH, DESIGN_HEIGHT),
            "fill": theme["background"],
        },
        _text(
            "header_title",
            "Режим киоска",
            48,
            42,
            420,
            44,
            ("Segoe UI", 26, "bold"),
            theme["text"],
        ),
        _text(
            "header_subtitle",
            "Режим оператора: Explorer не запущен.",
            50,
            88,
            760,
            30,
            ("Segoe UI", 15, "normal"),
            theme["muted"],
        ),
        _round_rect("left_panel", 50, 150, 820, 560, 14, theme["panel"], theme["line"]),
        _text(
            "allowed_title",
            "Разрешенное приложение",
            92,
            190,
            420,
            44,
            ("Segoe UI", 26, "bold"),
            theme["text"],
        ),
        _text(
            "allowed_subtitle",
            "Запущено только настроенное приложение.",
            94,
            238,
            650,
            30,
            ("Segoe UI", 15, "normal"),
            theme["muted"],
        ),
        _round_rect("app_card", 95, 300, 690, 250, 12, "#0b1220", "#1d4ed8"),
        _text(
            "app_name",
            _app_name(app_path),
            135,
            344,
            430,
            58,
            ("Segoe UI", 36, "bold"),
            theme["text"],
        ),
        _text(
            "app_path",
            app_path,
            138,
            410,
            520,
            28,
            ("Consolas", 13, "normal"),
            theme["muted"],
        ),
        _round_rect("running_pill", 135, 478, 190, 44, 22, status_fill, None),
        _text(
            "running_status",
            status_text,
            166,
            486,
            110,
            28,
            ("Segoe UI", 15, "normal"),
            status_color,
        ),
        _round_rect("watchdog_pill", 345, 478, 270, 44, 22, "#122033", None),
        _text(
            "watchdog_status",
            "Надзор: включен",
            372,
            486,
            190,
            28,
            ("Segoe UI", 15, "normal"),
            theme["accent"],
        ),
        _text(
            "restart_message",
            "Приложение должно быть поверх оболочки. Если оно свернуто, разверните его кнопкой.",
            94,
            586,
            720,
            34,
            ("Segoe UI", 15, "normal"),
            theme["muted"],
        ),
        _round_rect("right_panel", 920, 150, 470, 560, 14, theme["panel"], theme["line"]),
        _text(
            "admin_title",
            "Разблокировка",
            955,
            190,
            260,
            44,
            ("Segoe UI", 26, "bold"),
            theme["text"],
        ),
        _round_rect(
            "unlock_button",
            958,
            284,
            250,
            54,
            8,
            theme["blue"],
            None,
            tags=("unlock_click",),
        ),
        _text(
            "unlock_button_text",
            "Разблокировать",
            985,
            297,
            190,
            28,
            ("Segoe UI", 15, "bold"),
            "#00111f",
            tags=("unlock_click",),
        ),
        _text(
            "unlock_button_hint",
            "Нажмите кнопку для входа администратора.",
            958,
            360,
            360,
            28,
            ("Segoe UI", 13, "normal"),
            theme["muted"],
        ),
        _text(
            "unlock_success_message",
            "После успеха откроется ограниченная админ-сессия.",
            958,
            718,
            360,
            42,
            ("Segoe UI", 12, "normal"),
            theme["muted"],
        ),
        _round_rect("safety_strip", 50, 760, 1340, 86, 12, "#101010", "#27272a"),
        _text(
            "safety_title",
            "Модель безопасности",
            82,
            782,
            160,
            28,
            ("Segoe UI", 15, "normal"),
            theme["text"],
        ),
        _text(
            "safety_message",
            "Win+L остается доступен. Службы, драйверы, процессы и автозагрузка не трогаются.",
            82,
            815,
            1120,
            28,
            ("Segoe UI", 15, "normal"),
            theme["muted"],
        ),
        _text(
            "policy_note",
            "Политики реестра: только отдельной админ-командой.",
            735,
            782,
            580,
            28,
            ("Segoe UI", 15, "normal"),
            theme["muted"],
        ),
        _text(
            "developer_credit",
            "разработал: Абдрахманов Амаль Даулетович",
            1390,
            858,
            520,
            28,
            ("Segoe UI", 12, "normal"),
            "#6b7280",
            anchor="ne",
        ),
    ]
    if admin_session_active:
        layout.extend(
            [
                _text(
                    "admin_session_title",
                    "Админ-сессия активна",
                    958,
                    455,
                    330,
                    28,
                    ("Segoe UI", 15, "bold"),
                    theme["ok"],
                ),
                _round_rect(
                    "unlock_desktop_button",
                    958,
                    492,
                    250,
                    44,
                    8,
                    theme["blue"],
                    None,
                    tags=("unlock_desktop_click",),
                ),
                _text(
                    "unlock_desktop_button_text",
                    "Открыть рабочий стол",
                    980,
                    502,
                    210,
                    24,
                    ("Segoe UI", 13, "bold"),
                    "#00111f",
                    tags=("unlock_desktop_click",),
                ),
                _round_rect(
                    "stop_watchdog_button",
                    958,
                    548,
                    250,
                    44,
                    8,
                    "#242a31",
                    None,
                    tags=("stop_watchdog_click",),
                ),
                _text(
                    "stop_watchdog_button_text",
                    "Остановить надзор",
                    984,
                    558,
                    205,
                    24,
                    ("Segoe UI", 13, "bold"),
                    theme["text"],
                    tags=("stop_watchdog_click",),
                ),
                _round_rect(
                    "return_kiosk_button",
                    958,
                    604,
                    250,
                    44,
                    8,
                    "#101820",
                    "#374151",
                    tags=("return_kiosk_click",),
                ),
                _text(
                    "return_kiosk_button_text",
                    "Вернуться в киоск",
                    995,
                    614,
                    180,
                    24,
                    ("Segoe UI", 13, "bold"),
                    theme["accent"],
                    tags=("return_kiosk_click",),
                ),
                _round_rect(
                    "change_app_button",
                    958,
                    660,
                    250,
                    44,
                    8,
                    "#242a31",
                    None,
                    tags=("change_app_click",),
                ),
                _text(
                    "change_app_button_text",
                    "Изменить приложение",
                    1000,
                    670,
                    180,
                    24,
                    ("Segoe UI", 13, "bold"),
                    theme["text"],
                    tags=("change_app_click",),
                ),
            ]
        )
    if is_minimized:
        layout.extend(
            [
                _round_rect(
                    "minimized_alert",
                    135,
                    558,
                    520,
                    42,
                    8,
                    "#3a1616",
                    "#7f1d1d",
                ),
                _text(
                    "minimized_alert_text",
                    "Приложение свернуто",
                    158,
                    567,
                    440,
                    24,
                    ("Segoe UI", 14, "bold"),
                    theme["danger"],
                ),
                _round_rect(
                    "restore_app_button",
                    135,
                    615,
                    255,
                    44,
                    8,
                    theme["blue"],
                    None,
                    tags=("restore_app_click",),
                ),
                _text(
                    "restore_app_button_text",
                    "Развернуть приложение",
                    158,
                    625,
                    210,
                    24,
                    ("Segoe UI", 14, "bold"),
                    "#00111f",
                    tags=("restore_app_click",),
                ),
            ]
        )
    return layout


def build_unlock_dialog_layout():
    theme = SHELL_THEME
    return [
        _round_rect("unlock_dialog", 965, 270, 380, 350, 12, theme["panel2"], "#374151"),
        _text(
            "unlock_title",
            "Вход администратора Windows",
            1000,
            320,
            310,
            30,
            ("Segoe UI", 15, "normal"),
            theme["text"],
        ),
        _text(
            "username_label",
            "Логин",
            1000,
            365,
            120,
            22,
            ("Segoe UI", 11, "normal"),
            theme["muted"],
        ),
        _round_rect("username_input", 1000, 391, 300, 42, 8, "#090b0f", "#4b5563"),
        _text(
            "username_example",
            "Администратор",
            1018,
            401,
            220,
            22,
            ("Consolas", 12, "normal"),
            theme["muted"],
        ),
        _text(
            "password_label",
            "Пароль",
            1000,
            432,
            120,
            22,
            ("Segoe UI", 11, "normal"),
            theme["muted"],
        ),
        _round_rect("password_input", 1000, 458, 300, 42, 8, "#090b0f", "#4b5563"),
        _text(
            "password_bullets",
            "************",
            1018,
            468,
            220,
            24,
            ("Consolas", 13, "normal"),
            theme["muted"],
        ),
        _round_rect("unlock_button", 1000, 540, 132, 42, 8, theme["blue"], None),
        _text(
            "unlock_button_text",
            "Открыть",
            1035,
            548,
            78,
            26,
            ("Segoe UI", 15, "normal"),
            "#00111f",
        ),
        _round_rect("cancel_button", 1150, 540, 118, 42, 8, "#242a31", None),
        _text(
            "cancel_button_text",
            "Отмена",
            1183,
            548,
            70,
            26,
            ("Segoe UI", 15, "normal"),
            theme["text"],
        ),
    ]


def scaled_unlock_dialog_geometry(screen_width, screen_height):
    dialog = dict((item["name"], item) for item in build_unlock_dialog_layout())[
        "unlock_dialog"
    ]
    x, y, width, height, _ = dialog["rect"]
    scale_x = float(screen_width) / DESIGN_WIDTH
    scale_y = float(screen_height) / DESIGN_HEIGHT
    return "{0}x{1}+{2}+{3}".format(
        int(round(width * scale_x)),
        int(round(height * scale_y)),
        int(round(x * scale_x)),
        int(round(y * scale_y)),
    )


def build_login_entry_options(masked=False):
    options = {
        "fg": SHELL_THEME["text"],
        "bg": "#090b0f",
        "insertbackground": SHELL_THEME["text"],
        "insertwidth": 2,
        "relief": "flat",
        "font": ("Consolas", 13),
        "highlightthickness": 1,
        "highlightbackground": "#4b5563",
        "highlightcolor": SHELL_THEME["accent"],
        "selectbackground": SHELL_THEME["accent"],
        "selectforeground": "#00111f",
    }
    if masked:
        options["show"] = "*"
    return options


def _scale_rect(rect, scale_x, scale_y):
    if len(rect) == 5:
        x, y, width, height, radius = rect
        return (
            x * scale_x,
            y * scale_y,
            width * scale_x,
            height * scale_y,
            min(radius * scale_x, radius * scale_y),
        )
    x, y, width, height = rect
    return x * scale_x, y * scale_y, width * scale_x, height * scale_y


def _scale_font(font, scale_y):
    family, size, style = font
    scaled_size = max(8, int(round(size * scale_y)))
    return family, scaled_size, style


def _draw_round_rect(canvas, x, y, width, height, radius, fill, outline=None, tags=()):
    x2 = x + width
    y2 = y + height
    points = [
        x + radius,
        y,
        x2 - radius,
        y,
        x2,
        y,
        x2,
        y + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x + radius,
        y2,
        x,
        y2,
        x,
        y2 - radius,
        x,
        y + radius,
        x,
        y,
    ]
    canvas.create_polygon(
        points,
        smooth=True,
        splinesteps=16,
        fill=fill,
        outline=outline or fill,
        width=2,
        tags=tags,
    )


def render_layout(canvas, layout, width, height):
    scale_x = float(width) / DESIGN_WIDTH
    scale_y = float(height) / DESIGN_HEIGHT
    for item in layout:
        kind = item["kind"]
        if kind == "background":
            canvas.create_rectangle(0, 0, width, height, fill=item["fill"], outline=item["fill"])
        elif kind == "round_rect":
            x, y, w, h, r = _scale_rect(item["rect"], scale_x, scale_y)
            _draw_round_rect(
                canvas,
                x,
                y,
                w,
                h,
                r,
                item["fill"],
                item.get("outline"),
                item.get("tags", ()),
            )
        elif kind == "text":
            x, y, w, h = _scale_rect(item["rect"], scale_x, scale_y)
            canvas.create_text(
                x,
                y,
                anchor=item.get("anchor", "nw"),
                text=item["text"],
                fill=item["fill"],
                font=_scale_font(item["font"], scale_y),
                width=w,
                tags=item.get("tags", ()),
            )


class ShellWindow(object):
    def __init__(
        self,
        root,
        launcher,
        credential_provider=None,
        password_provider=None,
        unlock_action=None,
        hotkey_service=None,
        keyboard_filter_service=None,
        app_window_controller=None,
        canvas_factory=None,
        credential_dialog_factory=None,
        password_dialog_factory=None,
        failed_attempt_limiter=None,
        sleep_func=None,
        logger=None,
        admin_session=None,
        session_lockdown=None,
        error_reporter=None,
        allowed_app_selector=None,
        watchdog_interval_ms=WATCHDOG_INTERVAL_MS,
        focus_guard_interval_ms=FOCUS_GUARD_INTERVAL_MS,
    ):
        self.root = root
        self.launcher = launcher
        self.credential_provider = (
            credential_provider
            or self._wrap_password_provider(password_provider)
            or self._default_credential_provider
        )
        self.unlock_action = unlock_action or unlock_desktop
        self.hotkey_service = hotkey_service
        self.keyboard_filter_service = keyboard_filter_service
        self.app_window_controller = app_window_controller or AppWindowController()
        self.canvas_factory = canvas_factory
        self.credential_dialog_factory = (
            credential_dialog_factory
            or password_dialog_factory
            or StyledAdminLoginDialog
        )
        self.failed_attempt_limiter = failed_attempt_limiter or FailedAttemptLimiter()
        self.sleep_func = sleep_func or time.sleep
        self.logger = logger or KioskLogger()
        self.admin_session = admin_session or AdminSession(logger=self.logger)
        self.error_reporter = error_reporter or (
            show_admin_error if hasattr(self.root, "tk") else (lambda message: False)
        )
        self.allowed_app_selector = allowed_app_selector or select_allowed_application
        kiosk_options = getattr(self.launcher.config, "kiosk", {})
        self.session_lockdown = session_lockdown or WindowsSessionLockdown(
            logger=self.logger,
            enabled=bool(kiosk_options.get("blockDesktop", True)),
        )
        self.watchdog_interval_ms = int(watchdog_interval_ms)
        self.focus_guard_interval_ms = int(focus_guard_interval_ms)
        self.watchdog = None
        self.canvas = None
        self.app_status = "running"
        self.watchdog_disabled = False
        self.keyboard_filter_suspended_for_admin = False
        self.admin_dialog_open = False

    def configure_window(self):
        self.root.title("Режим киоска")
        self.root.configure(bg=SHELL_THEME["background"])
        self.root.protocol("WM_DELETE_WINDOW", self.ignore_close)
        self.root.bind("<FocusOut>", self.keep_shell_background)
        self.root.bind("<Unmap>", self._handle_shell_unmap)
        self.activate_restrictions()
        self._configure_canvas()
        self.enforce_shell_focus()
        self.keep_shell_background()
        self.root.after(self.focus_guard_interval_ms, self._focus_guard_tick)

    def ignore_close(self):
        return None

    def _wrap_password_provider(self, password_provider):
        if password_provider is None:
            return None

        def provider():
            return "", password_provider()

        return provider

    def _default_credential_provider(self):
        return self.credential_dialog_factory(self.root).ask()

    def _configure_canvas(self):
        factory = self.canvas_factory
        if factory is None and hasattr(self.root, "tk"):
            factory = create_shell_canvas
        if factory is None:
            return

        self.canvas = factory(self.root)
        self.canvas.pack(fill="both", expand=True)
        self._configure_canvas_clicks()
        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()
        self._render_canvas(width, height)
        self.canvas.bind("<Configure>", self._handle_canvas_resize)

    def _configure_canvas_clicks(self):
        if hasattr(self.canvas, "tag_bind"):
            self.canvas.tag_bind("unlock_click", "<Button-1>", self.handle_admin_unlock)
            self.canvas.tag_bind("restore_app_click", "<Button-1>", self.handle_restore_app)
            self.canvas.tag_bind("unlock_desktop_click", "<Button-1>", self.handle_unlock_desktop)
            self.canvas.tag_bind("stop_watchdog_click", "<Button-1>", self.handle_stop_watchdog)
            self.canvas.tag_bind("return_kiosk_click", "<Button-1>", self.handle_return_to_kiosk)
            self.canvas.tag_bind("change_app_click", "<Button-1>", self.handle_change_allowed_app)
        if hasattr(self.canvas, "tag_configure"):
            self.canvas.tag_configure("unlock_click", cursor="hand2")
            self.canvas.tag_configure("restore_app_click", cursor="hand2")
            self.canvas.tag_configure("unlock_desktop_click", cursor="hand2")
            self.canvas.tag_configure("stop_watchdog_click", cursor="hand2")
            self.canvas.tag_configure("return_kiosk_click", cursor="hand2")
            self.canvas.tag_configure("change_app_click", cursor="hand2")

    def _handle_canvas_resize(self, event):
        self._render_canvas(event.width, event.height)

    def _render_canvas(self, width, height):
        self.canvas.delete("all")
        layout = build_shell_layout(
            self.launcher.config.app_path,
            self.app_status,
            admin_session_active=self.admin_session.is_active(),
        )
        render_layout(self.canvas, layout, width, height)

    def enforce_shell_focus(self, event=None):
        for call in (
            lambda: self.root.state("normal"),
            self.root.deiconify,
            lambda: self.root.attributes("-fullscreen", True),
        ):
            try:
                call()
            except Exception:
                pass

    def keep_shell_background(self, event=None):
        for call in (
            lambda: self.root.attributes("-topmost", False),
            self.root.lower,
        ):
            try:
                call()
            except Exception:
                pass

    def _handle_shell_unmap(self, event=None):
        if not self.admin_session.is_active():
            self.enforce_shell_focus()
        self.keep_shell_background()

    def _focus_guard_tick(self):
        self.keep_shell_background()
        self.root.after(self.focus_guard_interval_ms, self._focus_guard_tick)

    def handle_admin_unlock(self, event=None):
        if self.admin_dialog_open or self.admin_session.is_active():
            return bool(self.admin_session.is_active())
        self.logger.info("admin.dialog_open")
        self.keep_shell_background()
        self._reset_keyboard_filter_state()
        self.admin_dialog_open = True
        try:
            credentials = self.credential_provider()
        finally:
            self.admin_dialog_open = False
        if not credentials:
            return False
        username, password = credentials
        result = self._verify_admin_credentials(username, password)
        if result.success:
            self.failed_attempt_limiter.record_success()
            self.logger.info("admin.unlock_granted", **result.to_log_data())
            self.admin_session.start(result.username or username)
            self._suspend_keyboard_filter_for_admin_session()
            self.keep_shell_background()
            self._rerender_canvas()
            return True
        delay = self.failed_attempt_limiter.record_failure()
        data = result.to_log_data()
        data["message"] = result.message
        data["delay_seconds"] = delay
        self.logger.warning("admin.unlock_denied", **data)
        self.error_reporter(result.message)
        if delay > 0:
            self.sleep_func(delay)
        return False

    def _verify_admin_credentials(self, username, password):
        if hasattr(self.launcher, "verify_admin_credentials_result"):
            return self.launcher.verify_admin_credentials_result(username, password)
        if self.launcher.verify_admin_credentials(username, password):
            return AuthResult(
                AUTH_SUCCESS,
                username=username,
                domain="",
                message="Доступ разрешён.",
            )
        return AuthResult(
            AUTH_BAD_CREDENTIALS,
            username=username,
            domain="",
            message=MESSAGE_BAD_CREDENTIALS,
        )

    def handle_unlock_desktop(self, event=None):
        if not self.admin_session.is_active():
            self.logger.warning("admin.action_denied", action="unlock_desktop")
            return False
        self.release_restrictions()
        self.unlock_action()
        self.admin_session.mark_desktop_unlocked()
        self.logger.info("explorer.launched", username=self.admin_session.username)
        return True

    def handle_stop_watchdog(self, event=None):
        if not self.admin_session.is_active():
            self.logger.warning("admin.action_denied", action="stop_watchdog")
            return False
        self.watchdog_disabled = True
        if self.watchdog is not None and hasattr(self.watchdog, "stop"):
            self.watchdog.stop()
        self.logger.warning("watchdog.stopped_by_admin", username=self.admin_session.username)
        return True

    def handle_return_to_kiosk(self, event=None):
        self.watchdog_disabled = False
        self.admin_session.close(reason="return_to_kiosk")
        self.logger.info("admin.return_to_kiosk")
        self.activate_restrictions()
        self.enforce_shell_focus()
        self.keep_shell_background()
        self._rerender_canvas()
        return True

    def handle_change_allowed_app(self, event=None):
        if not self.admin_session.is_active():
            self.logger.warning("admin.action_denied", action="change_allowed_app")
            return False
        app_path = self.allowed_app_selector()
        if not app_path:
            return False
        try:
            self.launcher.set_allowed_application_path(app_path)
        except Exception as error:
            self.logger.warning("admin.change_app_failed", error=str(error))
            self.error_reporter(str(error))
            return False
        self.watchdog = None
        self.app_status = "running"
        self._rerender_canvas()
        self.logger.info("admin.change_app_path", path=app_path)
        return True

    def release_restrictions(self):
        if self.hotkey_service is not None and hasattr(self.hotkey_service, "stop"):
            self.hotkey_service.stop()
        self._stop_keyboard_filter()
        if self.session_lockdown is not None and hasattr(
            self.session_lockdown,
            "release_operator_mode",
        ):
            self.session_lockdown.release_operator_mode()
        if self.app_window_controller is not None and hasattr(
            self.app_window_controller,
            "release_topmost",
        ):
            self.app_window_controller.release_topmost(self.launcher.config.app_path)

    def activate_restrictions(self):
        if self.keyboard_filter_service is not None:
            self.keyboard_filter_service.start()
            self.keyboard_filter_suspended_for_admin = False
        if self.session_lockdown is not None:
            self.session_lockdown.activate_operator_mode()

    def _reset_keyboard_filter_state(self):
        if self.keyboard_filter_service is not None and hasattr(
            self.keyboard_filter_service,
            "reset_state",
        ):
            self.keyboard_filter_service.reset_state()

    def _suspend_keyboard_filter_for_admin_session(self):
        self._stop_keyboard_filter()

    def _stop_keyboard_filter(self):
        if self.keyboard_filter_suspended_for_admin:
            return
        if self.keyboard_filter_service is not None and hasattr(
            self.keyboard_filter_service,
            "stop",
        ):
            self.keyboard_filter_service.stop()
        self.keyboard_filter_suspended_for_admin = True

    def handle_restore_app(self, event=None):
        if self.app_window_controller.restore(self.launcher.config.app_path):
            self.keep_shell_background()
            self.app_status = "running"
            self._rerender_canvas()
        return True

    def _rerender_canvas(self):
        if self.canvas is None:
            return
        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()
        self._render_canvas(width, height)

    def _watchdog_tick(self):
        if self.watchdog is None:
            self.watchdog = self.launcher.create_watchdog()
        if not self.watchdog_disabled:
            watchdog_result = self.watchdog.tick()
            if watchdog_result in ("started", "restarted"):
                self.app_status = "running"
            admin_active = self.admin_session.is_active()
            if not admin_active and self.keyboard_filter_suspended_for_admin:
                self.activate_restrictions()
                self._rerender_canvas()
            if not admin_active and not self.admin_dialog_open:
                self._update_allowed_app_window()
        self.root.after(self.watchdog_interval_ms, self._watchdog_tick)

    def _update_allowed_app_window(self):
        app_path = self.launcher.config.app_path
        allowed_options = getattr(self.launcher.config, "allowed_application", None)
        restore_if_minimized = getattr(allowed_options, "restore_if_minimized", False)
        if self.app_status == "minimized" and not restore_if_minimized:
            return

        if self.app_window_controller.is_minimized(app_path):
            if restore_if_minimized:
                if self.app_window_controller.restore(app_path):
                    self.keep_shell_background()
                    next_status = "running"
                else:
                    next_status = "minimized"
            else:
                next_status = "minimized"
        else:
            if hasattr(self.app_window_controller, "ensure_foreground"):
                self.app_window_controller.ensure_foreground(
                    app_path,
                    wait=True,
                    timeout_seconds=5,
                    start_maximized=getattr(
                        getattr(self.launcher.config, "allowed_application", None),
                        "start_maximized",
                        False,
                    ),
                )
            else:
                self.app_window_controller.bring_to_front(app_path)
            self.keep_shell_background()
            next_status = "running"

        if next_status != self.app_status:
            previous_status = self.app_status
            self.app_status = next_status
            self.logger.info(
                "shell.app_status_changed",
                previous=previous_status,
                current=next_status,
                app_path=app_path,
            )
            self._rerender_canvas()

    def start(self):
        self.logger.info("shell.starting")
        self.configure_window()
        try:
            self._watchdog_tick()
            self.root.mainloop()
        finally:
            self.release_restrictions()
            self.logger.info("shell.stopped")


def unlock_desktop(process_factory=None):
    factory = process_factory or subprocess.Popen
    return factory(["explorer.exe"])


def show_admin_error(message):
    try:
        import tkinter.messagebox as messagebox

        messagebox.showerror("Режим киоска", message)
    except Exception:
        return False
    return True


def select_allowed_application():
    try:
        import tkinter.filedialog as filedialog

        return filedialog.askopenfilename(
            title="Выберите разрешённое приложение",
            filetypes=(("Windows EXE", "*.exe"), ("Все файлы", "*.*")),
        )
    except Exception:
        return ""


def create_shell_canvas(root):
    import tkinter

    return tkinter.Canvas(
        root,
        bg=SHELL_THEME["background"],
        highlightthickness=0,
        bd=0,
    )


class StyledAdminLoginDialog(object):
    def __init__(self, root):
        self.root = root
        self.result = None

    def ask(self):
        import tkinter

        dialog = tkinter.Toplevel(self.root)
        dialog.title("Режим киоска")
        dialog.configure(bg=SHELL_THEME["panel2"])
        dialog.resizable(False, False)
        dialog.overrideredirect(True)
        dialog.transient(self.root)
        dialog.grab_set()
        try:
            dialog.attributes("-topmost", True)
            dialog.lift()
            dialog.focus_force()
        except Exception:
            pass

        dialog.geometry(
            scaled_unlock_dialog_geometry(
                dialog.winfo_screenwidth(),
                dialog.winfo_screenheight(),
            )
        )

        frame = tkinter.Frame(
            dialog,
            bg=SHELL_THEME["panel2"],
            highlightbackground="#374151",
            highlightthickness=2,
        )
        frame.pack(fill="both", expand=True)

        title = tkinter.Label(
            frame,
            text="Вход администратора Windows",
            fg=SHELL_THEME["text"],
            bg=SHELL_THEME["panel2"],
            font=("Segoe UI", 15),
            anchor="w",
        )
        title.place(x=34, y=30, width=310, height=30)

        username_label = tkinter.Label(
            frame,
            text="Логин",
            fg=SHELL_THEME["muted"],
            bg=SHELL_THEME["panel2"],
            font=("Segoe UI", 11),
            anchor="w",
        )
        username_label.place(x=34, y=72, width=160, height=22)

        username = tkinter.Entry(
            frame,
            **build_login_entry_options(masked=False)
        )
        username.place(x=34, y=98, width=300, height=42)

        password_label = tkinter.Label(
            frame,
            text="Пароль",
            fg=SHELL_THEME["muted"],
            bg=SHELL_THEME["panel2"],
            font=("Segoe UI", 11),
            anchor="w",
        )
        password_label.place(x=34, y=152, width=160, height=22)

        password = tkinter.Entry(
            frame,
            **build_login_entry_options(masked=True)
        )
        password.place(x=34, y=178, width=300, height=42)
        username.focus_set()
        try:
            dialog.after(50, username.focus_force)
        except Exception:
            pass

        def accept(event=None):
            self.result = (
                username.get().strip(),
                password.get(),
            )
            dialog.destroy()

        def cancel(event=None):
            self.result = None
            dialog.destroy()

        unlock_button = tkinter.Button(
            frame,
            text="Открыть",
            command=accept,
            fg="#00111f",
            bg=SHELL_THEME["blue"],
            activebackground=SHELL_THEME["blue"],
            activeforeground="#00111f",
            relief="flat",
            font=("Segoe UI", 15),
        )
        unlock_button.place(x=34, y=264, width=132, height=42)

        cancel_button = tkinter.Button(
            frame,
            text="Отмена",
            command=cancel,
            fg=SHELL_THEME["text"],
            bg="#242a31",
            activebackground="#242a31",
            activeforeground=SHELL_THEME["text"],
            relief="flat",
            font=("Segoe UI", 15),
        )
        cancel_button.place(x=184, y=264, width=118, height=42)

        dialog.bind("<Return>", accept)
        dialog.bind("<Escape>", cancel)
        self.root.wait_window(dialog)
        return self.result


StyledPasswordDialog = StyledAdminLoginDialog


class WindowsKeyFilter(object):
    WH_KEYBOARD_LL = 13
    HC_ACTION = 0
    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    WM_SYSKEYDOWN = 0x0104
    WM_SYSKEYUP = 0x0105
    WM_QUIT = 0x0012
    VK_L = ord("L")
    VK_TAB = 0x09
    VK_BACK = 0x08
    VK_RETURN = 0x0D
    VK_SPACE = 0x20
    VK_ESCAPE = 0x1B
    VK_DELETE = 0x2E
    VK_MENU = 0x12
    VK_CONTROL = 0x11
    VK_SHIFT = 0x10
    VK_F4 = 0x73
    VK_LWIN = 0x5B
    VK_RWIN = 0x5C
    VK_LSHIFT = 0xA0
    VK_RSHIFT = 0xA1
    VK_LCONTROL = 0xA2
    VK_RCONTROL = 0xA3
    VK_LMENU = 0xA4
    VK_RMENU = 0xA5

    def __init__(self, lock_workstation=None, logger=None, key_state_checker=None):
        self.lock_workstation = lock_workstation
        self.logger = logger or KioskLogger()
        self.key_state_checker = key_state_checker
        self.thread = None
        self.thread_id = None
        self.hook = None
        self.callback = None
        self.reset_state()

    def reset_state(self):
        self.win_down = False
        self.alt_down = False
        self.ctrl_down = False
        self.shift_down = False

    def should_block_key(self, vk_code, message):
        is_down = message in (self.WM_KEYDOWN, self.WM_SYSKEYDOWN)
        is_up = message in (self.WM_KEYUP, self.WM_SYSKEYUP)
        is_win_key = vk_code in (self.VK_LWIN, self.VK_RWIN)

        if is_win_key:
            if is_down:
                self.win_down = True
                return self._block_shortcut("Win", is_down)
            if is_up:
                self.win_down = False
            return False

        if vk_code in (self.VK_MENU, self.VK_LMENU, self.VK_RMENU):
            self.alt_down = is_down or (self.alt_down and not is_up)
            return False

        if vk_code in (self.VK_CONTROL, self.VK_LCONTROL, self.VK_RCONTROL):
            self.ctrl_down = is_down or (self.ctrl_down and not is_up)
            return False

        if vk_code in (self.VK_SHIFT, self.VK_LSHIFT, self.VK_RSHIFT):
            self.shift_down = is_down or (self.shift_down and not is_up)
            return False

        if not is_down:
            return False

        if self.win_down and not self._is_any_win_key_pressed():
            self.win_down = False
        self._recover_stale_modifier_state()

        alt_pressed = self.alt_down or self._is_any_alt_key_pressed()
        ctrl_pressed = self.ctrl_down or self._is_any_ctrl_key_pressed()

        if self.win_down:
            if is_down and vk_code == self.VK_L:
                self._lock_workstation()
                return self._block_shortcut("Win+L", is_down)
            return self._block_shortcut("Win+{0}".format(self._vk_name(vk_code)), is_down)

        if alt_pressed and vk_code == self.VK_TAB:
            if ctrl_pressed:
                return self._block_shortcut("Ctrl+Alt+Tab", is_down)
            return self._block_shortcut("Alt+Tab", is_down)

        if is_down and alt_pressed and vk_code in (self.VK_ESCAPE, self.VK_F4):
            return self._block_shortcut("Alt+{0}".format(self._vk_name(vk_code)), is_down)

        if is_down and ctrl_pressed and vk_code == self.VK_ESCAPE:
            return self._block_shortcut("Ctrl+Esc", is_down)

        return False

    def _block_shortcut(self, shortcut, is_down=True):
        if is_down:
            try:
                self.logger.warning("keyboard_filter.blocked_shortcut", shortcut=shortcut)
            except Exception:
                pass
        return True

    def _vk_name(self, vk_code):
        names = {
            self.VK_TAB: "Tab",
            self.VK_ESCAPE: "Esc",
            self.VK_F4: "F4",
            self.VK_L: "L",
        }
        if ord("A") <= int(vk_code) <= ord("Z") or ord("0") <= int(vk_code) <= ord("9"):
            return chr(int(vk_code))
        return "VK_{0}".format(vk_code)

    def _is_any_win_key_pressed(self):
        return self._is_key_pressed(self.VK_LWIN) or self._is_key_pressed(self.VK_RWIN)

    def _is_any_alt_key_pressed(self):
        return (
            self._is_key_pressed(self.VK_MENU)
            or self._is_key_pressed(self.VK_LMENU)
            or self._is_key_pressed(self.VK_RMENU)
        )

    def _is_any_ctrl_key_pressed(self):
        return (
            self._is_key_pressed(self.VK_CONTROL)
            or self._is_key_pressed(self.VK_LCONTROL)
            or self._is_key_pressed(self.VK_RCONTROL)
        )

    def _is_any_shift_key_pressed(self):
        return (
            self._is_key_pressed(self.VK_SHIFT)
            or self._is_key_pressed(self.VK_LSHIFT)
            or self._is_key_pressed(self.VK_RSHIFT)
        )

    def _recover_stale_modifier_state(self):
        if not self._has_physical_key_state_source():
            return
        if self.alt_down and not self._is_any_alt_key_pressed():
            self.alt_down = False
        if self.ctrl_down and not self._is_any_ctrl_key_pressed():
            self.ctrl_down = False
        if self.shift_down and not self._is_any_shift_key_pressed():
            self.shift_down = False

    def _has_physical_key_state_source(self):
        return self.key_state_checker is not None or os.name == "nt"

    def _is_key_pressed(self, vk_code):
        if self.key_state_checker is not None:
            try:
                return bool(self.key_state_checker(vk_code))
            except Exception:
                return False
        if os.name != "nt":
            return False
        try:
            import ctypes

            return bool(ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000)
        except Exception:
            return False

    def _lock_workstation(self):
        if self.lock_workstation is not None:
            self.lock_workstation()
            return
        if os.name == "nt":
            import ctypes

            ctypes.windll.user32.LockWorkStation()

    def start(self):
        if os.name != "nt":
            return
        if self.thread is not None and self.thread.is_alive():
            return
        self.thread = None
        self.thread_id = None
        self.thread = threading.Thread(
            target=self._message_loop,
            name="PythonKioskWinKeyFilter",
        )
        self.thread.daemon = True
        self.thread.start()
        try:
            self.logger.info("keyboard_filter.started")
        except Exception:
            pass

    def _message_loop(self):
        import ctypes
        from ctypes import wintypes

        class KBDLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("vkCode", wintypes.DWORD),
                ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t),
            ]

        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("message", wintypes.UINT),
                ("wParam", wintypes.WPARAM),
                ("lParam", wintypes.LPARAM),
                ("time", wintypes.DWORD),
                ("pt", wintypes.POINT),
            ]

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self.thread_id = kernel32.GetCurrentThreadId()

        HOOKPROC = ctypes.WINFUNCTYPE(
            wintypes.LPARAM,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )

        def callback(n_code, w_param, l_param):
            if n_code == self.HC_ACTION:
                event = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if self.should_block_key(event.vkCode, int(w_param)):
                    return 1
            return user32.CallNextHookEx(self.hook, n_code, w_param, l_param)

        self.callback = HOOKPROC(callback)
        self.hook = user32.SetWindowsHookExW(
            self.WH_KEYBOARD_LL,
            self.callback,
            None,
            0,
        )
        if not self.hook:
            try:
                self.logger.warning(
                    "keyboard_filter.install_failed",
                    error_code=kernel32.GetLastError(),
                )
            except Exception:
                pass
            return

        message = MSG()
        try:
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) != 0:
                pass
        finally:
            user32.UnhookWindowsHookEx(self.hook)
            self.hook = None

    def stop(self):
        if os.name != "nt" or self.thread_id is None:
            return
        import ctypes

        ctypes.windll.user32.PostThreadMessageW(
            self.thread_id,
            self.WM_QUIT,
            0,
            0,
        )
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(1.0)
        self.thread = None
        self.thread_id = None
        try:
            self.logger.info("keyboard_filter.stopped")
        except Exception:
            pass


def run_shell(
    launcher,
    tkinter_module=None,
    shell_window_class=ShellWindow,
    keyboard_filter_class=WindowsKeyFilter,
):
    if tkinter_module is None:
        import tkinter as tkinter_module

    root = tkinter_module.Tk()
    kiosk_options = getattr(launcher.config, "kiosk", {})
    keyboard_filter_service = (
        keyboard_filter_class(logger=launcher.logger)
        if os.name == "nt" and bool(kiosk_options.get("blockWinKey", True))
        else None
    )
    shell_window_class(
        root,
        launcher,
        hotkey_service=None,
        keyboard_filter_service=keyboard_filter_service,
        canvas_factory=create_shell_canvas,
        logger=launcher.logger,
    ).start()
```

## python_kiosk\single_instance.py

```python
# -*- coding: utf-8 -*-

import hashlib
import os


class SingleInstanceGuard(object):
    ERROR_ALREADY_EXISTS = 183

    def __init__(self, name):
        self.name = self._safe_name(name)
        self.handle = None
        self.acquired = False

    @classmethod
    def for_config(cls, config_path):
        normalized = os.path.normcase(os.path.abspath(config_path or "default"))
        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
        return cls("Local\\PythonKiosk-{0}".format(digest))

    @classmethod
    def for_operator(cls, operator_user):
        normalized = str(operator_user or "default").strip().lower() or "default"
        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
        return cls("Local\\PythonKiosk-Operator-{0}".format(digest))

    def acquire(self):
        if os.name != "nt":
            self.acquired = True
            return True
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.GetLastError.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.CreateMutexW(None, True, self.name)
        if not handle:
            self.acquired = False
            return False
        self.handle = handle
        if kernel32.GetLastError() == self.ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            self.handle = None
            self.acquired = False
            return False
        self.acquired = True
        return True

    def release(self):
        if os.name != "nt":
            self.acquired = False
            return
        if not self.handle:
            self.acquired = False
            return
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
        kernel32.ReleaseMutex.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        if self.acquired:
            kernel32.ReleaseMutex(self.handle)
        kernel32.CloseHandle(self.handle)
        self.handle = None
        self.acquired = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False

    @staticmethod
    def _safe_name(name):
        return str(name or "Local\\PythonKiosk").replace("/", "_")
```

## python_kiosk\system_backend.py

```python
# -*- coding: utf-8 -*-

import os
import re
import subprocess


FORBIDDEN_OPERATION_NAMES = set(
    [
        "stop_services",
        "disable_services",
        "clear_startup",
        "kill_processes",
        "terminate_processes",
        "disable_drivers",
    ]
)

ADMIN_RIGHTS_REQUIRED_MESSAGE = (
    "Отказано в доступе. Для выполнения действия требуются права администратора Windows."
)


OPERATOR_POLICY_VALUES = [
    (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\System",
        "DisableTaskMgr",
        "REG_DWORD",
        "1",
    ),
    (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\System",
        "DisableRegistryTools",
        "REG_DWORD",
        "1",
    ),
    (
        r"Software\Policies\Microsoft\Windows\System",
        "DisableCMD",
        "REG_DWORD",
        "2",
    ),
    (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "NoRun",
        "REG_DWORD",
        "1",
    ),
    (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "NoControlPanel",
        "REG_DWORD",
        "1",
    ),
    (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "NoViewContextMenu",
        "REG_DWORD",
        "1",
    ),
    (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "NoTrayContextMenu",
        "REG_DWORD",
        "1",
    ),
    (
        r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
        "NoSetTaskbar",
        "REG_DWORD",
        "1",
    ),
]


class CompletedCommand(object):
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = int(returncode)


class WindowsSystemBackend(object):
    def __init__(self, command_runner=None, logger=None):
        self.command_runner = command_runner or self._default_command_runner
        self.logger = logger

    def is_admin(self):
        if os.name != "nt":
            return False
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def apply_operation(self, operation):
        if operation.name in FORBIDDEN_OPERATION_NAMES:
            raise ValueError(
                "Операция запрещена границами безопасности киоска: {0}".format(
                    operation.name
                )
            )

        handler = getattr(self, "_apply_{0}".format(operation.name), None)
        if handler is None:
            return operation.name
        return handler(operation)

    def _default_command_runner(self, command, **kwargs):
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            creationflags=creationflags,
        )
        stdout_bytes, stderr_bytes = process.communicate()
        return CompletedCommand(
            stdout=self._decode_process_bytes(stdout_bytes),
            stderr=self._decode_process_bytes(stderr_bytes),
            returncode=process.returncode,
        )

    def _decode_process_bytes(self, value):
        if isinstance(value, str):
            return value
        for encoding in ("mbcs", "utf-8", "cp866", "cp1251"):
            try:
                return value.decode(encoding, "ignore")
            except (LookupError, UnicodeError, AttributeError):
                pass
        try:
            return value.decode("utf-8", "ignore")
        except AttributeError:
            return ""

    def _run(self, command, check=False):
        result = self.command_runner(command)
        if check and result.returncode != 0:
            detail = result.stderr or result.stdout or "код {0}".format(result.returncode)
            raise RuntimeError(
                "Команда Windows завершилась ошибкой: {0}; {1}".format(
                    " ".join(command),
                    detail.strip(),
                )
            )
        return result

    def _apply_create_backup(self, operation):
        return operation.name

    def _apply_load_backup(self, operation):
        return operation.name

    def _apply_preserve_services_drivers_startup(self, operation):
        return operation.name

    def _apply_allow_fixed_executable(self, operation):
        app_path = operation.data.get("app_path")
        if app_path and not os.path.exists(app_path):
            raise RuntimeError(
                "Разрешенное приложение не найдено: {0}".format(app_path)
            )
        return operation.name

    def _apply_prepare_srp_rules(self, operation):
        return self._apply_allow_fixed_executable(operation)

    def _apply_prepare_applocker_rules(self, operation):
        return self._apply_allow_fixed_executable(operation)

    def _apply_prepare_shelllauncher_config(self, operation):
        return operation.name

    def _apply_apply_home_fallback_policy(self, operation):
        return self._apply_apply_hkcu_operator_policies(operation)

    def _apply_apply_xp_legacy_registry_policy(self, operation):
        return self._apply_apply_hkcu_operator_policies(operation)

    def _apply_ensure_operator_user(self, operation):
        operator_user = self._required_operator(operation)
        result = self._run(["net", "user", operator_user])
        if result.returncode != 0:
            raise RuntimeError(
                "Операторская учетная запись не найдена: {0}. Создайте ее заранее отдельной командой или скриптом.".format(
                    operator_user
                )
            )
        self._ensure_operator_is_not_local_admin(operator_user)
        return operation.name

    def _ensure_operator_is_not_local_admin(self, operator_user):
        group_name = self._administrator_group_name()
        if not group_name:
            return
        result = self._run(["net", "localgroup", group_name])
        if result.returncode != 0:
            return
        operator_lower = operator_user.lower()
        members = [line.strip().lower() for line in result.stdout.splitlines()]
        if operator_lower in members:
            raise RuntimeError(
                "Операторская учетная запись не должна входить в локальную группу Administrators: {0}".format(
                    operator_user
                )
            )

    def _administrator_group_name(self):
        result = self._run(
            ["wmic", "group", "where", "sid='S-1-5-32-544'", "get", "name", "/value"]
        )
        if result.returncode != 0:
            return "Administrators"
        for line in result.stdout.splitlines():
            if line.strip().lower().startswith("name="):
                return line.split("=", 1)[1].strip() or "Administrators"
        return "Administrators"

    def _apply_set_operator_shell(self, operation):
        operator_user = self._required_operator(operation)
        shell_command = operation.data.get("shell_command") or operation.data.get("shell")
        if not shell_command:
            raise RuntimeError("Не задана команда shell для KioskLauncher.")

        def apply_to_hive(hive_root):
            self._reg_add(
                hive_root,
                r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon",
                "Shell",
                "REG_SZ",
                shell_command,
            )

        self._with_operator_hive(operator_user, apply_to_hive)
        return operation.name

    def _apply_restore_operator_shell(self, operation):
        operator_user = self._required_operator(operation)
        shell = operation.data.get("shell") or "explorer.exe"

        def apply_to_hive(hive_root):
            self._reg_add(
                hive_root,
                r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon",
                "Shell",
                "REG_SZ",
                shell,
            )

        self._with_operator_hive(operator_user, apply_to_hive)
        return operation.name

    def _apply_apply_hkcu_operator_policies(self, operation):
        operator_user = self._required_operator(operation)

        def apply_to_hive(hive_root):
            for key_path, value_name, value_type, value_data in OPERATOR_POLICY_VALUES:
                self._reg_add(hive_root, key_path, value_name, value_type, value_data)

        self._with_operator_hive(operator_user, apply_to_hive)
        return operation.name

    def _apply_restore_operator_policies(self, operation):
        operator_user = self._required_operator(operation)

        def apply_to_hive(hive_root):
            for key_path, value_name, _value_type, _value_data in OPERATOR_POLICY_VALUES:
                self._reg_delete_value(hive_root, key_path, value_name)

        self._with_operator_hive(operator_user, apply_to_hive)
        return operation.name

    def _required_operator(self, operation):
        operator_user = operation.data.get("operator_user")
        if not operator_user:
            raise RuntimeError("Не указана операторская учетная запись.")
        return operator_user

    def _with_operator_hive(self, operator_user, callback):
        sid = self._operator_sid(operator_user)
        mounted_hive = r"HKU\{0}".format(sid)
        if self._run(["reg", "query", mounted_hive]).returncode == 0:
            callback(mounted_hive)
            return

        profile_path = self._profile_path_for_sid(sid)
        ntuser_path = os.path.join(os.path.expandvars(profile_path), "NTUSER.DAT")
        temp_hive = r"HKU\PythonKiosk_{0}".format(re.sub(r"[^A-Za-z0-9_]", "_", sid))
        self._run(["reg", "load", temp_hive, ntuser_path], check=True)
        try:
            callback(temp_hive)
        finally:
            self._run(["reg", "unload", temp_hive])

    def _operator_sid(self, operator_user):
        escaped_user = operator_user.replace("'", "''")
        result = self._run(
            [
                "wmic",
                "useraccount",
                "where",
                "name='{0}' and localaccount=true".format(escaped_user),
                "get",
                "sid",
                "/value",
            ],
            check=True,
        )
        for line in result.stdout.splitlines():
            if line.strip().lower().startswith("sid="):
                sid = line.split("=", 1)[1].strip()
                if sid:
                    return sid
        raise RuntimeError(
            "Не удалось определить SID операторской учетной записи: {0}".format(
                operator_user
            )
        )

    def _profile_path_for_sid(self, sid):
        result = self._run(
            [
                "reg",
                "query",
                r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\{0}".format(
                    sid
                ),
                "/v",
                "ProfileImagePath",
            ],
            check=True,
        )
        for line in result.stdout.splitlines():
            if "ProfileImagePath" in line:
                parts = re.split(r"\s{2,}", line.strip())
                if len(parts) >= 3:
                    return parts[-1].strip()
        raise RuntimeError("Не найден профиль Windows для SID: {0}".format(sid))

    def _reg_add(self, hive_root, key_path, value_name, value_type, value_data):
        self._run(
            [
                "reg",
                "add",
                r"{0}\{1}".format(hive_root, key_path),
                "/v",
                value_name,
                "/t",
                value_type,
                "/d",
                str(value_data),
                "/f",
            ],
            check=True,
        )

    def _reg_delete_value(self, hive_root, key_path, value_name):
        self._run(
            [
                "reg",
                "delete",
                r"{0}\{1}".format(hive_root, key_path),
                "/v",
                value_name,
                "/f",
            ],
            check=False,
        )
```

## python_kiosk\window_control.py

```python
# -*- coding: utf-8 -*-

import os
import time

from python_kiosk.process_watchdog import (
    windows_process_ids_for_name,
    windows_process_ids_for_path,
)


class AppWindowController(object):
    def __init__(self, backend=None):
        self.backend = backend or WindowsWindowBackend()

    def _first_window(self, executable_path):
        windows = self.backend.find_windows_for_executable(executable_path)
        return windows[0] if windows else None

    def is_minimized(self, executable_path):
        windows = self.backend.find_windows_for_executable(executable_path)
        return bool(windows and any(self.backend.is_minimized(hwnd) for hwnd in windows))

    def bring_to_front(self, executable_path):
        hwnd = self._first_window(executable_path)
        if not hwnd:
            return False
        self.backend.bring_to_front(hwnd)
        return True

    def ensure_foreground(
        self,
        executable_path,
        wait=False,
        timeout_seconds=5,
        start_maximized=False,
    ):
        if wait and hasattr(self.backend, "wait_for_window"):
            hwnd = self.backend.wait_for_window(executable_path, timeout_seconds)
        else:
            hwnd = self._first_window(executable_path)
        if not hwnd:
            return False
        if self.backend.is_minimized(hwnd):
            self.backend.restore(hwnd)
        if start_maximized and hasattr(self.backend, "maximize"):
            self.backend.maximize(hwnd)
        self.backend.bring_to_front(hwnd)
        return True

    def restore(self, executable_path):
        hwnd = self._first_window(executable_path)
        if not hwnd:
            return False
        self.backend.restore(hwnd)
        self.backend.bring_to_front(hwnd)
        return True

    def release_topmost(self, executable_path):
        hwnd = self._first_window(executable_path)
        if not hwnd:
            return False
        self.backend.clear_topmost(hwnd)
        return True


class WindowsWindowBackend(object):
    SW_RESTORE = 9
    SW_SHOWNORMAL = 1
    SW_MAXIMIZE = 3
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040

    def wait_for_window(self, executable_path, timeout_seconds=5):
        deadline = time.time() + float(timeout_seconds)
        while time.time() <= deadline:
            hwnd = None
            windows = self.find_windows_for_executable(executable_path)
            if windows:
                hwnd = windows[0]
            if hwnd:
                return hwnd
            time.sleep(0.1)
        return None

    def find_windows_for_executable(self, executable_path):
        if os.name != "nt":
            return []

        pids = self._process_ids_for_executable(executable_path)
        if not pids:
            return []

        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        found = []

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def callback(hwnd, l_param):
            if not user32.IsWindowVisible(hwnd):
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if int(pid.value) in pids:
                found.append(hwnd)
            return True

        user32.EnumWindows(WNDENUMPROC(callback), 0)
        return found

    def _process_ids_for_executable(self, executable_path):
        pids = self._process_ids_for_exact_path(executable_path)
        if pids:
            return pids
        return self._process_ids_for_image_name(executable_path)

    def _process_ids_for_exact_path(self, executable_path):
        return windows_process_ids_for_path(executable_path)

    def _process_ids_for_image_name(self, executable_path):
        return windows_process_ids_for_name(executable_path)

    def is_minimized(self, hwnd):
        if os.name != "nt":
            return False
        import ctypes

        return bool(ctypes.windll.user32.IsIconic(hwnd))

    def bring_to_front(self, hwnd):
        if os.name != "nt":
            return
        import ctypes

        user32 = ctypes.windll.user32
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, self.SW_RESTORE)
        user32.SetWindowPos(
            hwnd,
            self.HWND_TOPMOST,
            0,
            0,
            0,
            0,
            self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_SHOWWINDOW,
        )
        user32.SetForegroundWindow(hwnd)
        user32.SetWindowPos(
            hwnd,
            self.HWND_NOTOPMOST,
            0,
            0,
            0,
            0,
            self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_SHOWWINDOW,
        )

    def maximize(self, hwnd):
        if os.name != "nt":
            return
        import ctypes

        ctypes.windll.user32.ShowWindow(hwnd, self.SW_MAXIMIZE)

    def clear_topmost(self, hwnd):
        if os.name != "nt":
            return
        import ctypes

        ctypes.windll.user32.SetWindowPos(
            hwnd,
            self.HWND_NOTOPMOST,
            0,
            0,
            0,
            0,
            self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_SHOWWINDOW,
        )

    def restore(self, hwnd):
        if os.name != "nt":
            return
        import ctypes

        ctypes.windll.user32.ShowWindow(hwnd, self.SW_RESTORE)
```

## README.md

```markdown
# Режим киоска

**Режим киоска** — Python-оболочка для отдельной операторской учётной записи Windows. Она запускается вместо `explorer.exe`, блокирует обычный рабочий стол оператора и держит запущенным только одно разрешённое Win32-приложение из `config/kiosk.json`.

Проект не останавливает службы Windows, драйверы, системные процессы и существующую автозагрузку. Ограничения применяются только к отдельной операторской УЗ.

## Быстрый запуск

В PyCharm кнопка `RUN` для `main.py` без аргументов сразу запускает оболочку (`launch`). Если `config/kiosk.json` отсутствует, создаётся шаблон с `C:\Windows\System32\notepad.exe`.

```powershell
python main.py launch --config config\kiosk.json
```

После любого ручного теста можно принудительно вернуть рабочий стол текущей сессии:

```powershell
python main.py recover-desktop
```

## Конфигурация

Основной файл:

```text
config/kiosk.json
```

Ключевой раздел:

```json
{
  "operatorUser": "KioskOperator",
  "allowedApplication": {
    "path": "C:\\Windows\\System32\\notepad.exe",
    "arguments": "",
    "workingDirectory": "C:\\Windows\\System32",
    "restartOnExit": true,
    "bringToFront": true,
    "restoreIfMinimized": false,
    "startMaximized": false
  },
  "kiosk": {
    "blockDesktop": true,
    "disableStartMenu": true,
    "disableExplorer": true,
    "allowWinL": true,
    "blockWinKey": true,
    "adminSessionTimeoutSeconds": 300
  },
  "testing": {
    "requireBackupBeforeTest": true,
    "restoreAfterTest": true,
    "testOnlySeparateOperatorUser": true
  }
}
```

Пароль администратора Windows в конфиге не хранится. Для разблокировки используется локальная проверка Windows API: `LogonUser`, токен и членство в группе Administrators.

## Операторский режим

Правильная схема работы:

1. Администратор настраивает отдельную операторскую УЗ без прав администратора.
2. Configurator назначает KioskLauncher как shell только для этой УЗ.
3. Оператор входит в свою УЗ.
4. Вместо `explorer.exe` стартует KioskLauncher.
5. KioskLauncher включает Win-key filter и session-lockdown.
6. Разрешённое приложение запускается, ожидается его главное окно и выводится поверх фонового окна киоска.
7. Если приложение свернули, киоск показывает предупреждение и кнопку `Развернуть приложение`; если закрыли, watchdog запускает его снова.

При тестовом запуске внутри уже открытой сессии киоск безопасно скрывает только desktop-элементы Explorer текущей сессии. `WM_CLOSE` в панель задач не отправляется, поэтому системное окно завершения Windows не вызывается. Массового завершения процессов нет.

## Блокировка клавиш

В операторском режиме блокируются `Win`, `Win+R`, `Win+E`, `Win+X`, `Win+S`, `Win+D`, `Win+M`, `Win+Tab`, `Ctrl+Esc`, `Alt+Tab`, `Alt+Esc`, `Alt+F4`. `Win+L` не блокируется: hook вызывает блокировку рабочей станции и не записывает нажатия клавиш.

`Ctrl+Alt+Del` не перехватывается небезопасными способами; ограничения Task Manager выполняются через политики, где это доступно.

## Разблокировка

Открыть окно администратора можно только кнопкой `Разблокировать`.

Окно содержит:

- пользователь;
- пароль;
- `ОК`;
- `Отмена`.

После успешного ввода учётных данных администратора Windows открывается ограниченная админ-сессия. В ней можно временно открыть рабочий стол (`explorer.exe`), остановить watchdog, изменить путь разрешённого приложения и вернуться в киоск.

## Установка и восстановление

Dry-run:

```powershell
.\scripts\install.ps1 -Config .\config\kiosk.json
.\scripts\restore.ps1 -Config .\config\kiosk.json
```

Реальное применение:

```powershell
.\scripts\install.ps1 -Config .\config\kiosk.json -Apply
.\scripts\restore.ps1 -Config .\config\kiosk.json -Apply
```

Если процесс не запущен с повышенными правами администратора Windows, административные действия возвращают:

```text
Отказано в доступе. Для выполнения действия требуются права администратора Windows.
```

## Совместимость

Архитектура содержит профили `xp_legacy`, `win7_srp`, `win10_applocker`, `win10_shelllauncher`, `home_fallback`. Home-редакции используют fallback с пониженной гарантией. Текущий exe, собранный Python 3.14, не является XP-совместимым; для XP нужна отдельная legacy-сборка старым Python/PyInstaller.

## Сборка

```powershell
python -m pip install -r requirements-build.txt
.\build_release.ps1
```

Результаты:

- `dist\RezhimKioska.exe`;
- `release\RezhimKioska.exe`;
- `release\config\kiosk.json`;
- `release\PythonKiosk-GitHub.zip`.

## Обновление 2026-06-16: горячие клавиши и один экземпляр приложения

В операторском режиме дополнительно явно блокируются `Alt+Tab` и `Ctrl+Alt+Tab`: переключатель окон Windows не должен появляться. Обычный ввод текста при этом не блокируется: буквы, цифры, пробел, `Backspace`, `Delete`, `Enter` и обычный `Tab` проходят дальше в разрешенное приложение и в окно авторизации администратора.

После успешной авторизации локальной учетной записью Windows, входящей в локальную группу `Administrators`, keyboard hook временно отключается на время admin-сессии. При возврате в киоск или истечении admin-сессии ограничения включаются снова. `Win+L` остается разрешенным.

`allowedApplication` в `config/kiosk.json` содержит защиту от повторного запуска:

```json
{
  "singleInstance": true,
  "bringExistingToFront": true,
  "restartDelayMs": 2000
}
```

Watchdog проверяет уже запущенное разрешенное приложение по полному пути через локальные Windows-механизмы, а не только по имени процесса. Если найден именно разрешенный `.exe`, новый экземпляр не запускается, а существующее окно выводится вперед. Если приложение свернуто, по умолчанию показываются уведомление и кнопка `Развернуть приложение`; автоматическое восстановление можно включить через `restoreIfMinimized: true`.

Для системных delegating-приложений Windows 11, например `C:\Windows\System32\notepad.exe`, watchdog сначала ищет точный путь, а затем использует fallback по имени процесса. Это предотвращает повторные запуски, когда System32-stub открывает фактический процесс из `WindowsApps`.
```

## requirements-build.txt

```text
pyinstaller==6.21.0
```

## RezhimKioska.spec

```python
# -*- mode: python ; coding: utf-8 -*-

# PyInstaller specification for "Режим киоска".
# config/kiosk.json is bundled so RUN/exe startup has a safe default template.

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("config/kiosk.json", "config")],
    hiddenimports=["tkinter"],
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
    name="RezhimKioska",
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
)
```

## scripts\apply-test-kiosk.ps1

```powershell
$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Users\impal\PycharmProjects\PythonKiosk"
$ExePath = Join-Path $ProjectRoot "release\RezhimKioska-inputfix.exe"
$ConfigPath = Join-Path $ProjectRoot "config\kiosk.json"
$LogPath = Join-Path $ProjectRoot "apply-test-kiosk.log"

function Write-Step {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    $line | Tee-Object -FilePath $LogPath -Append
}

Write-Step "=== apply-test-kiosk started ==="
Write-Step "ProjectRoot: $ProjectRoot"
Write-Step "ExePath: $ExePath"
Write-Step "ConfigPath: $ConfigPath"

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Step "ERROR: elevated administrator rights are required."
    throw "Отказано в доступе. Для выполнения действия требуются права администратора Windows."
}

if (-not (Test-Path -LiteralPath $ExePath)) {
    Write-Step "ERROR: exe not found."
    throw "Exe not found: $ExePath"
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    Write-Step "ERROR: config not found."
    throw "Config not found: $ConfigPath"
}

Write-Step "Running install --apply for operator test."
& $ExePath install --config $ConfigPath --apply 2>&1 | Tee-Object -FilePath $LogPath -Append
if ($LASTEXITCODE -ne 0) {
    Write-Step "ERROR: install failed with exit code $LASTEXITCODE."
    exit $LASTEXITCODE
}

Write-Step "Current sessions before optional test logoff:"
query user 2>&1 | Tee-Object -FilePath $LogPath -Append

$testSession = (query user 2>$null | Select-String -Pattern "^\s*test\s+|^\s*>\s*test\s+").ToString()
if ($testSession) {
    $parts = $testSession -split "\s+"
    $sessionId = $null
    foreach ($part in $parts) {
        if ($part -match "^\d+$") {
            $sessionId = $part
        }
    }
    if ($sessionId) {
        Write-Step "Logging off test session id $sessionId so the next login starts the new shell."
        logoff $sessionId 2>&1 | Tee-Object -FilePath $LogPath -Append
    }
}

Write-Step "Current sessions after apply:"
query user 2>&1 | Tee-Object -FilePath $LogPath -Append
Write-Step "=== apply-test-kiosk finished ==="
```

## scripts\create-operator-user.ps1

```powershell
param(
    [string]$UserName = "KioskOperator",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

function Decode-Text([string]$Base64) {
    return [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($Base64))
}

function Write-Ru([string]$Base64, [object[]]$Arguments = @()) {
    $Text = Decode-Text $Base64
    if ($Arguments.Count -gt 0) {
        $Text = [System.String]::Format($Text, $Arguments)
    }
    Write-Host $Text
}

if (-not $Apply) {
    Write-Ru "RFJZLVJVTjog0LHRg9C00LXRgiDRgdC+0LfQtNCw0L3QsCDQuNC70Lgg0L/RgNC+0LLQtdGA0LXQvdCwINC70L7QutCw0LvRjNC90LDRjyDRg9GH0LXRgtC90LDRjyDQt9Cw0L/QuNGB0Ywg0L7Qv9C10YDQsNGC0L7RgNCwINCx0LXQtyDQv9GA0LDQsiDQsNC00LzQuNC90LjRgdGC0YDQsNGC0L7RgNCwOiB7MH0=" @($UserName)
    Write-Ru "0JfQsNC/0YPRgdC60LDQudGC0LUg0YEgLUFwcGx5INGC0L7Qu9GM0LrQviDQv9C+0YHQu9C1INC/0YDQvtCy0LXRgNC60Lgg0L/Qu9Cw0L3QsCDQuCByZXN0b3JlLg=="
    exit 0
}

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    throw (Decode-Text "0J3Rg9C20L3RiyDQv9GA0LDQstCwINCw0LTQvNC40L3QuNGB0YLRgNCw0YLQvtGA0LAu")
}

if (Get-Command New-LocalUser -ErrorAction SilentlyContinue) {
    if (-not (Get-LocalUser -Name $UserName -ErrorAction SilentlyContinue)) {
        $prompt = [System.String]::Format((Decode-Text "0J/QsNGA0L7Qu9GMINC00LvRjyB7MH0="), $UserName)
        $password = Read-Host $prompt -AsSecureString
        $description = Decode-Text "0J7Qv9C10YDQsNGC0L7RgCBQeXRob25LaW9zaw=="
        New-LocalUser -Name $UserName -Password $password -Description $description
    }
    Remove-LocalGroupMember -Group "Administrators" -Member $UserName -ErrorAction SilentlyContinue
} else {
    Write-Ru "0J7QsdC90LDRgNGD0LbQtdC90LAgbGVnYWN5LdGB0LjRgdGC0LXQvNCwLiDQodC+0LfQtNCw0LnRgtC1INC/0L7Qu9GM0LfQvtCy0LDRgtC10LvRjyDQstGA0YPRh9C90YPRjiDRh9C10YDQtdC3IENvbXB1dGVyIE1hbmFnZW1lbnQg0LjQu9C4ICduZXQgdXNlcicu"
}
```

## scripts\install.ps1

```powershell
param(
    [string]$Config = "$PSScriptRoot\..\config\kiosk.json",
    [string]$StateDir = "",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
Set-Location $ProjectRoot

if ($Apply) {
    if ($StateDir) {
        python main.py install --config $Config --state-dir $StateDir --apply
    } else {
        python main.py install --config $Config --apply
    }
} else {
    if ($StateDir) {
        python main.py install --config $Config --state-dir $StateDir
    } else {
        python main.py install --config $Config
    }
}
```

## scripts\restore.ps1

```powershell
param(
    [string]$Config = "$PSScriptRoot\..\config\kiosk.json",
    [string]$StateDir = "",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
Set-Location $ProjectRoot

if ($Apply) {
    if ($StateDir) {
        python main.py restore --config $Config --state-dir $StateDir --apply
    } else {
        python main.py restore --config $Config --apply
    }
} else {
    if ($StateDir) {
        python main.py restore --config $Config --state-dir $StateDir
    } else {
        python main.py restore --config $Config
    }
}
```

## scripts\test-lab-setup.ps1

```powershell
param(
    [string]$UserName = "KioskOperator"
)

$ErrorActionPreference = "Stop"

function Decode-Text([string]$Base64) {
    return [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($Base64))
}

function Write-Ru([string]$Base64, [object[]]$Arguments = @()) {
    $Text = Decode-Text $Base64
    if ($Arguments.Count -gt 0) {
        $Text = [System.String]::Format($Text, $Arguments)
    }
    Write-Host $Text
}

Write-Ru "0KfQtdC6LdC70LjRgdGCINCx0LXQt9C+0L/QsNGB0L3QvtC5INC70LDQsdC+0YDQsNGC0L7RgNC90L7QuSDQv9GA0L7QstC10YDQutC4Og=="
Write-Ru "MS4g0JjRgdC/0L7Qu9GM0LfRg9C50YLQtSDQvtGC0LTQtdC70YzQvdGD0Y4g0LvQvtC60LDQu9GM0L3Rg9GOINGD0YfQtdGC0L3Rg9GOINC30LDQv9C40YHRjCDQvtC/0LXRgNCw0YLQvtGA0LAg0LHQtdC3INC/0YDQsNCyINCw0LTQvNC40L3QuNGB0YLRgNCw0YLQvtGA0LA6IHswfQ==" @($UserName)
Write-Ru "Mi4g0J3QtSDQv9GA0LjQvNC10L3Rj9C50YLQtSDQvdCw0YHRgtGA0L7QudC60Lgg0LrQuNC+0YHQutCwINC6INC+0YHQvdC+0LLQvdC+0Lkg0YPRh9C10YLQvdC+0Lkg0LfQsNC/0LjRgdC4Lg=="
Write-Ru "My4g0KHQvdCw0YfQsNC70LAg0LfQsNC/0YPRgdGC0LjRgtC1IGluc3RhbGwucHMxINCx0LXQtyAtQXBwbHku"
Write-Ru "NC4g0JTQviDQv9GA0LjQvNC10L3QtdC90LjRjyDQv9GA0L7QstC10YDRjNGC0LUg0LLRi9Cy0L7QtCByZXN0b3JlLnBzMSDQsiBkcnktcnVuLg=="
Write-Ru "NS4g0JTQtdGA0LbQuNGC0LUg0LTQvtGB0YLRg9C/0L3QvtC5INCw0LTQvNC40L3QuNGB0YLRgNCw0YLQuNCy0L3Rg9GOINGD0YfQtdGC0L3Rg9GOINC30LDQv9C40YHRjCDQtNC70Y8g0L7RgtC60LDRgtCwLg=="
```

## src\Common\README.md

```markdown
Common package boundary.

Shared configuration and backup code currently lives in `python_kiosk.config`
and `python_kiosk.backup_store`.
```

## src\Configurator\README.md

```markdown
Configurator package boundary.

Runtime implementation currently lives in `python_kiosk.configurator`.
PowerShell entry points are in `scripts/install.ps1` and
`scripts/create-operator-user.ps1`.
```

## src\KioskLauncher\README.md

```markdown
KioskLauncher package boundary.

Runtime implementation currently lives in `python_kiosk.launcher`,
`python_kiosk.process_watchdog`, `python_kiosk.shell_ui`, and
`python_kiosk.window_control`.
```

## src\Logging\README.md

```markdown
Logging package boundary.

Runtime implementation currently lives in `python_kiosk.logging_service`.
```

## src\PolicyEngine\README.md

```markdown
PolicyEngine package boundary.

Runtime implementation currently lives in `python_kiosk.policy_engine`,
`python_kiosk.policy_plan`, and `python_kiosk.platform_detect`.
```

## src\RestoreTool\README.md

```markdown
RestoreTool package boundary.

Runtime implementation currently lives in `python_kiosk.restore_tool`.
PowerShell entry point is `scripts/restore.ps1`.
```

## src\Security\README.md

```markdown
Security package boundary.

Runtime implementation currently lives in `python_kiosk.security` and
`python_kiosk.local_admin_auth`.
```

## src\Tests\README.md

```markdown
Tests package boundary.

Executable tests live in the top-level `tests` package.
```

## tests\__init__.py

```python
from . import _test_environment  # noqa: F401
```

## tests\_test_environment.py

```python
import os
import tempfile


TEST_LOG_DIRECTORY = os.path.join(tempfile.gettempdir(), "python-kiosk-tests")
TEST_LOG_PATH = os.path.join(TEST_LOG_DIRECTORY, "kiosk.log")

os.environ.setdefault("PYTHONKIOSK_LOG_PATH", TEST_LOG_PATH)
os.environ.setdefault("PYTHONKIOSK_SESSION_ID", "unit-tests")
```

## tests\test_admin_actions.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import os
import tempfile
import unittest

from python_kiosk.admin_actions import AdminActions
from python_kiosk.config import KioskConfig, load_config, save_config
from python_kiosk.security import hash_password, verify_password
from python_kiosk.system_backend import ADMIN_RIGHTS_REQUIRED_MESSAGE


class FakeBackend(object):
    def __init__(self, admin):
        self.admin = admin

    def is_admin(self):
        return self.admin


class AdminActionsTests(unittest.TestCase):
    def _write_config(self, path, app_path):
        password = hash_password("admin-pass", iterations=1000)
        config = KioskConfig(
            app_path=app_path,
            operator_user="KioskOperator",
            admin_password_hash=password["hash"],
            admin_password_salt=password["salt"],
            admin_password_algorithm=password["algorithm"],
            admin_password_iterations=password["iterations"],
        )
        save_config(config, path)

    def test_set_allowed_app_path_requires_existing_exe(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        app_path = os.path.join(temp_dir, "allowed.exe")
        open(app_path, "w").close()
        self._write_config(config_path, app_path)
        actions = AdminActions(config_path, backend=FakeBackend(admin=True))

        new_app_path = os.path.join(temp_dir, "new.exe")
        open(new_app_path, "w").close()
        actions.set_allowed_app_path(new_app_path)

        self.assertEqual(new_app_path, load_config(config_path).app_path)

    def test_set_allowed_app_path_refuses_without_windows_admin_rights(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        app_path = os.path.join(temp_dir, "allowed.exe")
        open(app_path, "w").close()
        self._write_config(config_path, app_path)
        actions = AdminActions(config_path, backend=FakeBackend(admin=False))

        new_app_path = os.path.join(temp_dir, "new.exe")
        open(new_app_path, "w").close()
        with self.assertRaises(PermissionError) as error:
            actions.set_allowed_app_path(new_app_path)

        self.assertEqual(ADMIN_RIGHTS_REQUIRED_MESSAGE, str(error.exception))
        self.assertEqual(app_path, load_config(config_path).app_path)

    def test_change_kiosk_admin_password_rehashes_with_new_salt(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        app_path = os.path.join(temp_dir, "allowed.exe")
        open(app_path, "w").close()
        self._write_config(config_path, app_path)
        old_config = load_config(config_path)
        actions = AdminActions(config_path, backend=FakeBackend(admin=True))

        actions.change_kiosk_admin_password("new-pass")

        new_config = load_config(config_path)
        self.assertNotEqual(old_config.admin_password_salt, new_config.admin_password_salt)
        self.assertTrue(
            verify_password(
                "new-pass",
                {
                    "iterations": new_config.admin_password_iterations,
                    "salt": new_config.admin_password_salt,
                    "hash": new_config.admin_password_hash,
                },
            )
        )


if __name__ == "__main__":
    unittest.main()
```

## tests\test_admin_session.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.admin_session import AdminSession


class FakeClock(object):
    def __init__(self, now=100.0):
        self.now = now

    def __call__(self):
        return self.now


class FakeLogger(object):
    def __init__(self):
        self.events = []

    def info(self, event, **data):
        self.events.append(("info", event, data))

    def warning(self, event, **data):
        self.events.append(("warning", event, data))


class AdminSessionTests(unittest.TestCase):
    def test_session_starts_with_limited_lifetime(self):
        clock = FakeClock()
        logger = FakeLogger()
        session = AdminSession(timeout_seconds=300, time_func=clock, logger=logger)

        session.start("Admin")

        self.assertTrue(session.is_active())
        self.assertEqual("Admin", session.username)
        self.assertEqual(400.0, session.expires_at)
        self.assertIn(("info", "admin.session_started"), [(level, event) for level, event, _ in logger.events])

    def test_session_times_out_and_logs_return_to_kiosk(self):
        clock = FakeClock()
        logger = FakeLogger()
        session = AdminSession(timeout_seconds=10, time_func=clock, logger=logger)
        session.start("Admin")

        clock.now = 111.0

        self.assertFalse(session.is_active())
        self.assertIn(("warning", "admin.session_timeout"), [(level, event) for level, event, _ in logger.events])

    def test_session_close_returns_to_kiosk(self):
        clock = FakeClock()
        logger = FakeLogger()
        session = AdminSession(timeout_seconds=300, time_func=clock, logger=logger)
        session.start("Admin")

        session.close(reason="manual")

        self.assertFalse(session.is_active())
        self.assertIn(("info", "admin.session_closed"), [(level, event) for level, event, _ in logger.events])

    def test_log_data_does_not_include_password_or_token(self):
        session = AdminSession(timeout_seconds=300, time_func=FakeClock())
        session.start("Admin")

        text = str(session.to_log_data())

        self.assertIn("Admin", text)
        self.assertNotIn("password", text.lower())
        self.assertNotIn("token", text.lower())


if __name__ == "__main__":
    unittest.main()
```

## tests\test_cli.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import os
import sys
import tempfile
import unittest
from unittest import mock

import main
from python_kiosk.config import load_config, save_config
from python_kiosk.logging_service import configured_log_path
from python_kiosk.system_backend import ADMIN_RIGHTS_REQUIRED_MESSAGE


class CliTests(unittest.TestCase):
    def test_frozen_default_config_can_resolve_from_pyinstaller_bundle(self):
        temp_dir = tempfile.mkdtemp()
        bundle_dir = os.path.join(temp_dir, "bundle")
        os.mkdir(bundle_dir)
        bundled_config = os.path.join(bundle_dir, "kiosk_config.json")
        open(bundled_config, "w").close()

        with mock.patch.object(main, "DEFAULT_CONFIG_PATH", "kiosk_config.json"):
            with mock.patch.object(main.sys, "frozen", True, create=True):
                with mock.patch.object(main.sys, "_MEIPASS", bundle_dir, create=True):
                    with mock.patch.object(
                        main.sys,
                        "executable",
                        os.path.join(temp_dir, "RezhimKioska.exe"),
                    ):
                        self.assertEqual(bundled_config, main.resolve_default_config_path())

    def test_no_arguments_launches_gui_shell_from_default_config(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        output = []
        shell_calls = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )

        with mock.patch.object(main, "DEFAULT_CONFIG_PATH", config_path):
            code = main.main(
                [],
                stdout=output.append,
                shell_runner=lambda launcher: shell_calls.append(launcher.config.app_path),
            )

        self.assertEqual(0, code)
        self.assertEqual([sys.executable], shell_calls)
        self.assertEqual([], output)

    def test_init_writes_config_and_check_password_verifies_it(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")

        init_code = main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        check_output = []
        check_code = main.main(
            [
                "check-password",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=check_output.append,
        )

        self.assertEqual(0, init_code)
        self.assertEqual(0, check_code)
        self.assertTrue(os.path.exists(config_path))
        self.assertIn("Пароль принят", "\n".join(check_output))

    def test_plan_prints_dry_run_policy_plan(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        output = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        code = main.main(["plan", "--config", config_path], stdout=output.append)

        self.assertEqual(0, code)
        self.assertIn("Режим: dry-run", "\n".join(output))

    def test_install_command_is_dry_run_by_default_and_creates_backup(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        output = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        code = main.main(["install", "--config", config_path], stdout=output.append)

        joined = "\n".join(output)
        self.assertEqual(0, code)
        self.assertIn("Режим: dry-run", joined)
        self.assertIn("create_backup", joined)
        self.assertIn("Backup:", joined)

    def test_launcher_shell_command_points_to_configured_launch_command(self):
        config_path = os.path.join(tempfile.mkdtemp(), "kiosk.json")

        command = main.build_launcher_shell_command(config_path)

        self.assertIn("launch", command)
        self.assertIn("--config", command)
        self.assertIn(os.path.abspath(config_path), command)

    def test_restore_command_is_dry_run_by_default_and_targets_explorer(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        output = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        code = main.main(["restore", "--config", config_path], stdout=output.append)

        joined = "\n".join(output)
        self.assertEqual(0, code)
        self.assertIn("Режим: dry-run", joined)
        self.assertIn("restore_operator_shell", joined)
        self.assertIn("explorer.exe", joined)

    def test_set_app_command_refuses_without_admin_rights(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        app_path = os.path.join(temp_dir, "allowed.exe")
        open(app_path, "w").close()
        output = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        code = main.main(
            ["set-app", "--config", config_path, "--app-path", app_path],
            stdout=output.append,
        )

        self.assertEqual(1, code)
        self.assertIn(ADMIN_RIGHTS_REQUIRED_MESSAGE, "\n".join(output))
        self.assertEqual(sys.executable, main.load_config(config_path).app_path)

    def test_change_password_command_refuses_without_admin_rights(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        output = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "old-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        code = main.main(
            ["change-password", "--config", config_path, "--password", "new-pass"],
            stdout=output.append,
        )

        self.assertEqual(1, code)
        self.assertIn(ADMIN_RIGHTS_REQUIRED_MESSAGE, "\n".join(output))

    def test_status_command_prints_profile_and_paths(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        output = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        code = main.main(["status", "--config", config_path], stdout=output.append)

        joined = "\n".join(output)
        self.assertEqual(0, code)
        self.assertIn("Оператор: Operator", joined)
        self.assertIn(sys.executable, joined)
        self.assertIn("Профиль политики:", joined)

    def test_launch_uses_gui_shell_by_default(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        shell_calls = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--password",
                "admin-pass",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )

        code = main.main(
            ["launch", "--config", config_path],
            stdout=lambda text: None,
            shell_runner=lambda launcher: shell_calls.append(launcher.config.app_path),
        )

        self.assertEqual(0, code)
        self.assertEqual([sys.executable], shell_calls)

    def test_launch_exits_when_same_config_instance_is_already_running(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        output = []
        shell_calls = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )

        class LockedGuard(object):
            acquired = False

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with mock.patch.object(main.SingleInstanceGuard, "for_operator", return_value=LockedGuard()):
            code = main.main(
                ["launch", "--config", config_path],
                stdout=output.append,
                shell_runner=lambda launcher: shell_calls.append(launcher),
            )

        self.assertEqual(0, code)
        self.assertEqual([], shell_calls)
        self.assertIn("Киоск уже запущен", "\n".join(output))

    def test_launch_single_instance_guard_is_scoped_to_operator(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        guards = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )

        class OpenGuard(object):
            acquired = True

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def guard_for_operator(operator_user):
            guards.append(operator_user)
            return OpenGuard()

        with mock.patch.object(main.SingleInstanceGuard, "for_operator", side_effect=guard_for_operator):
            main.main(
                ["launch", "--config", config_path],
                stdout=lambda text: None,
                shell_runner=lambda launcher: None,
            )

        self.assertEqual(["Operator"], guards)

    def test_recover_desktop_command_runs_current_session_recovery(self):
        output = []

        with mock.patch.object(
            main,
            "recover_current_desktop",
            return_value={"started_explorer": True, "restored_windows": [100]},
        ) as recovery:
            code = main.main(["recover-desktop"], stdout=output.append)

        self.assertEqual(0, code)
        self.assertTrue(recovery.called)
        self.assertIn("Рабочий стол текущей сессии восстановлен.", "\n".join(output))

    def test_log_path_command_prints_and_touches_diagnostic_log(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        log_dir = os.path.join(temp_dir, "logs")
        output = []

        main.main(
            [
                "init",
                "--app-path",
                sys.executable,
                "--operator",
                "Operator",
                "--config",
                config_path,
            ],
            stdout=lambda text: None,
        )
        config = load_config(config_path)
        config.logging["logDirectory"] = log_dir
        save_config(config, config_path)

        code = main.main(["log-path", "--config", config_path], stdout=output.append)

        self.assertEqual(0, code)
        self.assertIn(configured_log_path(config), "\n".join(output))
        with open(configured_log_path(config), "r", encoding="utf-8") as log_file:
            self.assertIn("diagnostic.log_ready", log_file.read())


if __name__ == "__main__":
    unittest.main()
```

## tests\test_config.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import os
import tempfile
import unittest

from python_kiosk.config import (
    DEFAULT_ALLOWED_APP_PATH,
    KioskConfig,
    ensure_default_config,
    load_config,
    save_config,
)


class ConfigTests(unittest.TestCase):
    def test_config_round_trips_through_json_file(self):
        config = KioskConfig(
            app_path=r"C:\Program Files\Vendor\App\app.exe",
            operator_user="Operator",
            admin_password_hash="hash-value",
            admin_password_salt="salt-value",
            policy_profile="win7_srp",
            restart_delay_seconds=3,
        )

        temp_dir = tempfile.mkdtemp()
        path = os.path.join(temp_dir, "kiosk.json")

        save_config(config, path)
        loaded = load_config(path)

        self.assertEqual(config.to_dict(), loaded.to_dict())

    def test_validate_rejects_missing_app_path(self):
        config = KioskConfig(
            app_path="",
            operator_user="Operator",
            admin_password_hash="hash",
            admin_password_salt="salt",
        )

        with self.assertRaises(ValueError) as error:
            config.validate()

        self.assertIn("app_path", str(error.exception))

    def test_validate_rejects_non_positive_restart_delay(self):
        config = KioskConfig(
            app_path=r"C:\App\app.exe",
            operator_user="Operator",
            admin_password_hash="hash",
            admin_password_salt="salt",
            restart_delay_seconds=0,
        )

        with self.assertRaises(ValueError) as error:
            config.validate()

        self.assertIn("restart_delay_seconds", str(error.exception))

    def test_password_iterations_round_trip_with_default(self):
        config = KioskConfig(
            app_path=r"C:\App\app.exe",
            operator_user="Operator",
            admin_password_hash="hash",
            admin_password_salt="salt",
        )

        data = config.to_dict()
        loaded = KioskConfig.from_dict(data)

        self.assertEqual(200000, loaded.admin_password_iterations)
        self.assertEqual("pbkdf2_hmac_sha256", loaded.admin_password_algorithm)

    def test_ensure_default_config_creates_required_nested_kiosk_json(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "config", "kiosk.json")

        created = ensure_default_config(config_path)
        loaded = load_config(config_path)

        self.assertEqual(config_path, created)
        self.assertTrue(os.path.exists(config_path))
        self.assertEqual(DEFAULT_ALLOWED_APP_PATH, loaded.allowed_application.path)
        self.assertEqual("KioskOperator", loaded.operator_user)
        self.assertFalse(loaded.allowed_application.restore_if_minimized)
        self.assertEqual(300, loaded.kiosk["adminSessionTimeoutSeconds"])
        self.assertTrue(loaded.kiosk["blockWinKey"])
        self.assertTrue(loaded.testing["requireBackupBeforeTest"])
        self.assertTrue(loaded.testing["restoreAfterTest"])
        self.assertTrue(loaded.testing["testOnlySeparateOperatorUser"])
        self.assertNotIn("windows_admin_password", loaded.to_dict())
        self.assertNotIn("password", loaded.to_dict().get("allowedApplication", {}))

    def test_load_config_reads_required_nested_model(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        with open(config_path, "w", encoding="utf-8") as config_file:
            config_file.write(
                """
{
  "operatorUser": "KioskOperator",
  "allowedApplication": {
    "path": "C:\\\\Windows\\\\System32\\\\notepad.exe",
    "arguments": "",
    "workingDirectory": "C:\\\\Windows\\\\System32",
    "restartOnExit": true,
    "bringToFront": true,
    "bringExistingToFront": true,
    "singleInstance": true,
    "restoreIfMinimized": true,
    "startMaximized": false,
    "restartDelayMs": 2000
  },
  "kiosk": {
    "blockDesktop": true,
    "disableStartMenu": true,
    "disableExplorer": true,
    "allowWinL": true,
    "blockWinKey": true,
    "adminSessionTimeoutSeconds": 300
  },
  "testing": {
    "requireBackupBeforeTest": true,
    "restoreAfterTest": true,
    "testOnlySeparateOperatorUser": true
  },
  "logging": {
    "logDirectory": "C:\\\\ProgramData\\\\Kiosk\\\\Logs",
    "level": "Info"
  }
}
"""
            )

        config = load_config(config_path)

        self.assertEqual(r"C:\Windows\System32\notepad.exe", config.app_path)
        self.assertEqual("", config.allowed_application.arguments)
        self.assertEqual(r"C:\Windows\System32", config.allowed_application.working_directory)
        self.assertTrue(config.allowed_application.restart_on_exit)
        self.assertTrue(config.allowed_application.bring_to_front)
        self.assertTrue(config.allowed_application.bring_existing_to_front)
        self.assertTrue(config.allowed_application.single_instance)
        self.assertTrue(config.allowed_application.restore_if_minimized)
        self.assertFalse(config.allowed_application.start_maximized)
        self.assertEqual(2000, config.allowed_application.restart_delay_ms)
        self.assertTrue(config.kiosk["blockWinKey"])
        self.assertTrue(config.testing["requireBackupBeforeTest"])

    def test_save_config_writes_nested_model_without_kiosk_password_requirement(self):
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "kiosk.json")
        config = KioskConfig(
            app_path=r"C:\Windows\System32\notepad.exe",
            operator_user="KioskOperator",
        )

        save_config(config, config_path)

        with open(config_path, "r", encoding="utf-8") as config_file:
            text = config_file.read()
        self.assertIn('"allowedApplication"', text)
        self.assertIn('"operatorUser"', text)
        self.assertIn('"singleInstance": true', text)
        self.assertIn('"restartDelayMs": 2000', text)
        self.assertNotIn("admin_password_hash", text)


if __name__ == "__main__":
    unittest.main()
```

## tests\test_configurator_restore.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import os
import tempfile
import unittest

from python_kiosk.config import KioskConfig
from python_kiosk.configurator import Configurator
from python_kiosk.restore_tool import RestoreTool
from python_kiosk.security import hash_password
from python_kiosk.system_backend import WindowsSystemBackend


class FakeSystemBackend(object):
    def __init__(self, admin=True, fail_on=None):
        self.admin = admin
        self.fail_on = fail_on
        self.applied = []

    def is_admin(self):
        return self.admin

    def apply_operation(self, operation):
        self.applied.append(operation.name)
        if operation.name == self.fail_on:
            raise RuntimeError("boom")


class ConfiguratorRestoreTests(unittest.TestCase):
    def _config(self):
        password = hash_password("admin-pass", iterations=1000)
        return KioskConfig(
            app_path=r"C:\Windows\System32\notepad.exe",
            operator_user="KioskOperator",
            admin_password_hash=password["hash"],
            admin_password_salt=password["salt"],
            admin_password_algorithm=password["algorithm"],
            admin_password_iterations=password["iterations"],
        )

    def test_install_is_dry_run_by_default_and_creates_backup_plan(self):
        temp_dir = tempfile.mkdtemp()
        backend = FakeSystemBackend(admin=True)
        configurator = Configurator(backend=backend, state_dir=temp_dir)

        result = configurator.install(self._config(), apply=False)

        self.assertFalse(result.applied)
        self.assertTrue(os.path.exists(result.backup_path))
        self.assertEqual([], backend.applied)
        self.assertIn("create_backup", [op.name for op in result.plan.operations])

    def test_install_refuses_apply_without_admin_rights(self):
        backend = FakeSystemBackend(admin=False)
        configurator = Configurator(
            backend=backend,
            state_dir=tempfile.mkdtemp(),
        )

        with self.assertRaises(PermissionError) as error:
            configurator.install(self._config(), apply=True)

        self.assertEqual(
            "Отказано в доступе. Для выполнения действия требуются права администратора Windows.",
            str(error.exception),
        )
        self.assertEqual([], backend.applied)

    def test_restore_refuses_apply_without_admin_rights(self):
        backend = FakeSystemBackend(admin=False)
        restore = RestoreTool(
            backend=backend,
            state_dir=tempfile.mkdtemp(),
        )

        with self.assertRaises(PermissionError) as error:
            restore.restore(self._config(), apply=True)

        self.assertEqual(
            "Отказано в доступе. Для выполнения действия требуются права администратора Windows.",
            str(error.exception),
        )
        self.assertEqual([], backend.applied)

    def test_restore_is_dry_run_by_default_and_targets_explorer_shell(self):
        temp_dir = tempfile.mkdtemp()
        backend = FakeSystemBackend(admin=True)
        restore = RestoreTool(backend=backend, state_dir=temp_dir)

        result = restore.restore(self._config(), apply=False)

        self.assertFalse(result.applied)
        self.assertEqual([], backend.applied)
        self.assertIn("restore_operator_shell", [op.name for op in result.plan.operations])
        self.assertIn("explorer.exe", result.plan.to_text().lower())

    def test_install_apply_failure_attempts_safe_restore_plan(self):
        temp_dir = tempfile.mkdtemp()
        backend = FakeSystemBackend(admin=True, fail_on="set_operator_shell")
        configurator = Configurator(backend=backend, state_dir=temp_dir)
        config = self._config()

        with self.assertRaises(RuntimeError):
            configurator.install(config, apply=True)

        self.assertIn("set_operator_shell", backend.applied)
        self.assertIn("restore_operator_shell", backend.applied)
        self.assertIn("restore_operator_policies", backend.applied)

    def test_system_backend_rejects_forbidden_operations(self):
        class Operation(object):
            name = "stop_services"

        with self.assertRaises(ValueError):
            WindowsSystemBackend().apply_operation(Operation())


if __name__ == "__main__":
    unittest.main()
```

## tests\test_launcher.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest
from unittest import mock

from python_kiosk.config import KioskConfig
from python_kiosk.launcher import KioskLauncher
from python_kiosk.local_admin_auth import AuthResult, AUTH_SUCCESS
from python_kiosk.security import hash_password


class LauncherTests(unittest.TestCase):
    def _config(self, app_path=r"C:\Missing\app.exe"):
        password = hash_password("admin-pass", iterations=1000)
        return KioskConfig(
            app_path=app_path,
            operator_user="Operator",
            admin_password_hash=password["hash"],
            admin_password_salt=password["salt"],
            admin_password_algorithm=password["algorithm"],
            admin_password_iterations=password["iterations"],
            logging={"logDirectory": _test_environment.TEST_LOG_DIRECTORY},
        )

    def test_admin_password_is_required_for_unlock(self):
        launcher = KioskLauncher(self._config())

        self.assertTrue(launcher.verify_admin_password("admin-pass"))
        self.assertFalse(launcher.verify_admin_password("wrong"))

    def test_local_admin_credentials_are_required_for_desktop_unlock(self):
        class FakeAuthenticator(object):
            def __init__(self):
                self.calls = []

            def authenticate(self, username, password):
                self.calls.append((username, password))
                return username == "Admin" and password == "secret"

        authenticator = FakeAuthenticator()
        launcher = KioskLauncher(self._config(), admin_authenticator=authenticator)

        self.assertTrue(launcher.verify_admin_credentials("Admin", "secret"))
        self.assertFalse(launcher.verify_admin_credentials("Operator", "secret"))
        self.assertEqual(
            [("Admin", "secret"), ("Operator", "secret")],
            authenticator.calls,
        )

    def test_launcher_exposes_structured_admin_credential_result(self):
        class FakeAuthenticator(object):
            def authenticate_result(self, username, password):
                return AuthResult(
                    AUTH_SUCCESS,
                    username=username,
                    domain=".",
                    message="Доступ разрешён.",
                )

        launcher = KioskLauncher(
            self._config(),
            admin_authenticator=FakeAuthenticator(),
        )

        result = launcher.verify_admin_credentials_result("Admin", "secret")

        self.assertTrue(result.success)
        self.assertEqual("Admin", result.username)

    def test_create_watchdog_rejects_missing_allowed_executable(self):
        launcher = KioskLauncher(self._config(app_path=r"C:\Missing\app.exe"))

        with self.assertRaises(ValueError) as error:
            launcher.create_watchdog()

        self.assertIn("Разрешенное приложение не найдено", str(error.exception))

    def test_create_watchdog_passes_duplicate_process_checker(self):
        created = []

        class FakeWatchdog(object):
            def __init__(
                self,
                command,
                restart_delay_seconds,
                process_running,
                working_directory=None,
                restart_on_exit=True,
                wait_for_input_idle=True,
                start_maximized=False,
                single_instance=True,
                bring_existing_to_front=None,
                logger=None,
            ):
                created.append(
                    {
                        "command": command,
                        "restart_delay_seconds": restart_delay_seconds,
                        "process_running": process_running,
                        "working_directory": working_directory,
                        "restart_on_exit": restart_on_exit,
                        "wait_for_input_idle": wait_for_input_idle,
                        "start_maximized": start_maximized,
                        "single_instance": single_instance,
                        "bring_existing_to_front": bring_existing_to_front,
                        "logger": logger,
                    }
                )

        config = KioskConfig(
            app_path=r"C:\Windows\System32\notepad.exe",
            operator_user="Operator",
            logging={"logDirectory": _test_environment.TEST_LOG_DIRECTORY},
        )
        config.allowed_application.arguments = "--safe-mode"
        config.allowed_application.working_directory = r"C:\Windows\System32"
        config.allowed_application.restart_on_exit = False
        config.allowed_application.start_maximized = True
        config.allowed_application.single_instance = True
        config.allowed_application.bring_existing_to_front = True
        config.allowed_application.restart_delay_ms = 1500
        launcher = KioskLauncher(config, watchdog_class=FakeWatchdog)

        with mock.patch("python_kiosk.launcher.os.path.isfile", return_value=True):
            launcher.create_watchdog()

        self.assertEqual(
            [r"C:\Windows\System32\notepad.exe", "--safe-mode"],
            created[0]["command"],
        )
        self.assertEqual(r"C:\Windows\System32", created[0]["working_directory"])
        self.assertFalse(created[0]["restart_on_exit"])
        self.assertTrue(created[0]["start_maximized"])
        self.assertEqual(1.5, created[0]["restart_delay_seconds"])
        self.assertTrue(created[0]["single_instance"])
        self.assertTrue(callable(created[0]["bring_existing_to_front"]))
        self.assertTrue(callable(created[0]["process_running"]))


if __name__ == "__main__":
    unittest.main()
```

## tests\test_local_admin_auth.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.local_admin_auth import (
    AUTH_BAD_CREDENTIALS,
    AUTH_NOT_ADMIN,
    AUTH_SUCCESS,
    AUTH_WINDOWS_ERROR,
    LocalAdminAuthenticator,
    parse_windows_account_name,
)


class FakeWindowsAuthBackend(object):
    def __init__(self, accepted=None, admins=None, logon_error=None, admin_error=None):
        self.accepted = accepted or set()
        self.admins = admins or set()
        self.logon_error = logon_error
        self.admin_error = admin_error
        self.calls = []

    def logon_user(self, username, domain, password):
        self.calls.append(("logon", username, domain, password))
        if self.logon_error is not None:
            raise self.logon_error
        token = (domain, username)
        return token if token in self.accepted else None

    def is_local_admin(self, token):
        self.calls.append(("admin", token))
        if self.admin_error is not None:
            raise self.admin_error
        return token in self.admins

    def close_token(self, token):
        self.calls.append(("close", token))


class LocalAdminAuthTests(unittest.TestCase):
    def test_parse_account_name_defaults_to_local_computer(self):
        self.assertEqual((".", "Admin"), parse_windows_account_name("Admin"))
        self.assertEqual((".", "Admin"), parse_windows_account_name(".\\Admin"))
        self.assertEqual(("PC", "Admin"), parse_windows_account_name("PC\\Admin"))

    def test_authenticate_accepts_local_admin_credentials(self):
        backend = FakeWindowsAuthBackend(
            accepted={(".", "Admin")},
            admins={(".", "Admin")},
        )
        authenticator = LocalAdminAuthenticator(backend=backend)

        self.assertTrue(authenticator.authenticate("Admin", "secret"))
        self.assertEqual(
            [
                ("logon", "Admin", ".", "secret"),
                ("admin", (".", "Admin")),
                ("close", (".", "Admin")),
            ],
            backend.calls,
        )

    def test_authenticate_rejects_non_admin_even_with_valid_password(self):
        backend = FakeWindowsAuthBackend(accepted={(".", "Operator")}, admins=set())
        authenticator = LocalAdminAuthenticator(backend=backend)

        self.assertFalse(authenticator.authenticate(".\\Operator", "secret"))
        self.assertIn(("close", (".", "Operator")), backend.calls)

    def test_authenticate_rejects_blank_credentials(self):
        authenticator = LocalAdminAuthenticator(backend=FakeWindowsAuthBackend())

        self.assertFalse(authenticator.authenticate("", "secret"))
        self.assertFalse(authenticator.authenticate("Admin", ""))

    def test_authenticate_result_accepts_local_admin_credentials(self):
        backend = FakeWindowsAuthBackend(
            accepted={(".", "Admin")},
            admins={(".", "Admin")},
        )
        authenticator = LocalAdminAuthenticator(backend=backend)

        result = authenticator.authenticate_result("Admin", "secret")

        self.assertEqual(AUTH_SUCCESS, result.code)
        self.assertTrue(result.success)
        self.assertEqual("Admin", result.username)
        self.assertEqual(".", result.domain)
        self.assertNotIn("secret", str(result.to_log_data()))

    def test_authenticate_result_rejects_bad_credentials(self):
        backend = FakeWindowsAuthBackend()
        authenticator = LocalAdminAuthenticator(backend=backend)

        result = authenticator.authenticate_result("Admin", "wrong")

        self.assertEqual(AUTH_BAD_CREDENTIALS, result.code)
        self.assertFalse(result.success)
        self.assertEqual(
            "Отказано в доступе. Неверное имя пользователя или пароль.",
            result.message,
        )

    def test_authenticate_result_rejects_non_admin_credentials(self):
        backend = FakeWindowsAuthBackend(accepted={(".", "Operator")}, admins=set())
        authenticator = LocalAdminAuthenticator(backend=backend)

        result = authenticator.authenticate_result(".\\Operator", "secret")

        self.assertEqual(AUTH_NOT_ADMIN, result.code)
        self.assertFalse(result.success)
        self.assertEqual(
            "Отказано в доступе. Указанная учётная запись не является администратором Windows.",
            result.message,
        )
        self.assertIn(("close", (".", "Operator")), backend.calls)

    def test_authenticate_result_reports_windows_api_error_and_closes_token(self):
        backend = FakeWindowsAuthBackend(
            accepted={(".", "Admin")},
            admins={(".", "Admin")},
            admin_error=OSError("api failed"),
        )
        authenticator = LocalAdminAuthenticator(backend=backend)

        result = authenticator.authenticate_result("Admin", "secret")

        self.assertEqual(AUTH_WINDOWS_ERROR, result.code)
        self.assertFalse(result.success)
        self.assertIn("ошибка Windows/API", result.message)
        self.assertIn(("close", (".", "Admin")), backend.calls)


if __name__ == "__main__":
    unittest.main()
```

## tests\test_logging_service.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import json
import os
import tempfile
import unittest
from unittest import mock

from python_kiosk.config import KioskConfig
from python_kiosk.logging_service import (
    KioskLogger,
    configured_log_path,
    create_configured_logger,
)


class LoggingServiceTests(unittest.TestCase):
    def test_logger_writes_json_lines_without_touching_system_logs(self):
        temp_dir = tempfile.mkdtemp()
        log_path = os.path.join(temp_dir, "kiosk.log")
        logger = KioskLogger(log_path=log_path)

        logger.info("install.plan", operator="Operator", dry_run=True)
        logger.error("policy.failed", error="access denied")

        with open(log_path, "r", encoding="utf-8") as log_file:
            rows = [json.loads(line) for line in log_file.read().splitlines()]

        self.assertEqual("install.plan", rows[0]["event"])
        self.assertEqual("info", rows[0]["level"])
        self.assertEqual(True, rows[0]["data"]["dry_run"])
        self.assertIn("session_id", rows[0])
        self.assertIn("process_id", rows[0])
        self.assertEqual("policy.failed", rows[1]["event"])
        self.assertEqual("error", rows[1]["level"])

    def test_default_logger_uses_environment_log_path_override(self):
        temp_dir = tempfile.mkdtemp()
        env_log_path = os.path.join(temp_dir, "isolated", "kiosk.log")

        with mock.patch.dict(os.environ, {"PYTHONKIOSK_LOG_PATH": env_log_path}):
            logger = KioskLogger()
            logger.info("environment.log_path")

        self.assertEqual(os.path.abspath(env_log_path), os.path.abspath(logger.log_path))
        self.assertTrue(os.path.exists(env_log_path))

    def test_logger_falls_back_to_user_home_when_primary_path_fails(self):
        temp_dir = tempfile.mkdtemp()
        primary_path = os.path.join(temp_dir, "primary", "kiosk.log")
        fallback_home = os.path.join(temp_dir, "home")
        real_open = open

        def guarded_open(path, *args, **kwargs):
            if path == os.path.abspath(primary_path):
                raise OSError("denied")
            return real_open(path, *args, **kwargs)

        with mock.patch("python_kiosk.logging_service.open", guarded_open, create=True):
            with mock.patch(
                "python_kiosk.logging_service.os.path.expanduser",
                return_value=fallback_home,
            ):
                KioskLogger(primary_path).info("fallback.event")

        fallback_path = os.path.join(
            fallback_home,
            "PythonKiosk",
            "logs",
            "kiosk.log",
        )
        self.assertTrue(os.path.exists(fallback_path))

    def test_logger_rotates_when_file_exceeds_limit(self):
        temp_dir = tempfile.mkdtemp()
        log_path = os.path.join(temp_dir, "kiosk.log")
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write("x" * 20)

        logger = KioskLogger(log_path=log_path, max_bytes=10, backup_count=2)
        logger.info("rotate.event")

        self.assertTrue(os.path.exists(log_path))
        self.assertTrue(os.path.exists(log_path + ".1"))
        with open(log_path, "r", encoding="utf-8") as log_file:
            self.assertIn("rotate.event", log_file.read())

    def test_logger_redacts_sensitive_fields(self):
        temp_dir = tempfile.mkdtemp()
        log_path = os.path.join(temp_dir, "kiosk.log")
        logger = KioskLogger(log_path=log_path, session_id="test-session")

        logger.warning(
            "admin.unlock_denied",
            username="Admin",
            password="secret",
            nested={"admin_password": "another-secret"},
        )

        with open(log_path, "r", encoding="utf-8") as log_file:
            row = json.loads(log_file.read().splitlines()[0])

        self.assertEqual("test-session", row["session_id"])
        self.assertEqual("***REDACTED***", row["data"]["password"])
        self.assertEqual("***REDACTED***", row["data"]["nested"]["admin_password"])
        self.assertNotIn("secret", json.dumps(row, ensure_ascii=False))

    def test_configured_logger_uses_config_log_directory(self):
        temp_dir = tempfile.mkdtemp()
        config = KioskConfig(logging={"logDirectory": temp_dir, "level": "Debug"})

        with mock.patch.dict(os.environ, {"PYTHONKIOSK_LOG_PATH": ""}):
            logger = create_configured_logger(config, session_id="configured")
            logger.info("diagnostic.test")
            configured_path = configured_log_path(config)

        self.assertEqual(os.path.join(temp_dir, "kiosk.log"), configured_path)
        with open(os.path.join(temp_dir, "kiosk.log"), "r", encoding="utf-8") as log_file:
            row = json.loads(log_file.read().splitlines()[0])
        self.assertEqual("configured", row["session_id"])
        self.assertEqual("diagnostic.test", row["event"])

    def test_configured_logger_uses_environment_log_path_override(self):
        temp_dir = tempfile.mkdtemp()
        env_log_path = os.path.join(temp_dir, "configured", "kiosk.log")
        config = KioskConfig(logging={"logDirectory": r"C:\ProgramData\Kiosk\Logs"})

        with mock.patch.dict(os.environ, {"PYTHONKIOSK_LOG_PATH": env_log_path}):
            logger = create_configured_logger(config, session_id="configured-env")
            logger.info("configured.environment")

        self.assertEqual(os.path.abspath(env_log_path), os.path.abspath(logger.log_path))
        self.assertTrue(os.path.exists(env_log_path))


if __name__ == "__main__":
    unittest.main()
```

## tests\test_platform_detect.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.platform_detect import WindowsInfo, select_policy_profile


class PlatformDetectionTests(unittest.TestCase):
    def test_xp_uses_legacy_profile(self):
        info = WindowsInfo(major=5, minor=1, build=2600, edition="Professional")

        self.assertEqual("xp_legacy", select_policy_profile(info))

    def test_windows_7_professional_uses_srp_profile(self):
        info = WindowsInfo(major=6, minor=1, build=7601, edition="Professional")

        self.assertEqual("win7_srp", select_policy_profile(info))

    def test_windows_10_home_uses_home_fallback(self):
        info = WindowsInfo(major=10, minor=0, build=19045, edition="Home")

        self.assertEqual("home_fallback", select_policy_profile(info))

    def test_windows_10_pro_uses_applocker_profile(self):
        info = WindowsInfo(major=10, minor=0, build=19045, edition="Professional")

        self.assertEqual("win10_applocker", select_policy_profile(info))

    def test_windows_10_enterprise_uses_shell_launcher_profile(self):
        info = WindowsInfo(major=10, minor=0, build=19045, edition="Enterprise")

        self.assertEqual("win10_shelllauncher", select_policy_profile(info))


if __name__ == "__main__":
    unittest.main()
```

## tests\test_policy_engine.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import os
import unittest

from python_kiosk.config import KioskConfig
from python_kiosk.platform_detect import WindowsInfo
from python_kiosk.policy_engine import PolicyEngine
from python_kiosk.security import hash_password


class PolicyEngineTests(unittest.TestCase):
    def _config(self):
        password = hash_password("admin-pass", iterations=1000)
        return KioskConfig(
            app_path=r"C:\Windows\System32\notepad.exe",
            operator_user="KioskOperator",
            admin_password_hash=password["hash"],
            admin_password_salt=password["salt"],
            admin_password_algorithm=password["algorithm"],
            admin_password_iterations=password["iterations"],
        )

    def test_builds_reversible_operator_only_install_plan(self):
        engine = PolicyEngine()
        plan = engine.build_install_plan(
            self._config(),
            WindowsInfo(10, 0, 22631, "Home", "Microsoft Windows 11 Home"),
            launcher_command=r'"C:\Kiosk\RezhimKioska.exe" launch --config "C:\Kiosk\config\kiosk.json"',
        )

        operation_names = [operation.name for operation in plan.operations]
        shell_operation = [
            operation for operation in plan.operations if operation.name == "set_operator_shell"
        ][0]
        self.assertEqual("home_fallback", plan.profile)
        self.assertIn("create_backup", operation_names)
        self.assertIn("ensure_operator_user", operation_names)
        self.assertIn("set_operator_shell", operation_names)
        self.assertIn("apply_hkcu_operator_policies", operation_names)
        self.assertNotIn("stop_services", operation_names)
        self.assertNotIn("clear_startup", operation_names)
        self.assertEqual(
            r'"C:\Kiosk\RezhimKioska.exe" launch --config "C:\Kiosk\config\kiosk.json"',
            shell_operation.data["shell_command"],
        )

    def test_policy_profiles_file_contains_required_profiles(self):
        profiles = PolicyEngine.load_profiles()

        for profile in [
            "xp_legacy",
            "win7_srp",
            "win10_applocker",
            "win10_shelllauncher",
            "home_fallback",
        ]:
            self.assertIn(profile, profiles)
            self.assertIn("description", profiles[profile])


if __name__ == "__main__":
    unittest.main()
```

## tests\test_policy_plan.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.config import KioskConfig
from python_kiosk.platform_detect import WindowsInfo
from python_kiosk.policy_plan import build_install_plan, build_restore_plan


class PolicyPlanTests(unittest.TestCase):
    def _config(self):
        return KioskConfig(
            app_path=r"C:\Program Files\Vendor\App\app.exe",
            operator_user="Operator",
            admin_password_hash="hash",
            admin_password_salt="salt",
            restart_delay_seconds=2,
        )

    def test_install_plan_is_dry_run_and_mentions_core_restrictions(self):
        info = WindowsInfo(major=10, minor=0, build=19045, edition="Enterprise")

        plan = build_install_plan(self._config(), info)
        text = plan.to_text()

        self.assertTrue(plan.dry_run)
        self.assertIn("Назначить оболочку Operator на KioskLauncher", text)
        self.assertIn("Отключить диспетчер задач", text)
        self.assertIn("Не отключать службы", text)
        self.assertIn("Оставить Win+L доступным", text)
        self.assertIn("Shell Launcher", text)

    def test_restore_plan_returns_shell_without_touching_startup_services(self):
        plan = build_restore_plan(self._config())
        text = plan.to_text()

        self.assertTrue(plan.dry_run)
        self.assertIn("Вернуть оболочку Operator на explorer.exe", text)
        self.assertIn("Не удалять элементы автозагрузки", text)
        self.assertIn("Не останавливать службы", text)


if __name__ == "__main__":
    unittest.main()
```

## tests\test_project_structure.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import os
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ProjectStructureTests(unittest.TestCase):
    def test_required_architecture_directories_exist(self):
        required = [
            "src",
            os.path.join("src", "KioskLauncher"),
            os.path.join("src", "Configurator"),
            os.path.join("src", "PolicyEngine"),
            os.path.join("src", "RestoreTool"),
            os.path.join("src", "Common"),
            os.path.join("src", "Logging"),
            os.path.join("src", "Security"),
            os.path.join("src", "Tests"),
            "config",
            "scripts",
            "docs",
        ]

        missing = [
            path for path in required
            if not os.path.isdir(os.path.join(PROJECT_ROOT, path))
        ]

        self.assertEqual([], missing)

    def test_required_config_scripts_and_docs_exist(self):
        required = [
            os.path.join("config", "kiosk.default.json"),
            os.path.join("config", "policy-profiles.json"),
            os.path.join("scripts", "install.ps1"),
            os.path.join("scripts", "restore.ps1"),
            os.path.join("scripts", "create-operator-user.ps1"),
            os.path.join("scripts", "test-lab-setup.ps1"),
            os.path.join("docs", "INSTALL.md"),
            os.path.join("docs", "RESTORE.md"),
            os.path.join("docs", "TESTING.md"),
            os.path.join("docs", "SECURITY.md"),
            os.path.join("docs", "AUDIT.md"),
        ]

        missing = [
            path for path in required
            if not os.path.isfile(os.path.join(PROJECT_ROOT, path))
        ]

        self.assertEqual([], missing)

    def test_release_script_packages_architecture_directories(self):
        script_path = os.path.join(PROJECT_ROOT, "build_release.ps1")
        with open(script_path, "r", encoding="utf-8") as script_file:
            script = script_file.read()

        for directory in ["python_kiosk", "tests", "docs", "config", "scripts", "src"]:
            self.assertIn('"{0}"'.format(directory), script)


if __name__ == "__main__":
    unittest.main()
```

## tests\test_security.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.security import FailedAttemptLimiter, hash_password, verify_password


class PasswordSecurityTests(unittest.TestCase):
    def test_password_hash_verifies_original_password(self):
        record = hash_password("change-me")

        self.assertTrue(verify_password("change-me", record))

    def test_wrong_password_does_not_verify(self):
        record = hash_password("change-me")

        self.assertFalse(verify_password("wrong-password", record))

    def test_same_password_uses_different_salts(self):
        first = hash_password("change-me")
        second = hash_password("change-me")

        self.assertNotEqual(first["salt"], second["salt"])
        self.assertNotEqual(first["hash"], second["hash"])
        self.assertNotIn("change-me", first["hash"])

    def test_failed_attempt_limiter_adds_delay_after_threshold(self):
        limiter = FailedAttemptLimiter(
            threshold=2,
            base_delay_seconds=3,
            max_delay_seconds=9,
        )

        self.assertEqual(0, limiter.record_failure())
        self.assertEqual(3, limiter.record_failure())
        self.assertEqual(6, limiter.record_failure())
        self.assertEqual(9, limiter.record_failure())

        limiter.record_success()

        self.assertEqual(0, limiter.record_failure())


if __name__ == "__main__":
    unittest.main()
```

## tests\test_session_lockdown.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.session_lockdown import (
    WindowsDesktopBackend,
    WindowsSessionLockdown,
    recover_current_desktop,
)


class FakeDesktopBackend(object):
    def __init__(self):
        self.calls = []

    def lockdown_current_desktop_shell(self):
        self.calls.append("lockdown_current_desktop_shell")
        return {
            "shell_window": 100,
            "hidden_windows": [100, 200],
            "closed_explorer": False,
        }

    def restore_current_desktop_shell(self):
        self.calls.append("restore_current_desktop_shell")
        return {"restored_windows": [100, 200]}


class FakeLogger(object):
    def __init__(self):
        self.events = []

    def info(self, event, **data):
        self.events.append(("info", event, data))

    def warning(self, event, **data):
        self.events.append(("warning", event, data))


class FakeWindowsDesktopBackend(WindowsDesktopBackend):
    def __init__(self):
        super(FakeWindowsDesktopBackend, self).__init__()
        self.show_calls = []
        self.close_calls = []

    def _find_shell_windows(self):
        return [100, 200]

    def _find_window(self, class_name):
        return 100 if class_name == "Shell_TrayWnd" else 0

    def _show_window(self, hwnd, command):
        self.show_calls.append((hwnd, command))
        return True

    def _post_close(self, hwnd):
        self.close_calls.append(hwnd)
        return True

    def _is_window(self, hwnd):
        return True


class SessionLockdownTests(unittest.TestCase):
    def test_operator_mode_locks_only_current_desktop_shell(self):
        backend = FakeDesktopBackend()
        logger = FakeLogger()
        lockdown = WindowsSessionLockdown(backend=backend, logger=logger)

        result = lockdown.activate_operator_mode()

        self.assertEqual(["lockdown_current_desktop_shell"], backend.calls)
        self.assertFalse(result["closed_explorer"])
        self.assertIn(("info", "session.lockdown_enabled"), [(level, event) for level, event, _ in logger.events])
        logged_text = str(logger.events)
        self.assertNotIn("stop_services", logged_text)
        self.assertNotIn("clear_startup", logged_text)
        self.assertNotIn("kill_processes", logged_text)

    def test_desktop_backend_hides_shell_without_posting_wm_close(self):
        backend = FakeWindowsDesktopBackend()

        result = backend.lockdown_current_desktop_shell()

        self.assertEqual(
            [(100, WindowsDesktopBackend.SW_HIDE), (200, WindowsDesktopBackend.SW_HIDE)],
            backend.show_calls,
        )
        self.assertEqual([], backend.close_calls)
        self.assertFalse(result["closed_explorer"])

    def test_release_restores_hidden_current_desktop_windows(self):
        backend = FakeDesktopBackend()
        logger = FakeLogger()
        lockdown = WindowsSessionLockdown(backend=backend, logger=logger)

        lockdown.activate_operator_mode()
        result = lockdown.release_operator_mode()

        self.assertEqual(
            ["lockdown_current_desktop_shell", "restore_current_desktop_shell"],
            backend.calls,
        )
        self.assertEqual([100, 200], result["restored_windows"])
        self.assertIn(("info", "session.lockdown_released"), [(level, event) for level, event, _ in logger.events])

    def test_desktop_backend_restore_finds_shell_windows_when_state_was_lost(self):
        backend = FakeWindowsDesktopBackend()

        result = backend.restore_current_desktop_shell()

        self.assertEqual(
            [(100, WindowsDesktopBackend.SW_SHOW), (200, WindowsDesktopBackend.SW_SHOW)],
            backend.show_calls,
        )
        self.assertEqual([100, 200], result["restored_windows"])

    def test_recover_current_desktop_restores_windows_and_starts_explorer(self):
        backend = FakeWindowsDesktopBackend()
        process_calls = []

        result = recover_current_desktop(
            backend=backend,
            process_factory=lambda command: process_calls.append(command),
        )

        self.assertEqual([["explorer.exe"]], process_calls)
        self.assertTrue(result["started_explorer"])
        self.assertEqual([100, 200], result["restored_windows"])


if __name__ == "__main__":
    unittest.main()
```

## tests\test_shell_ui.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.shell_ui import (
    SHELL_THEME,
    ShellWindow,
    StyledPasswordDialog,
    WindowsKeyFilter,
    build_login_entry_options,
    build_shell_layout,
    build_unlock_dialog_layout,
    combine_windows_account_name,
    scaled_unlock_dialog_geometry,
    run_shell,
    unlock_desktop,
)
from python_kiosk.security import FailedAttemptLimiter


class FakeRoot(object):
    def __init__(self):
        self.attributes_calls = []
        self.protocol_calls = []
        self.bind_calls = []
        self.after_calls = []
        self.config_values = {}
        self.title_value = None
        self.mainloop_called = False
        self.destroy_called = False
        self.screen_width = 1440
        self.screen_height = 900
        self.state_calls = []
        self.deiconify_called = False
        self.lift_called = False
        self.focus_force_called = False
        self.lower_called = False

    def title(self, value):
        self.title_value = value

    def configure(self, **kwargs):
        self.config_values.update(kwargs)

    def attributes(self, name, value):
        self.attributes_calls.append((name, value))

    def protocol(self, name, callback):
        self.protocol_calls.append((name, callback))

    def bind(self, event, callback):
        self.bind_calls.append((event, callback))

    def after(self, delay_ms, callback):
        self.after_calls.append((delay_ms, callback))

    def mainloop(self):
        self.mainloop_called = True

    def destroy(self):
        self.destroy_called = True

    def state(self, value):
        self.state_calls.append(value)

    def deiconify(self):
        self.deiconify_called = True

    def lift(self):
        self.lift_called = True

    def focus_force(self):
        self.focus_force_called = True

    def lower(self):
        self.lower_called = True

    def winfo_screenwidth(self):
        return self.screen_width

    def winfo_screenheight(self):
        return self.screen_height


class FakeTkFactory(object):
    def __init__(self):
        self.root = FakeRoot()

    def Tk(self):
        return self.root


class FakeCanvas(object):
    def __init__(self):
        self.pack_calls = []
        self.configure_calls = []
        self.bind_calls = []
        self.rectangle_calls = []
        self.polygon_calls = []
        self.text_calls = []
        self.tag_bind_calls = []
        self.tag_configs = []

    def pack(self, **kwargs):
        self.pack_calls.append(kwargs)

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)

    def bind(self, event, callback):
        self.bind_calls.append((event, callback))

    def tag_bind(self, tag, event, callback):
        self.tag_bind_calls.append((tag, event, callback))

    def tag_configure(self, tag, **kwargs):
        self.tag_configs.append((tag, kwargs))

    def delete(self, tag):
        pass

    def create_rectangle(self, *args, **kwargs):
        self.rectangle_calls.append((args, kwargs))

    def create_polygon(self, *args, **kwargs):
        self.polygon_calls.append((args, kwargs))

    def create_text(self, *args, **kwargs):
        self.text_calls.append((args, kwargs))


class FakeWatchdog(object):
    def __init__(self, actions):
        self.actions = list(actions)
        self.tick_count = 0
        self.stop_called = False

    def tick(self):
        self.tick_count += 1
        return self.actions.pop(0) if self.actions else "running"

    def stop(self):
        self.stop_called = True


class FakeLauncher(object):
    def __init__(self, watchdog, restore_if_minimized=False):
        self.watchdog = watchdog
        self.unlock_attempts = []
        self.changed_app_paths = []
        self.config = type(
            "Config",
            (),
            {
                "app_path": r"C:\Program Files\Vendor\App\VendorApp.exe",
                "kiosk": {"blockDesktop": True},
                "allowed_application": type(
                    "Allowed",
                    (),
                    {
                        "start_maximized": False,
                        "restore_if_minimized": restore_if_minimized,
                    },
                )(),
            },
        )()
        self.logger = FakeLogger()

    def create_watchdog(self):
        return self.watchdog

    def verify_admin_password(self, password):
        self.unlock_attempts.append(password)
        return password == "admin-pass"

    def verify_admin_credentials(self, username, password):
        self.unlock_attempts.append((username, password))
        return username == "Admin" and password == "secret"

    def set_allowed_application_path(self, app_path):
        self.changed_app_paths.append(app_path)
        self.config.app_path = app_path
        return True


class FakeHotkeyService(object):
    def __init__(self):
        self.started = []
        self.stopped = []

    def start(self, root, callback):
        self.started.append((root, callback))

    def stop(self):
        self.stopped.append("stopped")


class FakeKeyboardFilterService(object):
    def __init__(self):
        self.started = []
        self.stopped = []
        self.reset_calls = []

    def start(self):
        self.started.append("started")

    def stop(self):
        self.stopped.append("stopped")

    def reset_state(self):
        self.reset_calls.append("reset")


class FakeSessionLockdown(object):
    def __init__(self):
        self.activated = []
        self.released = []

    def activate_operator_mode(self):
        self.activated.append("activated")
        return {"closed_explorer": True}

    def release_operator_mode(self):
        self.released.append("released")
        return {"restored_windows": []}


class FakeLogger(object):
    def __init__(self):
        self.events = []

    def info(self, event, **data):
        self.events.append(("info", event, data))

    def warning(self, event, **data):
        self.events.append(("warning", event, data))


class FakeAppWindowController(object):
    def __init__(self, minimized=False):
        self.minimized = minimized
        self.calls = []

    def is_minimized(self, app_path):
        self.calls.append(("is_minimized", app_path))
        return self.minimized

    def bring_to_front(self, app_path):
        self.calls.append(("bring_to_front", app_path))
        return True

    def ensure_foreground(self, app_path, **kwargs):
        self.calls.append(("ensure_foreground", app_path))
        self.calls.append(("ensure_foreground_kwargs", kwargs))
        return True

    def restore(self, app_path):
        self.calls.append(("restore", app_path))
        self.minimized = False
        return True

    def release_topmost(self, app_path):
        self.calls.append(("release_topmost", app_path))
        return True


class ShellWindowTests(unittest.TestCase):
    def test_shell_layout_matches_approved_mockup_structure(self):
        layout = build_shell_layout(r"C:\Program Files\Vendor\App\VendorApp.exe")
        by_name = dict((item["name"], item) for item in layout)

        self.assertEqual("#050505", by_name["background"]["fill"])
        self.assertEqual((50, 150, 820, 560, 14), by_name["left_panel"]["rect"])
        self.assertEqual((920, 150, 470, 560, 14), by_name["right_panel"]["rect"])
        self.assertEqual((50, 760, 1340, 86, 12), by_name["safety_strip"]["rect"])
        self.assertEqual("Режим киоска", by_name["header_title"]["text"])
        self.assertEqual("VendorApp.exe", by_name["app_name"]["text"])
        self.assertEqual("Надзор: включен", by_name["watchdog_status"]["text"])
        self.assertEqual("Разблокировать", by_name["unlock_button_text"]["text"])
        self.assertIn("Win+L остается доступен", by_name["safety_message"]["text"])
        self.assertEqual(
            "разработал: Абдрахманов Амаль Даулетович",
            by_name["developer_credit"]["text"],
        )
        self.assertEqual("#6b7280", by_name["developer_credit"]["fill"])

    def test_unlock_dialog_layout_matches_approved_mockup(self):
        layout = build_unlock_dialog_layout()
        by_name = dict((item["name"], item) for item in layout)

        self.assertEqual((965, 270, 380, 350, 12), by_name["unlock_dialog"]["rect"])
        self.assertEqual("Вход администратора Windows", by_name["unlock_title"]["text"])
        self.assertEqual((1000, 391, 300, 42, 8), by_name["username_input"]["rect"])
        self.assertNotIn("domain_label", by_name)
        self.assertNotIn("domain_input", by_name)
        self.assertEqual((1000, 458, 300, 42, 8), by_name["password_input"]["rect"])
        self.assertEqual("#0ea5e9", by_name["unlock_button"]["fill"])
        self.assertEqual("Отмена", by_name["cancel_button_text"]["text"])
        self.assertEqual("#38bdf8", SHELL_THEME["accent"])

    def test_combine_windows_account_name_uses_domain_field_when_present(self):
        self.assertEqual("Admin", combine_windows_account_name("Admin", ""))
        self.assertEqual(".\\Admin", combine_windows_account_name("Admin", "."))
        self.assertEqual("PC\\Admin", combine_windows_account_name("Admin", "PC"))
        self.assertEqual("PC\\Admin", combine_windows_account_name("PC\\Admin", "OTHER"))

    def test_login_entry_options_make_typed_input_visible_and_mask_password(self):
        username_options = build_login_entry_options(masked=False)
        password_options = build_login_entry_options(masked=True)

        self.assertEqual(SHELL_THEME["text"], username_options["fg"])
        self.assertNotIn("show", username_options)
        self.assertEqual(SHELL_THEME["text"], password_options["fg"])
        self.assertEqual("*", password_options["show"])

    def test_unlock_dialog_geometry_uses_mockup_position(self):
        geometry = scaled_unlock_dialog_geometry(1440, 900)

        self.assertEqual("380x350+965+270", geometry)

    def test_configure_window_renders_design_to_canvas(self):
        root = FakeRoot()
        canvas = FakeCanvas()
        launcher = FakeLauncher(FakeWatchdog(["started"]))

        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            canvas_factory=lambda parent: canvas,
        )
        shell.configure_window()

        rendered_text = [call[1]["text"] for call in canvas.text_calls]
        self.assertEqual([{"fill": "both", "expand": True}], canvas.pack_calls)
        self.assertIn("VendorApp.exe", rendered_text)
        self.assertIn("Режим киоска", rendered_text)
        self.assertIn("разработал: Абдрахманов Амаль Даулетович", rendered_text)
        self.assertNotIn("Пароль администратора", rendered_text)
        self.assertNotIn("Отмена", rendered_text)
        self.assertTrue(canvas.polygon_calls)

    def test_canvas_unlock_button_is_clickable(self):
        root = FakeRoot()
        canvas = FakeCanvas()
        launcher = FakeLauncher(FakeWatchdog(["started"]))
        unlock_calls = []
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
            unlock_action=lambda: unlock_calls.append("unlock"),
            canvas_factory=lambda parent: canvas,
        )

        shell.configure_window()
        unlock_bindings = [
            call for call in canvas.tag_bind_calls if call[0] == "unlock_click" and call[1] in ("<Button-1>", "<ButtonPress-1>")
        ]
        self.assertEqual(1, len(unlock_bindings))
        self.assertEqual("<Button-1>", unlock_bindings[0][1])

        unlock_bindings[0][2](None)

        self.assertEqual([], unlock_calls)
        self.assertTrue(shell.admin_session.is_active())
        self.assertFalse(root.destroy_called)

    def test_default_password_provider_uses_styled_dialog(self):
        root = FakeRoot()
        dialog = type("Dialog", (), {"ask": lambda self: ("Admin", "secret")})()
        launcher = FakeLauncher(FakeWatchdog(["started"]))

        shell = ShellWindow(
            root,
            launcher,
            credential_dialog_factory=lambda parent: dialog,
        )

        self.assertEqual(("Admin", "secret"), shell._default_credential_provider())

    def test_shell_configures_fullscreen_background_and_blocks_close(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["started"]))

        shell = ShellWindow(root, launcher, credential_provider=lambda: ("Operator", "bad"))
        shell.configure_window()

        self.assertIn(("-fullscreen", True), root.attributes_calls)
        self.assertNotIn(("-topmost", True), root.attributes_calls)
        self.assertEqual("Режим киоска", root.title_value)
        self.assertEqual(SHELL_THEME["background"], root.config_values["bg"])
        self.assertEqual("WM_DELETE_WINDOW", root.protocol_calls[0][0])
        self.assertEqual(["<FocusOut>", "<Unmap>"], [call[0] for call in root.bind_calls])

    def test_focus_guard_restores_fullscreen_window(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["started"]))
        shell = ShellWindow(root, launcher, credential_provider=lambda: ("Operator", "bad"))

        shell.enforce_shell_focus()

        self.assertIn("normal", root.state_calls)
        self.assertTrue(root.deiconify_called)
        self.assertFalse(root.lift_called)
        self.assertFalse(root.focus_force_called)
        self.assertIn(("-fullscreen", True), root.attributes_calls)
        self.assertNotIn(("-topmost", True), root.attributes_calls)

    def test_focus_guard_tick_keeps_shell_behind_running_allowed_app(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        app_windows = FakeAppWindowController(minimized=False)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            app_window_controller=app_windows,
        )

        shell._focus_guard_tick()

        self.assertEqual([], root.state_calls)
        self.assertFalse(root.deiconify_called)
        self.assertNotIn(("-fullscreen", True), root.attributes_calls)
        self.assertTrue(root.lower_called)

    def test_focus_guard_tick_does_not_cover_admin_session_windows(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        shell = ShellWindow(root, launcher, credential_provider=lambda: ("Admin", "secret"))
        shell.handle_admin_unlock()

        root.state_calls = []
        root.deiconify_called = False
        root.attributes_calls = []
        root.lower_called = False
        shell._focus_guard_tick()

        self.assertEqual([], root.state_calls)
        self.assertFalse(root.deiconify_called)
        self.assertNotIn(("-fullscreen", True), root.attributes_calls)
        self.assertTrue(root.lower_called)

    def test_admin_unlock_lowers_background_before_modal_dialog(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))

        def credential_provider():
            self.assertTrue(root.lower_called)
            return None

        shell = ShellWindow(
            root,
            launcher,
            credential_provider=credential_provider,
        )

        self.assertFalse(shell.handle_admin_unlock())

    def test_shell_does_not_start_global_hotkey_service(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["started"]))
        hotkey_service = FakeHotkeyService()

        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            hotkey_service=hotkey_service,
        )
        shell.configure_window()

        self.assertEqual([], hotkey_service.started)

    def test_shell_starts_windows_key_filter_when_present(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["started"]))
        keyboard_filter_service = FakeKeyboardFilterService()

        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            keyboard_filter_service=keyboard_filter_service,
        )
        shell.configure_window()

        self.assertEqual(["started"], keyboard_filter_service.started)

    def test_shell_activates_operator_session_lockdown_on_start(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["started"]))
        session_lockdown = FakeSessionLockdown()

        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            session_lockdown=session_lockdown,
        )
        shell.configure_window()

        self.assertEqual(["activated"], session_lockdown.activated)

    def test_start_ticks_watchdog_and_schedules_next_tick(self):
        root = FakeRoot()
        watchdog = FakeWatchdog(["started"])
        launcher = FakeLauncher(watchdog)
        shell = ShellWindow(root, launcher, credential_provider=lambda: ("Operator", "bad"))

        shell.start()

        self.assertEqual(1, watchdog.tick_count)
        self.assertEqual((2000, shell._watchdog_tick), root.after_calls[-1])
        self.assertTrue(root.mainloop_called)

    def test_start_releases_restrictions_when_mainloop_returns(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["started"]))
        keyboard_filter_service = FakeKeyboardFilterService()
        session_lockdown = FakeSessionLockdown()
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            keyboard_filter_service=keyboard_filter_service,
            session_lockdown=session_lockdown,
        )

        shell.start()

        self.assertEqual(["stopped"], keyboard_filter_service.stopped)
        self.assertEqual(["released"], session_lockdown.released)

    def test_admin_button_opens_admin_session_after_windows_admin_password(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        unlock_calls = []
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
            unlock_action=lambda: unlock_calls.append("unlock"),
        )

        shell.handle_admin_unlock()

        self.assertEqual([("Admin", "secret")], launcher.unlock_attempts)
        self.assertEqual([], unlock_calls)
        self.assertTrue(shell.admin_session.is_active())
        self.assertFalse(root.destroy_called)

    def test_admin_unlock_resets_keyboard_filter_before_dialog(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        keyboard_filter_service = FakeKeyboardFilterService()

        def credential_provider():
            self.assertEqual(["reset"], keyboard_filter_service.reset_calls)
            return None

        shell = ShellWindow(
            root,
            launcher,
            credential_provider=credential_provider,
            keyboard_filter_service=keyboard_filter_service,
        )

        self.assertFalse(shell.handle_admin_unlock())

    def test_successful_admin_unlock_temporarily_stops_keyboard_filter(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        keyboard_filter_service = FakeKeyboardFilterService()
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
            keyboard_filter_service=keyboard_filter_service,
        )
        shell.configure_window()

        self.assertEqual(["started"], keyboard_filter_service.started)

        shell.handle_admin_unlock()

        self.assertEqual(["stopped"], keyboard_filter_service.stopped)
        self.assertTrue(shell.admin_session.is_active())

        shell.handle_return_to_kiosk()

        self.assertEqual(["started", "started"], keyboard_filter_service.started)

    def test_failed_admin_unlock_keeps_keyboard_filter_active(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        keyboard_filter_service = FakeKeyboardFilterService()
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            keyboard_filter_service=keyboard_filter_service,
        )
        shell.configure_window()

        shell.handle_admin_unlock()

        self.assertEqual(["started"], keyboard_filter_service.started)
        self.assertEqual([], keyboard_filter_service.stopped)
        self.assertFalse(shell.admin_session.is_active())

    def test_admin_session_unlock_desktop_stops_restrictions_and_launches_explorer(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        hotkey_service = FakeHotkeyService()
        keyboard_filter_service = FakeKeyboardFilterService()
        app_windows = FakeAppWindowController()
        session_lockdown = FakeSessionLockdown()
        unlock_calls = []
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
            unlock_action=lambda: unlock_calls.append("explorer"),
            hotkey_service=hotkey_service,
            keyboard_filter_service=keyboard_filter_service,
            app_window_controller=app_windows,
            session_lockdown=session_lockdown,
        )

        shell.handle_admin_unlock()
        shell.handle_unlock_desktop()

        self.assertEqual(["stopped"], hotkey_service.stopped)
        self.assertEqual(["stopped"], keyboard_filter_service.stopped)
        self.assertEqual(["released"], shell.session_lockdown.released)
        self.assertIn(("release_topmost", launcher.config.app_path), app_windows.calls)
        self.assertEqual(["explorer"], unlock_calls)
        self.assertFalse(root.destroy_called)

    def test_admin_session_can_stop_watchdog(self):
        root = FakeRoot()
        watchdog = FakeWatchdog(["running"])
        launcher = FakeLauncher(watchdog)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
        )
        shell._watchdog_tick()
        shell.handle_admin_unlock()

        shell.handle_stop_watchdog()

        self.assertTrue(watchdog.stop_called)
        self.assertTrue(shell.watchdog_disabled)

    def test_watchdog_tick_does_not_force_allowed_app_above_admin_session(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        app_windows = FakeAppWindowController(minimized=False)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
            app_window_controller=app_windows,
        )
        shell.handle_admin_unlock()

        root.lower_called = False
        shell._watchdog_tick()

        self.assertNotIn(("ensure_foreground", launcher.config.app_path), app_windows.calls)
        self.assertFalse(root.lower_called)

    def test_return_to_kiosk_closes_admin_session(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
        )
        shell.handle_admin_unlock()

        shell.handle_return_to_kiosk()

        self.assertFalse(shell.admin_session.is_active())
        self.assertFalse(root.destroy_called)

    def test_bad_admin_credentials_do_not_unlock(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        unlock_calls = []
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            unlock_action=lambda: unlock_calls.append("unlock"),
        )

        shell.handle_admin_unlock()

        self.assertEqual([("Operator", "bad")], launcher.unlock_attempts)
        self.assertEqual([], unlock_calls)
        self.assertFalse(shell.admin_session.is_active())
        self.assertFalse(root.destroy_called)

    def test_bad_admin_credentials_are_logged_and_delayed(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        logger = FakeLogger()
        sleep_calls = []
        errors = []
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "secret-pass-should-not-log"),
            unlock_action=lambda: None,
            failed_attempt_limiter=FailedAttemptLimiter(
                threshold=1,
                base_delay_seconds=4,
                max_delay_seconds=4,
            ),
            sleep_func=lambda seconds: sleep_calls.append(seconds),
            logger=logger,
            error_reporter=lambda message: errors.append(message),
        )

        shell.handle_admin_unlock()

        self.assertEqual([4], sleep_calls)
        self.assertIn(("warning", "admin.unlock_denied"), [(level, event) for level, event, _ in logger.events])
        logged_text = str(logger.events)
        self.assertIn("bad_credentials", logged_text)
        self.assertNotIn("secret-pass-should-not-log", logged_text)
        self.assertEqual(1, len(errors))
        self.assertIn("Отказано", errors[0])

    def test_admin_session_can_change_allowed_application_path(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Admin", "secret"),
            allowed_app_selector=lambda: r"C:\Windows\System32\notepad.exe",
        )
        shell.handle_admin_unlock()

        self.assertTrue(shell.handle_change_allowed_app())

        self.assertEqual([r"C:\Windows\System32\notepad.exe"], launcher.changed_app_paths)
        self.assertIsNone(shell.watchdog)

    def test_admin_session_layout_has_change_application_button(self):
        layout = build_shell_layout(
            r"C:\Program Files\Vendor\App\VendorApp.exe",
            admin_session_active=True,
        )
        by_name = dict((item["name"], item) for item in layout)

        self.assertIn("change_app_button", by_name)
        self.assertEqual("Изменить приложение", by_name["change_app_button_text"]["text"])

    def test_watchdog_tick_marks_minimized_app_and_renders_restore_button(self):
        root = FakeRoot()
        canvas = FakeCanvas()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        app_windows = FakeAppWindowController(minimized=True)
        logger = FakeLogger()
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            canvas_factory=lambda parent: canvas,
            app_window_controller=app_windows,
            logger=logger,
        )
        shell.configure_window()

        shell._watchdog_tick()

        rendered_text = [call[1]["text"] for call in canvas.text_calls]
        self.assertIn("Свернуто", rendered_text)
        self.assertIn("Развернуть приложение", rendered_text)
        self.assertIn(
            ("info", "shell.app_status_changed"),
            [(level, event) for level, event, _ in logger.events],
        )
        self.assertNotIn(("restore", launcher.config.app_path), app_windows.calls)

    def test_watchdog_tick_restores_minimized_allowed_app_when_configured(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]), restore_if_minimized=True)
        app_windows = FakeAppWindowController(minimized=True)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            app_window_controller=app_windows,
        )

        shell._watchdog_tick()

        self.assertIn(("restore", launcher.config.app_path), app_windows.calls)
        self.assertEqual("running", shell.app_status)
        self.assertTrue(root.lower_called)

    def test_watchdog_tick_does_not_steal_focus_while_admin_dialog_is_open(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        app_windows = FakeAppWindowController(minimized=False)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            app_window_controller=app_windows,
        )
        shell.admin_dialog_open = True

        shell._watchdog_tick()

        self.assertEqual(1, launcher.watchdog.tick_count)
        self.assertNotIn(("ensure_foreground", launcher.config.app_path), app_windows.calls)
        self.assertFalse(root.lower_called)

    def test_minimized_app_stays_minimized_until_restore_button(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        app_windows = FakeAppWindowController(minimized=False)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            app_window_controller=app_windows,
        )
        shell.app_status = "minimized"

        shell._watchdog_tick()

        self.assertEqual("minimized", shell.app_status)
        self.assertNotIn(("ensure_foreground", launcher.config.app_path), app_windows.calls)
        self.assertNotIn(("restore", launcher.config.app_path), app_windows.calls)

    def test_watchdog_restart_resets_minimized_status(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["restarted"]))
        app_windows = FakeAppWindowController(minimized=False)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            app_window_controller=app_windows,
        )
        shell.app_status = "minimized"

        shell._watchdog_tick()

        self.assertEqual("running", shell.app_status)
        self.assertIn(("ensure_foreground", launcher.config.app_path), app_windows.calls)

    def test_minimized_layout_separates_notification_from_restore_button(self):
        layout = build_shell_layout(
            r"C:\Program Files\Vendor\App\VendorApp.exe",
            app_status="minimized",
        )
        by_name = dict((item["name"], item) for item in layout)

        self.assertIn("minimized_alert", by_name)
        self.assertEqual((135, 558, 520, 42, 8), by_name["minimized_alert"]["rect"])
        self.assertEqual((135, 615, 255, 44, 8), by_name["restore_app_button"]["rect"])

    def test_watchdog_tick_keeps_allowed_app_foreground_above_shell(self):
        root = FakeRoot()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        app_windows = FakeAppWindowController(minimized=False)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            app_window_controller=app_windows,
        )

        shell._watchdog_tick()

        self.assertIn(("ensure_foreground", launcher.config.app_path), app_windows.calls)
        self.assertNotIn(("bring_to_front", launcher.config.app_path), app_windows.calls)
        self.assertTrue(root.lower_called)

    def test_restore_button_restores_allowed_application(self):
        root = FakeRoot()
        canvas = FakeCanvas()
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        app_windows = FakeAppWindowController(minimized=True)
        shell = ShellWindow(
            root,
            launcher,
            credential_provider=lambda: ("Operator", "bad"),
            canvas_factory=lambda parent: canvas,
            app_window_controller=app_windows,
        )
        shell.configure_window()
        shell._watchdog_tick()
        restore_bindings = [
            call for call in canvas.tag_bind_calls if call[0] == "restore_app_click" and call[1] == "<Button-1>"
        ]

        self.assertEqual(1, len(restore_bindings))
        restore_bindings[0][2](None)

        self.assertIn(("restore", launcher.config.app_path), app_windows.calls)

    def test_unlock_desktop_launches_explorer(self):
        calls = []

        unlock_desktop(process_factory=lambda command: calls.append(command))

        self.assertEqual([["explorer.exe"]], calls)

    def test_windows_key_filter_blocks_win_key_and_allows_win_l_lock(self):
        lock_calls = []
        key_filter = WindowsKeyFilter(
            lock_workstation=lambda: lock_calls.append("lock"),
            key_state_checker=lambda vk_code: vk_code
            in (WindowsKeyFilter.VK_LWIN, WindowsKeyFilter.VK_RWIN),
        )

        self.assertTrue(
            key_filter.should_block_key(
                WindowsKeyFilter.VK_LWIN,
                WindowsKeyFilter.WM_KEYDOWN,
            )
        )
        self.assertTrue(
            key_filter.should_block_key(
                ord("D"),
                WindowsKeyFilter.WM_KEYDOWN,
            )
        )
        self.assertEqual([], lock_calls)

        self.assertTrue(
            key_filter.should_block_key(
                WindowsKeyFilter.VK_L,
                WindowsKeyFilter.WM_KEYDOWN,
            )
        )
        self.assertEqual(["lock"], lock_calls)

        self.assertFalse(
            key_filter.should_block_key(
                WindowsKeyFilter.VK_LWIN,
                WindowsKeyFilter.WM_KEYUP,
            )
        )
        self.assertFalse(
            key_filter.should_block_key(
                WindowsKeyFilter.VK_L,
                WindowsKeyFilter.WM_KEYDOWN,
            )
        )

    def test_windows_key_filter_blocks_required_win_shortcuts(self):
        for vk_code in [ord("R"), ord("E"), ord("X"), ord("S"), ord("D"), ord("M"), WindowsKeyFilter.VK_TAB]:
            key_filter = WindowsKeyFilter(
                key_state_checker=lambda key: key
                in (WindowsKeyFilter.VK_LWIN, WindowsKeyFilter.VK_RWIN)
            )
            self.assertTrue(
                key_filter.should_block_key(
                    WindowsKeyFilter.VK_LWIN,
                    WindowsKeyFilter.WM_KEYDOWN,
                )
            )
            self.assertTrue(
                key_filter.should_block_key(vk_code, WindowsKeyFilter.WM_KEYDOWN)
            )

    def test_windows_key_filter_blocks_task_switching_shortcuts(self):
        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code
            in (WindowsKeyFilter.VK_MENU, WindowsKeyFilter.VK_LMENU)
        )

        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_MENU, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_TAB, WindowsKeyFilter.WM_KEYDOWN))

        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code
            in (WindowsKeyFilter.VK_MENU, WindowsKeyFilter.VK_LMENU)
        )
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_MENU, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_F4, WindowsKeyFilter.WM_KEYDOWN))

        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code
            in (WindowsKeyFilter.VK_MENU, WindowsKeyFilter.VK_LMENU)
        )
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_MENU, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_ESCAPE, WindowsKeyFilter.WM_KEYDOWN))

        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code
            in (WindowsKeyFilter.VK_CONTROL, WindowsKeyFilter.VK_LCONTROL)
        )
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_CONTROL, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_ESCAPE, WindowsKeyFilter.WM_KEYDOWN))

        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code
            in (
                WindowsKeyFilter.VK_CONTROL,
                WindowsKeyFilter.VK_LCONTROL,
                WindowsKeyFilter.VK_SHIFT,
                WindowsKeyFilter.VK_LSHIFT,
            )
        )
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_CONTROL, WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_SHIFT, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_ESCAPE, WindowsKeyFilter.WM_KEYDOWN))

    def test_windows_key_filter_blocks_ctrl_alt_tab_switcher(self):
        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code
            in (
                WindowsKeyFilter.VK_CONTROL,
                WindowsKeyFilter.VK_LCONTROL,
                WindowsKeyFilter.VK_MENU,
                WindowsKeyFilter.VK_LMENU,
            )
        )

        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_CONTROL, WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_MENU, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_TAB, WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_TAB, WindowsKeyFilter.WM_KEYUP))

    def test_windows_key_filter_never_blocks_keyup_events(self):
        key_filter = WindowsKeyFilter()

        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_LWIN, WindowsKeyFilter.WM_KEYDOWN))

        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_LWIN, WindowsKeyFilter.WM_KEYUP))
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_TAB, WindowsKeyFilter.WM_SYSKEYUP))

    def test_windows_key_filter_fails_open_when_physical_key_state_is_unavailable(self):
        def broken_key_state(_vk_code):
            raise OSError("GetAsyncKeyState failed")

        key_filter = WindowsKeyFilter(key_state_checker=broken_key_state)
        key_filter.win_down = True

        self.assertFalse(key_filter.should_block_key(ord("A"), WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.win_down)

    def test_windows_key_filter_blocks_alt_f4_when_alt_is_physically_down(self):
        key_filter = WindowsKeyFilter(
            key_state_checker=lambda key: key
            in (WindowsKeyFilter.VK_MENU, WindowsKeyFilter.VK_LMENU)
        )

        self.assertTrue(
            key_filter.should_block_key(
                WindowsKeyFilter.VK_F4,
                WindowsKeyFilter.WM_SYSKEYDOWN,
            )
        )

    def test_windows_key_filter_passes_normal_text_and_dialog_input_keys(self):
        for vk_code in [
            ord("A"),
            ord("Z"),
            ord("0"),
            WindowsKeyFilter.VK_SPACE,
            WindowsKeyFilter.VK_BACK,
            WindowsKeyFilter.VK_DELETE,
            WindowsKeyFilter.VK_RETURN,
            WindowsKeyFilter.VK_TAB,
        ]:
            key_filter = WindowsKeyFilter()
            self.assertFalse(
                key_filter.should_block_key(vk_code, WindowsKeyFilter.WM_KEYDOWN),
                "vk {0} must pass through".format(vk_code),
            )

    def test_windows_key_filter_recovers_from_stale_win_modifier_state(self):
        key_filter = WindowsKeyFilter(key_state_checker=lambda vk_code: False)
        key_filter.win_down = True

        self.assertFalse(key_filter.should_block_key(ord("A"), WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.win_down)

    def test_windows_key_filter_recovers_from_stale_alt_modifier_state(self):
        key_filter = WindowsKeyFilter(key_state_checker=lambda vk_code: False)
        key_filter.alt_down = True

        self.assertFalse(
            key_filter.should_block_key(WindowsKeyFilter.VK_F4, WindowsKeyFilter.WM_SYSKEYDOWN)
        )
        self.assertFalse(key_filter.alt_down)

    def test_windows_key_filter_recovers_from_stale_ctrl_modifier_state(self):
        key_filter = WindowsKeyFilter(key_state_checker=lambda vk_code: False)
        key_filter.ctrl_down = True

        self.assertFalse(
            key_filter.should_block_key(WindowsKeyFilter.VK_ESCAPE, WindowsKeyFilter.WM_KEYDOWN)
        )
        self.assertFalse(key_filter.ctrl_down)

    def test_windows_key_filter_allows_regular_ctrl_alt_shift_k_input(self):
        key_filter = WindowsKeyFilter()

        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_CONTROL, WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_MENU, WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_SHIFT, WindowsKeyFilter.WM_KEYDOWN))
        self.assertFalse(key_filter.should_block_key(ord("K"), WindowsKeyFilter.WM_KEYDOWN))

    def test_windows_key_filter_tracks_left_and_right_modifier_keys(self):
        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code == WindowsKeyFilter.VK_LMENU
        )

        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_LMENU, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_TAB, WindowsKeyFilter.WM_KEYDOWN))

        key_filter = WindowsKeyFilter(
            key_state_checker=lambda vk_code: vk_code == WindowsKeyFilter.VK_RCONTROL
        )
        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_RCONTROL, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_ESCAPE, WindowsKeyFilter.WM_KEYDOWN))

    def test_windows_key_filter_logs_only_blocked_shortcuts_not_text_input(self):
        logger = FakeLogger()
        key_filter = WindowsKeyFilter(
            logger=logger,
            key_state_checker=lambda vk_code: vk_code
            in (WindowsKeyFilter.VK_MENU, WindowsKeyFilter.VK_LMENU),
        )

        self.assertFalse(key_filter.should_block_key(ord("A"), WindowsKeyFilter.WM_KEYDOWN))
        self.assertEqual([], logger.events)

        self.assertFalse(key_filter.should_block_key(WindowsKeyFilter.VK_MENU, WindowsKeyFilter.WM_KEYDOWN))
        self.assertTrue(key_filter.should_block_key(WindowsKeyFilter.VK_TAB, WindowsKeyFilter.WM_KEYDOWN))

        self.assertIn(
            ("warning", "keyboard_filter.blocked_shortcut"),
            [(level, event) for level, event, _ in logger.events],
        )
        logged_text = str(logger.events)
        self.assertIn("Alt+Tab", logged_text)
        self.assertNotIn("'A'", logged_text)

    def test_run_shell_passes_launcher_logger_to_shell_and_keyboard_filter(self):
        launcher = FakeLauncher(FakeWatchdog(["running"]))
        created = {}

        class FakeFilter(object):
            def __init__(self, logger=None, **kwargs):
                created["filter_logger"] = logger

            def start(self):
                pass

            def stop(self):
                pass

        class FakeShell(object):
            def __init__(self, root, shell_launcher, **kwargs):
                created["shell_logger"] = kwargs.get("logger")
                created["keyboard_filter"] = kwargs.get("keyboard_filter_service")

            def start(self):
                created["started"] = True

        run_shell(
            launcher,
            tkinter_module=FakeTkFactory(),
            shell_window_class=FakeShell,
            keyboard_filter_class=FakeFilter,
        )

        self.assertIs(launcher.logger, created["filter_logger"])
        self.assertIs(launcher.logger, created["shell_logger"])
        self.assertTrue(created["started"])


if __name__ == "__main__":
    unittest.main()
```

## tests\test_system_backend.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.policy_engine import PolicyOperation
from python_kiosk.system_backend import WindowsSystemBackend


class FakeCompleted(object):
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


class FakeRunner(object):
    def __init__(self):
        self.commands = []

    def __call__(self, command, **kwargs):
        self.commands.append(list(command))
        text = " ".join(command).lower()
        if command[:2] == ["wmic", "useraccount"]:
            return FakeCompleted("SID=S-1-5-21-100-200-300-1007\r\n")
        if command[:2] == ["reg", "query"]:
            return FakeCompleted("", 0)
        if command[:2] == ["net", "user"]:
            return FakeCompleted("User name                    test\r\n", 0)
        if command[:2] == ["net", "localgroup"]:
            return FakeCompleted("Users\r\n", 0)
        if "profileimagepath" in text:
            return FakeCompleted("ProfileImagePath    REG_EXPAND_SZ    C:\\Users\\test\r\n", 0)
        return FakeCompleted("", 0)


class MissingUserRunner(FakeRunner):
    def __call__(self, command, **kwargs):
        self.commands.append(list(command))
        if command[:2] == ["net", "user"]:
            return FakeCompleted("The user name could not be found.", 2)
        return FakeCompleted("", 0)


class AdminOperatorRunner(FakeRunner):
    def __call__(self, command, **kwargs):
        self.commands.append(list(command))
        if command[:2] == ["net", "user"]:
            return FakeCompleted("User name                    test\r\n", 0)
        if command[:4] == ["wmic", "group", "where", "sid='S-1-5-32-544'"]:
            return FakeCompleted("Name=Administrators\r\n", 0)
        if command[:3] == ["net", "localgroup", "Administrators"]:
            return FakeCompleted("Alias name     Administrators\r\n-------------------------------------------------------------------------------\r\ntest\r\n", 0)
        return FakeCompleted("", 0)


class WindowsSystemBackendTests(unittest.TestCase):
    def test_set_operator_shell_writes_shell_under_operator_hku(self):
        runner = FakeRunner()
        backend = WindowsSystemBackend(command_runner=runner)

        backend.apply_operation(
            PolicyOperation(
                "set_operator_shell",
                "set shell",
                data={
                    "operator_user": "test",
                    "shell_command": '"C:\\Kiosk\\RezhimKioska.exe" launch --config "C:\\Kiosk\\config\\kiosk.json"',
                },
            )
        )

        commands = [" ".join(command) for command in runner.commands]
        self.assertTrue(any("Winlogon" in command and "Shell" in command for command in commands))
        self.assertTrue(any("RezhimKioska.exe" in command for command in commands))
        self.assertFalse(any("stop" in command.lower() for command in commands))

    def test_restore_operator_shell_sets_explorer_and_removes_known_policies(self):
        runner = FakeRunner()
        backend = WindowsSystemBackend(command_runner=runner)

        backend.apply_operation(
            PolicyOperation(
                "restore_operator_shell",
                "restore shell",
                data={"operator_user": "test", "shell": "explorer.exe"},
            )
        )
        backend.apply_operation(
            PolicyOperation(
                "restore_operator_policies",
                "restore policies",
                data={"operator_user": "test"},
            )
        )

        commands = [" ".join(command) for command in runner.commands]
        self.assertTrue(any("explorer.exe" in command for command in commands))
        self.assertTrue(any("reg delete" in command and "DisableTaskMgr" in command for command in commands))
        self.assertFalse(any("taskkill" in command.lower() for command in commands))

    def test_apply_operator_policies_uses_only_registry_values(self):
        runner = FakeRunner()
        backend = WindowsSystemBackend(command_runner=runner)

        backend.apply_operation(
            PolicyOperation(
                "apply_hkcu_operator_policies",
                "apply policies",
                data={"operator_user": "test"},
            )
        )

        commands = [" ".join(command) for command in runner.commands]
        self.assertTrue(any("DisableTaskMgr" in command for command in commands))
        self.assertTrue(any("NoRun" in command for command in commands))
        self.assertFalse(any("net stop" in command.lower() for command in commands))
        self.assertFalse(any("sc.exe" in command.lower() for command in commands))

    def test_ensure_operator_user_rejects_missing_account(self):
        backend = WindowsSystemBackend(command_runner=MissingUserRunner())

        with self.assertRaises(RuntimeError):
            backend.apply_operation(
                PolicyOperation(
                    "ensure_operator_user",
                    "ensure user",
                    data={"operator_user": "test"},
                )
            )

    def test_ensure_operator_user_rejects_local_admin_operator(self):
        backend = WindowsSystemBackend(command_runner=AdminOperatorRunner())

        with self.assertRaises(RuntimeError):
            backend.apply_operation(
                PolicyOperation(
                    "ensure_operator_user",
                    "ensure user",
                    data={"operator_user": "test"},
                )
            )


if __name__ == "__main__":
    unittest.main()
```

## tests\test_watchdog.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.process_watchdog import (
    ProcessWatchdog,
    windows_allowed_process_running,
    windows_process_ids_for_name,
    windows_process_name_running,
)
from python_kiosk.process_watchdog import windows_process_path_running


class FakeProcess(object):
    def __init__(self, return_code=None):
        self.return_code = return_code

    def poll(self):
        return self.return_code


class FakeFactory(object):
    def __init__(self, processes):
        self.processes = list(processes)
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        return self.processes.pop(0)


class FakeLogger(object):
    def __init__(self):
        self.events = []

    def info(self, event, **data):
        self.events.append(("info", event, data))

    def warning(self, event, **data):
        self.events.append(("warning", event, data))


class ProcessWatchdogTests(unittest.TestCase):
    def test_tick_starts_process_when_none_is_running(self):
        factory = FakeFactory([FakeProcess(return_code=None)])
        watchdog = ProcessWatchdog([r"C:\App\app.exe"], process_factory=factory)

        action = watchdog.tick()

        self.assertEqual("started", action)
        self.assertEqual([([r"C:\App\app.exe"], {})], factory.calls)

    def test_tick_keeps_running_process(self):
        factory = FakeFactory([FakeProcess(return_code=None)])
        watchdog = ProcessWatchdog([r"C:\App\app.exe"], process_factory=factory)
        watchdog.tick()

        action = watchdog.tick()

        self.assertEqual("running", action)
        self.assertEqual(1, len(factory.calls))

    def test_tick_restarts_finished_process(self):
        first = FakeProcess(return_code=0)
        second = FakeProcess(return_code=None)
        factory = FakeFactory([first, second])
        watchdog = ProcessWatchdog([r"C:\App\app.exe"], process_factory=factory)
        watchdog.process = first

        action = watchdog.tick()

        self.assertEqual("restarted", action)
        self.assertEqual(1, len(factory.calls))

    def test_watchdog_logs_start_and_restart(self):
        first = FakeProcess(return_code=0)
        second = FakeProcess(return_code=None)
        factory = FakeFactory([first, second])
        logger = FakeLogger()
        watchdog = ProcessWatchdog(
            [r"C:\App\app.exe"],
            process_factory=factory,
            logger=logger,
        )

        self.assertEqual("started", watchdog.tick())
        watchdog.process = first
        self.assertEqual("restarted", watchdog.tick())

        events = [(level, event) for level, event, _ in logger.events]
        self.assertIn(("info", "watchdog.started"), events)
        self.assertIn(("warning", "watchdog.restarted"), events)

    def test_watchdog_logs_do_not_store_full_command_arguments(self):
        factory = FakeFactory([FakeProcess(return_code=None)])
        logger = FakeLogger()
        watchdog = ProcessWatchdog(
            [r"C:\App\app.exe", "--password", "secret-pass"],
            process_factory=factory,
            logger=logger,
        )

        watchdog.tick()

        self.assertEqual(r"C:\App\app.exe", logger.events[0][2]["executable"])
        self.assertEqual(2, logger.events[0][2]["argument_count"])
        logged_text = str(logger.events)
        self.assertIn("argument_count", logged_text)
        self.assertNotIn("secret-pass", logged_text)
        self.assertNotIn("--password", logged_text)

    def test_tick_does_not_start_duplicate_when_same_app_is_already_running(self):
        first = FakeProcess(return_code=0)
        factory = FakeFactory([FakeProcess(return_code=None)])
        bring_calls = []
        watchdog = ProcessWatchdog(
            [r"C:\Windows\System32\notepad.exe"],
            process_factory=factory,
            process_running=lambda: True,
            bring_existing_to_front=lambda: bring_calls.append("front"),
        )
        watchdog.process = first

        action = watchdog.tick()

        self.assertEqual("running", action)
        self.assertEqual([], factory.calls)
        self.assertEqual(["front"], bring_calls)

    def test_tick_starts_second_instance_only_when_single_instance_disabled(self):
        factory = FakeFactory([FakeProcess(return_code=None)])
        watchdog = ProcessWatchdog(
            [r"C:\Windows\System32\notepad.exe"],
            process_factory=factory,
            process_running=lambda: True,
            single_instance=False,
        )

        action = watchdog.tick()

        self.assertEqual("started", action)
        self.assertEqual(1, len(factory.calls))

    def test_start_passes_working_directory_and_waits_for_input_idle(self):
        factory = FakeFactory([FakeProcess(return_code=None)])
        wait_calls = []
        watchdog = ProcessWatchdog(
            [r"C:\App\app.exe"],
            process_factory=factory,
            working_directory=r"C:\App",
            input_idle_waiter=lambda process, timeout: wait_calls.append((process, timeout)),
        )

        action = watchdog.tick()

        self.assertEqual("started", action)
        self.assertEqual(r"C:\App", factory.calls[0][1]["cwd"])
        self.assertEqual([(watchdog.process, 5)], wait_calls)

    def test_tick_does_not_restart_when_restart_on_exit_is_disabled(self):
        first = FakeProcess(return_code=0)
        factory = FakeFactory([FakeProcess(return_code=None)])
        watchdog = ProcessWatchdog(
            [r"C:\App\app.exe"],
            process_factory=factory,
            restart_on_exit=False,
        )
        watchdog.process = first

        action = watchdog.tick()

        self.assertEqual("exited", action)
        self.assertEqual([], factory.calls)

    def test_windows_process_name_running_detects_image_name_from_tasklist(self):
        calls = []

        def fake_runner(command, **kwargs):
            calls.append(command)
            return b"notepad.exe                  1234 Console"

        running = windows_process_name_running(
            r"C:\Windows\System32\notepad.exe",
            command_runner=fake_runner,
        )

        self.assertTrue(running)
        self.assertEqual("tasklist", calls[0][0])

    def test_windows_process_path_running_matches_exact_executable_path(self):
        calls = []

        def fake_runner(command, **kwargs):
            calls.append(command)
            return (
                "Node,ExecutablePath,ProcessId\r\n"
                "PC,C:\\Windows\\System32\\notepad.exe,100\r\n"
                "PC,C:\\Temp\\notepad.exe,101\r\n"
            ).encode("utf-8")

        running = windows_process_path_running(
            r"C:\Windows\System32\notepad.exe",
            command_runner=fake_runner,
        )

        self.assertTrue(running)
        self.assertEqual("wmic", calls[0][0])

    def test_windows_process_path_running_rejects_same_name_different_path(self):
        def fake_runner(command, **kwargs):
            return (
                "Node,ExecutablePath,ProcessId\r\n"
                "PC,C:\\Temp\\notepad.exe,101\r\n"
            ).encode("utf-8")

        running = windows_process_path_running(
            r"C:\Windows\System32\notepad.exe",
            command_runner=fake_runner,
        )

        self.assertFalse(running)

    def test_allowed_process_running_falls_back_to_image_name_for_delegating_exe(self):
        calls = []

        def fake_path_runner(command, **kwargs):
            calls.append(("path", command[0]))
            return (
                "Node,ExecutablePath,ProcessId\r\n"
                "PC,C:\\Program Files\\WindowsApps\\Microsoft.WindowsNotepad\\Notepad.exe,101\r\n"
            ).encode("utf-8")

        def fake_name_runner(command, **kwargs):
            calls.append(("name", command[0]))
            return b"notepad.exe                  101 Console"

        running = windows_allowed_process_running(
            r"C:\Windows\System32\notepad.exe",
            path_command_runner=fake_path_runner,
            name_command_runner=fake_name_runner,
        )

        self.assertTrue(running)
        self.assertEqual([("path", "wmic"), ("name", "tasklist")], calls)

    def test_windows_process_ids_for_name_reads_wmic_process_ids(self):
        def fake_runner(command, **kwargs):
            return (
                "Node,ProcessId\r\n"
                "PC,101\r\n"
                "PC,102\r\n"
            ).encode("utf-8")

        pids = windows_process_ids_for_name(
            r"C:\Windows\System32\notepad.exe",
            command_runner=fake_runner,
        )

        self.assertEqual(set([101, 102]), pids)

    def test_windows_process_path_running_accepts_bom_and_blank_wmic_lines(self):
        def fake_runner(command, **kwargs):
            return (
                "\r\n"
                "\ufeffNode,ExecutablePath,ProcessId\r\n"
                "PC,C:\\Windows\\System32\\notepad.exe,100\r\n"
            ).encode("utf-8")

        running = windows_process_path_running(
            r"C:\Windows\System32\notepad.exe",
            command_runner=fake_runner,
        )

        self.assertTrue(running)


if __name__ == "__main__":
    unittest.main()
```

## tests\test_window_control.py

```python
try:
    import _test_environment  # noqa: F401
except ImportError:
    from tests import _test_environment  # noqa: F401

import unittest

from python_kiosk.window_control import AppWindowController


class FakeWindowBackend(object):
    def __init__(self, windows=None):
        self.minimized = False
        self.calls = []
        self.windows = windows or [100]
        self.minimized_by_hwnd = {}

    def find_windows_for_executable(self, executable_path):
        self.calls.append(("find", executable_path))
        return list(self.windows)

    def is_minimized(self, hwnd):
        self.calls.append(("is_minimized", hwnd))
        if hwnd in self.minimized_by_hwnd:
            return self.minimized_by_hwnd[hwnd]
        return self.minimized

    def bring_to_front(self, hwnd):
        self.calls.append(("bring_to_front", hwnd))

    def restore(self, hwnd):
        self.calls.append(("restore", hwnd))
        self.minimized = False

    def maximize(self, hwnd):
        self.calls.append(("maximize", hwnd))

    def wait_for_window(self, executable_path, timeout_seconds=5):
        self.calls.append(("wait_for_window", executable_path, timeout_seconds))
        return 100

    def clear_topmost(self, hwnd):
        self.calls.append(("clear_topmost", hwnd))


class AppWindowControllerTests(unittest.TestCase):
    def test_reports_minimized_when_allowed_app_window_is_iconic(self):
        backend = FakeWindowBackend()
        backend.minimized = True
        controller = AppWindowController(backend=backend)

        self.assertTrue(controller.is_minimized(r"C:\App\app.exe"))

    def test_reports_minimized_when_any_allowed_app_window_is_iconic(self):
        backend = FakeWindowBackend(windows=[100, 200])
        backend.minimized_by_hwnd = {100: False, 200: True}
        controller = AppWindowController(backend=backend)

        self.assertTrue(controller.is_minimized(r"C:\App\app.exe"))
        self.assertIn(("is_minimized", 100), backend.calls)
        self.assertIn(("is_minimized", 200), backend.calls)

    def test_bring_to_front_marks_allowed_window_topmost(self):
        backend = FakeWindowBackend()
        controller = AppWindowController(backend=backend)

        self.assertTrue(controller.bring_to_front(r"C:\App\app.exe"))
        self.assertIn(("bring_to_front", 100), backend.calls)

    def test_restore_unminimizes_allowed_window(self):
        backend = FakeWindowBackend()
        backend.minimized = True
        controller = AppWindowController(backend=backend)

        self.assertTrue(controller.restore(r"C:\App\app.exe"))
        self.assertFalse(backend.minimized)
        self.assertIn(("restore", 100), backend.calls)

    def test_ensure_foreground_restores_and_places_allowed_app_topmost(self):
        backend = FakeWindowBackend()
        backend.minimized = True
        controller = AppWindowController(backend=backend)

        self.assertTrue(controller.ensure_foreground(r"C:\App\app.exe"))

        self.assertFalse(backend.minimized)
        self.assertIn(("restore", 100), backend.calls)
        self.assertIn(("bring_to_front", 100), backend.calls)

    def test_ensure_foreground_can_wait_for_window_and_maximize(self):
        backend = FakeWindowBackend()
        controller = AppWindowController(backend=backend)

        self.assertTrue(
            controller.ensure_foreground(
                r"C:\App\app.exe",
                wait=True,
                timeout_seconds=7,
                start_maximized=True,
            )
        )

        self.assertIn(("wait_for_window", r"C:\App\app.exe", 7), backend.calls)
        self.assertIn(("maximize", 100), backend.calls)
        self.assertIn(("bring_to_front", 100), backend.calls)

    def test_release_topmost_clears_allowed_window_topmost_state(self):
        backend = FakeWindowBackend()
        controller = AppWindowController(backend=backend)

        self.assertTrue(controller.release_topmost(r"C:\App\app.exe"))
        self.assertIn(("clear_topmost", 100), backend.calls)

    def test_window_backend_falls_back_to_image_name_when_exact_path_has_no_pids(self):
        from python_kiosk.window_control import WindowsWindowBackend

        class Backend(WindowsWindowBackend):
            def __init__(self):
                pass

            def _process_ids_for_exact_path(self, executable_path):
                return set()

            def _process_ids_for_image_name(self, executable_path):
                return set([101])

        backend = Backend()

        self.assertEqual(set([101]), backend._process_ids_for_executable(r"C:\Windows\System32\notepad.exe"))


if __name__ == "__main__":
    unittest.main()
```


# Аудит проекта

## Состояние dual-release на 2026-06-18

- Modern и Legacy имеют независимые entry point, зависимости, spec и build-скрипты.
- Общие контракты находятся в `contracts/`; оба тестовых набора проверяют JSON и русские UI-метки.
- `build_release.ps1` только пакует два заранее собранных EXE, не вызывает PyInstaller и не подменяет их старым `dist\RezhimKioska.exe`.
- Legacy frozen-файл собран как PE32 x86. На Windows 11 проверен безопасный отказ с кодом `3`: HKCU/HKLM shell не менялись, процесс и hook не оставались.
- XP SP1/SP3 и Server 2003 x86 пока не проверены на snapshot-VM, поэтому Legacy остаётся `Targeted, не проверено на VM`.
- Во время текущего этапа live-киоск не применялся; рабочий стол основной УЗ не изменялся.

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

## Исправления foreground, keyboard hook и аргументов 2026-06-17

Найдено:

- `SetForegroundWindow()` без attach/fallback не всегда переводил разрешенное приложение в настоящий foreground на Windows 11.
- После исправления foreground выяснилось, что реальный low-level keyboard hook мог мешать обычному вводу из-за неявных 32-bit `ctypes`-сигнатур WinAPI.
- `allowedApplication.arguments` разбирался через `shlex.split(..., posix=False)`, поэтому кавычки оставались внутри аргументов и ломали запуск любого ПО с путями/аргументами в кавычках.
- `scripts\apply-test-kiosk.ps1` был привязан к устаревшему имени `release\RezhimKioska-inputfix.exe`, которого больше нет после штатной сборки.

Исправлено:

- `WindowsWindowBackend.bring_to_front()` теперь использует `AttachThreadInput`, `BringWindowToTop`, `SetActiveWindow`, `SetFocus`, `SetForegroundWindow`, `AllowSetForegroundWindow` и безопасный Alt-fallback. Логика работает по найденному HWND и не привязана к Notepad.
- `WindowsKeyFilter` настраивает 64-bit safe `restype/argtypes` для `SetWindowsHookExW`, `CallNextHookEx`, `UnhookWindowsHookEx`, `GetMessageW`, `PostThreadMessageW`, `GetCurrentThreadId`, `GetLastError`.
- Callback keyboard hook работает fail-open при исключениях: сбрасывает внутренние модификаторы, пишет только техническое событие ошибки и пропускает ввод через hook-цепочку; текст ввода не логируется.
- `_split_windows_arguments()` на Windows использует `CommandLineToArgvW`, поэтому кавычки группируют аргументы, но не попадают в `subprocess.Popen(list)`.
- `scripts\apply-test-kiosk.ps1` теперь использует актуальный `release\RezhimKioska.exe`.

Проверено:

- `.\.venv\Scripts\python.exe -m unittest discover tests` — 164 теста, OK.
- `python -m PyInstaller --noconfirm --clean RezhimKioska.spec` — сборка OK.
- `powershell -ExecutionPolicy Bypass -File .\build_release.ps1` — обновлены `release\RezhimKioska.exe` и `release\PythonKiosk-GitHub.zip`.
- Live-проверка исходников с включенным keyboard hook и произвольным разрешенным приложением `pythonw.exe live-test\keyboard_probe.py`: foreground перешел к разрешенному приложению, ввод `1234567890` записан в capture, после сворачивания окно осталось свернутым до ручного восстановления.
- Live-проверка собранного `release\RezhimKioska.exe`: foreground перешел к разрешенному приложению, ввод `2468135790` записан в capture, после сворачивания окно осталось свернутым до ручного восстановления.
- После каждого live-прогона выполнен `python main.py recover-desktop`; новых процессов `RezhimKioska`, `pythonw`, `notepad` не осталось.

Ограничение текущего прогона:

- Реальное применение shell replacement к операторской УЗ `test` не выполнялось из текущего неповышенного токена. Для этого по-прежнему нужен PowerShell от имени администратора Windows и запуск `scripts\apply-test-kiosk.ps1`.

## Исправление Windows/API 1309 при админ-разблокировке 2026-06-17

Найдено:

- При корректном логине и пароле администратора Windows `LogonUserW` возвращал primary token, а проверка `CheckTokenMembership` могла завершаться ошибкой 1309 (`ERROR_NO_IMPERSONATION_TOKEN`).
- Из-за этого пользователь видел сообщение `Отказано в доступе. ошибка Windows/API: код 1309`, хотя пароль был правильный.

Исправлено:

- Добавлена обработка `ERROR_NO_IMPERSONATION_TOKEN`.
- Если `CheckTokenMembership` получает 1309, `WindowsAuthBackend` дублирует primary token через `DuplicateToken` в impersonation token, повторяет проверку членства в локальной группе Administrators и закрывает временный token handle.
- Пароль Windows по-прежнему не сохраняется, не логируется и не кэшируется.

Проверено:

- `.\.venv\Scripts\python.exe -m unittest tests.test_local_admin_auth` — 9 тестов, OK.
- `.\.venv\Scripts\python.exe -m unittest discover tests` — 165 тестов, OK.
- `powershell -ExecutionPolicy Bypass -File .\build_release.ps1` — обновлены `release\RezhimKioska.exe` и `release\PythonKiosk-GitHub.zip`.

## Исправление отказа для UAC-администратора 2026-06-17

Найдено:

- После устранения ошибки 1309 корректный пользователь `impal` с правильным паролем мог получать отказ `учетная запись не является администратором Windows`.
- Причина: у неповышенного UAC-администратора SID группы `Administrators` может присутствовать в токене как deny-only/filtered group. `CheckTokenMembership` возвращает `False`, хотя учетная запись реально состоит в локальной группе Administrators.

Исправлено:

- Если активная проверка `CheckTokenMembership` возвращает `False`, `WindowsAuthBackend` дополнительно читает группы токена через `GetTokenInformation(TokenGroups)` и сравнивает SID группы Administrators через `EqualSid`.
- Это разрешает разблокировку для локального администратора с UAC filtered token, но не разрешает обычного пользователя без SID Administrators.
- Пароль Windows по-прежнему не сохраняется, не логируется и не кэшируется.

Проверено:

- `.\.venv\Scripts\python.exe -m unittest tests.test_local_admin_auth` — 10 тестов, OK.
- `.\.venv\Scripts\python.exe -m unittest discover tests` — 166 тестов, OK.
- `powershell -ExecutionPolicy Bypass -File .\build_release.ps1` — обновлены `release\RezhimKioska.exe` и `release\PythonKiosk-GitHub.zip`.

## Исправление OverflowError при проверке SID Administrators 2026-06-17

Найдено:

- После добавления fallback-проверки групп токена Windows мог показать `argument 1: OverflowError: int too long to convert`.
- Причина: `EqualSid` и `GetTokenInformation` вызывались без явных `ctypes` `restype/argtypes`. На Windows x64 SID pointer мог неявно трактоваться как 32-bit integer.

Исправлено:

- Добавлена настройка 64-bit safe WinAPI-сигнатур для `GetTokenInformation` и `EqualSid`.
- Проверка текущего токена `impal` без ввода пароля показала `contains_admin_sid=True` без `OverflowError`.

Проверено:

- `.\.venv\Scripts\python.exe -m unittest tests.test_local_admin_auth.LocalAdminAuthTests.test_windows_backend_configures_64bit_safe_token_api_signatures` — OK.
- `.\.venv\Scripts\python.exe -m unittest discover tests` — 167 тестов, OK.
- `powershell -ExecutionPolicy Bypass -File .\build_release.ps1` — обновлены `release\RezhimKioska.exe` и `release\PythonKiosk-GitHub.zip`.

## Исправление смены приложения после остановки надзора 2026-06-17

Найдено:

- После нажатия `Остановить надзор` флаг `watchdog_disabled` оставался активным.
- При последующей смене разрешенного приложения создавался новый watchdog, но
  он не выполнял стартовый тик, поэтому выбранный `.exe` не запускался.
- Экран киоска продолжал показывать `Надзор: включен`, поэтому кнопка
  выглядела нерабочей.
- При возврате в киоск после остановки мог использоваться старый остановленный
  объект watchdog.

Исправлено:

- Экран киоска отдельно показывает `Надзор: включен` и `Надзор: остановлен`.
- Кнопка надзора перерисовывает состояние сразу после нажатия.
- Повторное нажатие кнопки в админ-сессии запускает надзор обратно.
- При смене разрешенного приложения старый watchdog останавливается, создается
  свежий watchdog и выполняется один стартовый тик нового приложения.
- При возврате в киоск после остановки используется свежий watchdog.
- `_watchdog_tick` не создает новый watchdog, пока надзор явно остановлен
  администратором.

Проверено:

- `.\.venv\Scripts\python.exe -m unittest tests.test_shell_ui` — 60 тестов, OK.
- `.\.venv\Scripts\python.exe -m unittest discover tests` — 171 тест, OK.

## Исправление постоянного пути конфигурации в one-file exe 2026-06-17

Найдено:

- В собранном PyInstaller one-file exe дефолтный `DEFAULT_CONFIG_PATH` мог быть
  абсолютным путем внутри временной папки `_MEI...`.
- Из-за этого при запуске без явного `--config` выбор нового разрешенного ПО мог
  сохраняться во временный `config/kiosk.json`, который исчезает после выхода из
  приложения.

Исправлено:

- В frozen-режиме `resolve_default_config_path()` теперь всегда выбирает
  постоянный путь рядом с `RezhimKioska.exe`.
- Если PyInstaller дал путь `_MEI...\config\kiosk.json`, приложение использует
  `папка_exe\config\kiosk.json`.
- Это совпадает со структурой релиза, где `build_release.ps1` кладет
  `release\config\kiosk.json` рядом с `release\RezhimKioska.exe`.

Проверено:

- `.\.venv\Scripts\python.exe -m unittest tests.test_cli` — 16 тестов, OK.
- `.\.venv\Scripts\python.exe -m unittest discover tests` — 172 теста, OK.

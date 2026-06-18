# Режим киоска

## Выбор загрузчика

Выберите файл вручную по версии Windows: автоматического селектора и третьего загрузчика нет.

```text
XP SP1-SP3 / Server 2003 x86 -> release\legacy\RezhimKioska-Legacy.exe
Windows 7 SP1-11             -> release\modern\RezhimKioska-Modern.exe
```

Оба файла используют внешний `config\kiosk.json` рядом с EXE и запускают только указанный там обычный Win32 `.exe`. Modern и Legacy собраны независимо: Legacy-код не импортирует Modern-код, поэтому поддержка старых Windows не изменяет работающую Modern-оболочку.

Текущий статус платформ приведён в [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md). XP/Server 2003 пока являются целевыми, но не подтверждёнными на snapshot-VM платформами; универсальная готовность до такой проверки не заявляется.

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

Архитектура содержит профили `xp_legacy`, `win7_srp`, `win10_applocker`, `win10_shelllauncher`, `home_fallback`. Home-редакции используют fallback с пониженной гарантией. Для XP/Server 2003 используется отдельный Legacy EXE на Python 2.7 x86; Modern EXE на старых системах не запускается.

## Сборка

Сначала отдельно соберите и проверьте Modern и Legacy, затем запустите упаковщик:

```powershell
.\build_modern.ps1
cmd /c build_legacy.cmd
.\build_release.ps1
```

Результаты:

- `release\modern\RezhimKioska-Modern.exe`;
- `release\legacy\RezhimKioska-Legacy.exe`;
- `release\package\PythonKiosk-GitHub.zip`;
- `release\package\SHA256SUMS.txt`;
- `release\package\build-manifest.json`.

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

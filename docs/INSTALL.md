# Установка

## Два независимых EXE

```text
XP SP1-SP3 / Server 2003 x86 -> release\legacy\RezhimKioska-Legacy.exe
Windows 7 SP1-11             -> release\modern\RezhimKioska-Modern.exe
```

Установка выполняется из обычной административной УЗ Windows. Оператор должен быть отдельным локальным пользователем без членства в `Administrators`; основную УЗ не указывайте. На XP/Server 2003 создайте оператора штатными средствами Windows, войдите в него один раз для создания `NTUSER.DAT`, затем вернитесь в административную УЗ.

Сначала измените `config\kiosk.json`: `operatorUser`, путь `allowedApplication.path` и `workingDirectory`. Можно выбрать любой существующий обычный `.exe`; UWP/Store не поддерживается.

Modern, dry-run и применение:

```powershell
.\RezhimKioska-Modern.exe install --config .\config\kiosk.json
.\RezhimKioska-Modern.exe install --config .\config\kiosk.json --apply
```

Legacy, dry-run и применение:

```cmd
RezhimKioska-Legacy.exe --config .\config\kiosk.json install
RezhimKioska-Legacy.exe --config .\config\kiosk.json install --apply
```

Для смены разрешённого приложения без ручного редактирования:

```powershell
.\RezhimKioska-Modern.exe set-app --config .\config\kiosk.json --app-path "C:\Path\App.exe"
```

```cmd
RezhimKioska-Legacy.exe --config .\config\kiosk.json set-app "C:\Path\App.exe"
```

`--apply` требует повышенных прав. До записи shell выполняются проверка платформы, оператора, пути EXE и backup. Shell оператора записывается последним; при ошибке уже выполненные операции откатываются.

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
# Kiosk V2: transactional installation

V2 has two independent build families: Modern for Windows 7-11 and Legacy for
Windows XP SP1/Server 2003. Always run `dry-run` first from an elevated local
administrator account. The named operator must already exist, have a profile with
`NTUSER.DAT`, and must not belong directly or indirectly to local Administrators.

Installation captures the operator shell, allowlisted policy values, file DACLs,
and previous installed files before the first write. Files and DACLs are applied
first, operator policies second, and the per-user shell last. An error rolls applied
operations back in reverse order and preserves the integrity-checked backup.

PowerShell wrappers under `v2/scripts` never apply automatically. Pass `-Apply`
explicitly only after reviewing dry-run output and verifying the backup location.

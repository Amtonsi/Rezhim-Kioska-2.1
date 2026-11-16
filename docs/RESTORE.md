# Восстановление

> Этот документ относится к предыдущим выпускам. Для версии 2.1 используем [инструкцию по установке и откату](../README.md) и [протокол испытаний в VMware](VMWARE-2.1.md).

## Штатный Restore/Undo

Восстановление запускается из административной УЗ, не из оператора. Сначала выполните dry-run, затем `--apply`.

Modern:

```powershell
.\RezhimKioska-Modern.exe restore --config .\config\kiosk.json
.\RezhimKioska-Modern.exe restore --config .\config\kiosk.json --apply
.\RezhimKioska-Modern.exe recover-desktop
```

Legacy:

```cmd
RezhimKioska-Legacy.exe --config .\config\kiosk.json restore
RezhimKioska-Legacy.exe --config .\config\kiosk.json restore --apply
RezhimKioska-Legacy.exe --config .\config\kiosk.json recover-desktop
```

Legacy Restore/Undo читает `backup\legacy-backup.json`, проверяет семейство сборки и SID оператора, точно возвращает записанные значения реестра и DACL. Он не зависит от запущенной оболочки. После восстановления выполните выход из операторской УЗ и новый вход: должен стартовать `explorer.exe`, а Пуск и панель задач должны работать обычно.

Если штатный EXE недоступен, войдите в другую административную УЗ и вручную верните для SID оператора значение `HKU\<SID>\Software\Microsoft\Windows NT\CurrentVersion\Winlogon\Shell` в `explorer.exe`, затем удалите только политики, перечисленные в backup. Не меняйте HKCU основной УЗ и не удаляйте чужие значения политик.

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
# Kiosk V2: Restore/Undo

Run the Restore executable from a separate elevated local administrator session.
Restore validates the backup SHA-256, build family, operator name/SID, and every
allowlisted target before writing. It restores previous file bytes, then exact
DACLs, then exact operator registry values including the previous shell. Values
that were absent before installation are deleted rather than replaced with guessed
defaults.

`recover-desktop` is an emergency current-session action. It shows only shell
surfaces in that session and starts `explorer.exe` only when no exact current-session
Explorer is running. It does not replace full Restore.

Never delete the backup after an incomplete Restore. The result lists every item
that could not be recovered without including exception text, passwords, or typed
input.

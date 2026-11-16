# Совместимость

> Этот документ относится к предыдущим выпускам. Для версии 2.1 используем [инструкцию по установке и откату](../README.md) и [протокол испытаний в VMware](VMWARE-2.1.md).

Статусы означают:

- `Verified` — frozen EXE прошёл полный сценарий install/operator/admin/restore на указанной ОС;
- `Targeted, не проверено на VM` — код, API и сборка рассчитаны на ОС, но полный сценарий на snapshot-VM ещё не выполнен;
- `Rejected safely` — неподходящий загрузчик показал сообщение и завершился до изменений.

| ОС | Архитектура | Загрузчик | Статус |
|---|---:|---|---|
| Windows XP SP1 x86 | x86 | Legacy | Targeted, не проверено на VM |
| Windows XP SP2 x86 | x86 | Legacy | Targeted, не проверено на VM |
| Windows XP SP3 x86 | x86 | Legacy | Targeted, не проверено на VM |
| Windows Server 2003 x86 | x86 | Legacy | Targeted, не проверено на VM |
| Windows 7 SP1 | x86/x64 | Modern | Targeted, не проверено на VM |
| Windows 8/8.1 | x86/x64 | Modern | Targeted, не проверено на VM |
| Windows 10 | x86/x64 | Modern | Targeted, не проверено на VM |
| Windows 11 | x64 | Modern | Ранее проверено на доступном ноутбуке; текущие regression-тесты пройдены |
| Windows 11 | x64 | Legacy | Rejected safely, код 3, shell без изменений |

Windows XP без SP и Windows 2000 не поддерживаются. Legacy поддерживает только 32-битную NT 5.x. Modern не поддерживает XP/Server и ARM64.

Home-редакции используют `home_fallback`: shell replacement и пользовательские registry policies не дают гарантий уровня Enterprise. Профили AppLocker/Shell Launcher применимы только там, где функция реально доступна редакции Windows.

На текущем доступном Windows 11 пройдены 196 Modern unit/regression-тестов и 84 Legacy-теста. Оба EXE проверены как PE32/x86; Legacy дополнительно прошел безопасный wrong-platform smoke с кодом выхода 3 и без изменения shell.
# Kiosk V2 compatibility status

- Modern source baseline: Python 3.8 x86, Windows 7 through Windows 11.
- Legacy source baseline: Python 2.7 x86 and XP-compatible Win32/NetAPI functions,
  intended for Windows XP SP1 and Windows Server 2003.
- Home editions use shell replacement, per-user registry policy, desktop isolation,
  and keyboard filtering; they do not provide Enterprise-equivalent AppLocker or
  Shell Launcher guarantees.
- XP and Server 2003 are end-of-life. Source compatibility is tested, but a frozen
  Legacy executable is not supported evidence until it passes the required VM run.

# Совместимость

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

На текущем доступном Windows 11 пройдены 195 Modern unit/regression-тестов и 84 Legacy-теста. Оба EXE проверены как PE32/x86; Legacy дополнительно прошел безопасный wrong-platform smoke с кодом выхода 3 и без изменения shell.

# Сборка версии 2.1.0

Все команды запускаем из корня репозитория на Windows. Для работы программы на терминале достаточно готового комплекта. Python и PyInstaller требуются машине сборки.

| Комплект | Интерпретатор сборки | Упаковщик | Каталог |
|---|---|---|---|
| Modern для Windows 10/11 x64 | CPython 3.14.10 x64 | PyInstaller 6.22.3 | `v2\dist\modern-x64` |
| Compat для Windows 7 SP1 | CPython 3.8.10 x86 | PyInstaller 6.22.3 | `v2\dist\modern` |
| Legacy для Windows XP x86 | CPython 2.7.18 x86 | PyInstaller 3.2.1 | `v2\dist\legacy` |

## Modern и Compat

Устанавливаем Python соответствующей разрядности с Tcl/Tk. Создаём отдельные виртуальные окружения. Подставляем пути к своим интерпретаторам.

```powershell
& 'C:\BuildTools\Python314-x64\python.exe' -m venv .venv\modern
& 'C:\BuildTools\Python38-x86\python.exe' -m venv .venv\compat

& .\.venv\modern\Scripts\python.exe -m pip install -r v2/requirements-modern.txt
& .\.venv\compat\Scripts\python.exe -m pip install -r v2/requirements-modern.txt

& .\.venv\modern\Scripts\python.exe -m unittest discover -s v2\tests -p 'test_*.py'
& .\.venv\compat\Scripts\python.exe -m unittest discover -s v2\tests -p 'test_*.py'

.\v2\scripts\build-modern.ps1 -Python (Resolve-Path .\.venv\modern\Scripts\python.exe) -Target current-x64
.\v2\scripts\build-modern.ps1 -Python (Resolve-Path .\.venv\compat\Scripts\python.exe) -Target compat-x86
```

В обоих каталогах появляются Launcher, Restore и Configurator. У помощников есть короткие имена `Restore.exe` и `Configurator.exe`, которые использует интерфейс. Вложенный `config\kiosk.v2.json` копируется из релизного шаблона. В GitHub Actions выполняем тесты V2 и сборку для каждой архитектуры.

## Legacy

Устанавливаем 32-битный CPython 2.7.18 с Tcl/Tk и pip. Зависимости скачиваем современным Python по HTTPS. Скрипт сверяет SHA-256 каждого пакета, затем вызывает старый pip в автономном режиме и помещает результат в отдельный каталог проекта.

```powershell
$legacy = 'C:\BuildTools\Python27-x86\python.exe'
& .\.venv\modern\Scripts\python.exe .\v2\scripts\prepare-legacy-toolchain.py --python27 $legacy
& $legacy -m unittest discover -s v2\tests\legacy -p 'test_*.py'
.\v2\scripts\build-legacy.ps1 -Python $legacy
```

Файлы в `v2\dist\legacy` образуют единый комплект. Вместе с EXE оставляем DLL среды выполнения, контракты, Tcl/Tk и конфигурацию.

## Архивы и самораспаковывающиеся EXE

Устанавливаем 32-битный 7-Zip с файлами `7z.exe`, `7z.sfx` и `License.txt` в одной папке. Для опубликованных файлов использован 7-Zip 26.06 x86. Указываем путь к своему экземпляру. Сборку каждого семейства завершаем до упаковки.

```powershell
$zip = 'C:\Program Files (x86)\7-Zip\7z.exe'
foreach ($target in 'current-x64','compat-x86','legacy-x86') {
    & .\.venv\modern\Scripts\python.exe .\v2\scripts\package-release.py --target $target --sevenzip $zip --out release
    if ($LASTEXITCODE) { throw "Packaging failed for $target" }
}
$lines = Get-ChildItem release -File | Where-Object Extension -in '.zip','.exe' |
    Sort-Object Name | ForEach-Object { (Get-FileHash $_.FullName).Hash.ToLowerInvariant() + '  ' + $_.Name }
[IO.File]::WriteAllLines((Join-Path (Resolve-Path release) 'SHA256SUMS.txt'), [string[]]$lines, [Text.Encoding]::ASCII)
```

Упаковщик проверяет архитектуру исполняемых файлов и идентичность коротких имён помощников. Конфигурация должна совпадать с `config\kiosk.v2.default.json` вплоть до байта, а `configured` должен быть равен `false`. Затем распаковываем каждый созданный контейнер и сверяем полный список путей и SHA-256 с подготовленным содержимым. Внутри есть `FILES-SHA256.txt`, лицензии и краткая инструкция. Внешний `SHA256SUMS.txt` относится к файлам, загружаемым из Releases. Хеши нового локального билда могут отличаться от опубликованных.

## Приёмка

Перед эксплуатацией проверяем собранный комплект на целевой версии Windows с отдельным стандартным оператором. Проходим первый запуск, перезапуск разрешённого EXE, сворачивание, разблокировку, вход с установленной оболочкой и восстановление после нового входа. Фактические результаты выпуска приведены в [протоколе VMware](VMWARE-2.1.md).

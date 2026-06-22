# Публикация проекта «Режим Киоска» Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Опубликовать последнюю проверенную рабочую версию «Режим Киоска» с полным исходным кодом, русской инструкцией, MIT-лицензией и готовыми Modern/Legacy-сборками.

**Architecture:** Исходный код и документация хранятся в публичном Git-репозитории `Rezhim-Kioska`; воспроизводимые бинарные архивы публикуются вложениями GitHub Release `v2.0.0`. Корневая README служит одновременно описанием проекта и пользовательской инструкцией, а изображения лежат в `docs/images/`.

**Tech Stack:** Git, GitHub, GitHub Releases, Markdown, PowerShell, Python 2.7 x86 для Legacy, современный Python/PyInstaller для Modern.

---

### Task 1: Зафиксировать безопасный состав публикации

**Files:**
- Modify: `.gitignore`
- Inspect: `v2/toolchain/`
- Inspect: `v2/dist/`
- Inspect: `config/`

- [ ] **Step 1: Получить полный список изменённых и неотслеживаемых файлов**

Run: `git status --short && git diff --stat && git diff --cached --stat`

Expected: список содержит только код, тесты, конфигурационные шаблоны, скрипты и документацию проекта.

- [ ] **Step 2: Проверить историю и рабочее дерево на секреты**

Run: `rg -n -i "password\s*[:=]|пароль\s*[:=]|token\s*[:=]|secret\s*[:=]|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|ghp_|github_pat_" --glob '!v2/toolchain/**' --glob '!*.pyc' .`

Expected: нет реальных паролей, токенов и приватных ключей; допускаются только имена полей, проверки и документированные запреты хранения пароля.

- [ ] **Step 3: Уточнить исключения Git**

В `.gitignore` оставить исключёнными сборочные каталоги, журналы, виртуальные окружения, кэш, IDE-файлы и локальные рабочие деревья. Не исключать исходники, тесты, схемы, документацию и необходимые скрипты сборки.

- [ ] **Step 4: Проверить результат**

Run: `git check-ignore -v v2/dist/RezhimKioska-V2-Legacy-XP-x86.zip; git check-ignore -v v2/modern/kiosk_v2_modern/launcher.py`

Expected: ZIP исключён, исходный файл Modern не исключён.

### Task 2: Добавить лицензию и русскую страницу проекта

**Files:**
- Create: `LICENSE`
- Rewrite: `README.md`
- Create: `docs/images/README.md`

- [ ] **Step 1: Добавить лицензию MIT**

Создать `LICENSE` с полным стандартным текстом MIT и строкой copyright:

```text
Copyright (c) 2026 Абдрахманов Амаль Даулетович
```

- [ ] **Step 2: Переписать корневую README в UTF-8**

README должна содержать заголовок «Режим Киоска», краткое назначение, предупреждение о тестировании только под отдельной операторской УЗ, таблицу совместимости, ссылки на Modern/Legacy, инструкции первого запуска, разблокировки, смены приложения, Restore/Undo, сборки из исходников, раздел безопасности, ограничения старых/Home-редакций, автора и MIT.

- [ ] **Step 3: Добавить схему работы**

Использовать Mermaid-схему с потоком:

```text
Администратор -> Configurator -> операторская УЗ -> KioskLauncher -> разрешённое приложение
KioskLauncher -> авторизация администратора -> временная админ-сессия -> Restore/возврат в киоск
```

- [ ] **Step 4: Добавить описание изображений**

В `docs/images/README.md` перечислить происхождение каждого изображения и подтвердить отсутствие паролей и персональных данных.

- [ ] **Step 5: Проверить кодировку и ссылки**

Run: `python -c "from pathlib import Path; Path('README.md').read_text(encoding='utf-8'); Path('LICENSE').read_text(encoding='utf-8'); print('UTF-8 OK')"`

Expected: `UTF-8 OK`.

### Task 3: Подготовить чистые иллюстрации

**Files:**
- Create: `docs/images/01-main-screen.png`
- Create: `docs/images/02-admin-login.png`
- Create: `docs/images/03-admin-session.png`
- Create: `docs/images/04-select-application.png`

- [ ] **Step 1: Подготовить безопасную конфигурацию для снимков**

Использовать временную копию `config/kiosk.v2.default.json`, не менять установленную конфигурацию и не назначать shell основной учётной записи.

- [ ] **Step 2: Получить снимки фактического интерфейса**

Снять четыре состояния последней рабочей Modern-версии: основной экран, локальная авторизация администратора, активная админ-сессия и выбор разрешённого EXE. На снимках не должно быть реальных паролей, персонального рабочего стола или сообщений старых ошибок.

- [ ] **Step 3: Проверить изображения**

Run: `Get-ChildItem docs/images/*.png | Select-Object Name,Length`

Expected: четыре непустых PNG-файла с согласованными именами.

- [ ] **Step 4: Вставить изображения в README**

Использовать относительные Markdown-ссылки вида:

```markdown
![Главный экран режима киоска](docs/images/01-main-screen.png)
```

### Task 4: Проверить рабочую версию и собрать релизные архивы

**Files:**
- Use: `v2/scripts/build-modern.ps1`
- Use: `v2/scripts/build-legacy.ps1`
- Use: `v2/scripts/write-sha256.ps1`
- Create ignored artifact: `v2/dist/RezhimKioska-V2-Modern-Windows7-11.zip`
- Preserve ignored artifact: `v2/dist/RezhimKioska-V2-Legacy-XP-x86.zip`
- Update ignored artifact: `v2/dist/SHA256SUMS.txt`

- [ ] **Step 1: Выполнить Modern-тесты**

Run: `python -m unittest discover -s v2/tests/modern -p 'test_*.py'`

Expected: все тесты завершаются со статусом `OK`.

- [ ] **Step 2: Выполнить Legacy-тесты**

Run: `& "$env:LOCALAPPDATA\Python27-x86-portable\python.exe" -m unittest discover -s v2/tests/legacy -p 'test_*.py'`

Expected: все тесты завершаются со статусом `OK`.

- [ ] **Step 3: Проверить общие контрактные тесты**

Run: `python -m unittest discover -s v2/tests -p 'test_*.py'`

Expected: все применимые тесты завершаются успешно; несовместимые Legacy-модули запускаются отдельной командой Python 2.7.

- [ ] **Step 4: Собрать только при необходимости**

Если исходники новее текущих EXE или контрольные суммы не совпадают, выполнить:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\v2\scripts\build-modern.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\v2\scripts\build-legacy.ps1
```

Expected: каталоги `v2/dist/modern` и `v2/dist/legacy` содержат Launcher, Configurator, Restore и обязательные ресурсы.

- [ ] **Step 5: Создать Modern ZIP и контрольные суммы**

Сжать полное содержимое `v2/dist/modern` в `v2/dist/RezhimKioska-V2-Modern-Windows7-11.zip`, затем записать SHA-256 обоих архивов в `v2/dist/SHA256SUMS.txt` через `v2/scripts/write-sha256.ps1`.

- [ ] **Step 6: Проверить архивы распаковкой**

Распаковать оба ZIP во временные каталоги с кириллицей и проверить наличие Launcher, Configurator, Restore, конфигурации, схемы и требуемых библиотек. Для Legacy выполнить `RezhimKioska-V2-Legacy.exe --platform-check`; на Windows 11 ожидается код несовместимой платформы без Fatal Error.

### Task 5: Сформировать один проверенный коммит исходного кода

**Files:**
- Stage: все согласованные исходники, тесты, скрипты, конфигурационные шаблоны, `LICENSE`, `README.md`, `docs/`
- Exclude: `v2/dist/`, логи, кэш, локальные секреты и временные файлы

- [ ] **Step 1: Просмотреть итоговый diff**

Run: `git status --short; git diff --check; git diff --stat`

Expected: нет ошибок пробелов; изменения соответствуют последней рабочей версии и публикационной документации.

- [ ] **Step 2: Явно проиндексировать согласованные файлы**

Использовать `git add` с явными путями или подтверждённым полным набором, не добавлять игнорируемые релизные ZIP.

- [ ] **Step 3: Проверить staged diff**

Run: `git diff --cached --check; git diff --cached --stat; git status --short`

Expected: в индексе нет бинарных релизных архивов, журналов или секретов.

- [ ] **Step 4: Создать коммит**

Run: `git commit -m "release: опубликовать рабочую версию Режим Киоска 2.0.0"`

Expected: коммит содержит последний рабочий исходный код и русскую документацию.

### Task 6: Создать публичный GitHub-репозиторий и релиз

**Files:**
- Upload: `v2/dist/RezhimKioska-V2-Modern-Windows7-11.zip`
- Upload: `v2/dist/RezhimKioska-V2-Legacy-XP-x86.zip`
- Upload: `v2/dist/SHA256SUMS.txt`

- [ ] **Step 1: Установить и проверить GitHub CLI**

Run: `winget install --id GitHub.cli --exact --accept-source-agreements --accept-package-agreements`

Expected: `gh --version` показывает установленную версию.

- [ ] **Step 2: Авторизовать GitHub CLI**

Run: `gh auth status`

Если авторизации нет, выполнить `gh auth login --web` и завершить подтверждение в браузере без передачи токена в чат или файлы проекта.

- [ ] **Step 3: Создать публичный репозиторий**

Run: `gh repo create Rezhim-Kioska --public --source . --remote origin --description "Режим киоска для запуска одного разрешённого приложения в отдельной операторской учётной записи Windows"`

Expected: добавлен remote `origin`, репозиторий публичный.

- [ ] **Step 4: Отправить последнюю рабочую ветку**

Переименовать основную публикуемую ветку в `main`, если это не нарушает существующую структуру, и выполнить `git push -u origin main`.

- [ ] **Step 5: Настроить страницу проекта**

Run: `gh repo edit --enable-issues --description "Режим киоска для запуска одного разрешённого приложения в отдельной операторской учётной записи Windows" --add-topic windows --add-topic kiosk --add-topic python --add-topic windows-7 --add-topic windows-xp`

Expected: русское описание и темы отображаются на странице репозитория.

- [ ] **Step 6: Создать релиз `v2.0.0`**

Создать русское описание релиза с матрицей Modern/Legacy, предупреждением о backup/Restore и контрольными суммами, затем выполнить `gh release create v2.0.0 ...` с тремя вложениями.

- [ ] **Step 7: Проверить публикацию**

Run: `gh repo view --web` и `gh release view v2.0.0 --json url,assets,name,tagName`

Expected: README и изображения отображаются, исходный код доступен, релиз содержит оба ZIP и `SHA256SUMS.txt`.

### Task 7: Финальная локальная проверка

**Files:**
- Inspect: Windows session and registry only

- [ ] **Step 1: Проверить состояние Git**

Run: `git status -sb`

Expected: нет незакоммиченных файлов публикации; игнорируемые локальные сборки не отображаются.

- [ ] **Step 2: Проверить основной рабочий стол**

Проверить, что для текущей УЗ shell не переопределён, `explorer.exe` работает, kiosk-процессы не запущены, keyboard hook отсутствует.

- [ ] **Step 3: Сформировать итоговый отчёт**

Указать URL репозитория, URL релиза, коммит, результаты тестов, SHA-256 архивов, список опубликованных материалов и подтверждение нормального состояния рабочего стола.

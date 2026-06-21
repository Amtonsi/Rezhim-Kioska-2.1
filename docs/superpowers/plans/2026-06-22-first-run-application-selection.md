# First-Run Application Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Запускать защищенную оболочку при невыбранном или отсутствующем разрешенном EXE и позволять сохранить приложение только после авторизации администратора.

**Architecture:** Конфигурация получает обратимо совместимый признак `allowedApplication.configured`. Bootstrap загружает структурно корректный JSON без требования наличия EXE, а чистая функция выбора создает либо существующий `ObservedApplication`, либо безопасный `UnconfiguredApplication`. Configurator остается отдельным повышенным процессом, атомарно сохраняет выбор, после чего текущая сессия заменяет адаптер без перезапуска киоска.

**Tech Stack:** Python 3.8 Modern, Python 2.7 Legacy, Tk file dialog, JSON Schema, `unittest`, PyInstaller, PowerShell.

---

### Task 1: Контракт конфигурации и сохранение первоначального выбора

**Files:**
- Modify: `v2/contracts/kiosk-config-v2.schema.json`
- Modify: `config/kiosk.v2.default.json`
- Modify: `v2/modern/kiosk_v2_modern/app/runtime_settings.py`
- Modify: `v2/legacy/kiosk_v2_legacy/app/runtime_settings.py`
- Modify: `v2/modern/kiosk_v2_modern/configurator.py`
- Modify: `v2/legacy/kiosk_v2_legacy/configurator.py`
- Test: `v2/tests/contracts/test_contract_documents.py`
- Test: `v2/tests/modern/test_runtime_settings.py`
- Test: `v2/tests/legacy/test_legacy_composition_adapters.py`
- Test: `v2/tests/modern/test_configurator.py`
- Test: `v2/tests/legacy/test_configurator.py`

- [ ] **Step 1: Написать падающие тесты контракта и runtime settings**

В `test_v2_default_matches_every_required_contract_field` заменить равенство ключей секции проверкой обязательного подмножества и отсутствия неизвестных полей:

```python
required = set(section_schema["required"])
properties = set(section_schema["properties"])
actual = set(default[section])
self.assertTrue(required.issubset(actual))
self.assertTrue(actual.issubset(properties))
```

В этот же тест добавить:

```python
self.assertFalse(default["allowedApplication"]["configured"])
self.assertEqual(
    "boolean",
    schema["properties"]["allowedApplication"]["properties"]["configured"]["type"],
)
```

Поле не добавляется в `required`, чтобы старые JSON оставались валидными:

```python
self.assertNotIn(
    "configured",
    schema["properties"]["allowedApplication"]["required"],
)
```

В Modern и Legacy runtime-тестах проверить новый параметр и совместимость:

```python
runtime = RuntimeSettingsFactory(FakeArgumentParser()).build(default_config())
self.assertFalse(runtime.application_configured)

legacy_config = default_config()
del legacy_config["allowedApplication"]["configured"]
runtime = RuntimeSettingsFactory(FakeArgumentParser()).build(legacy_config)
self.assertTrue(runtime.application_configured)
```

Проверку верхнего уровня `self.assertEqual(set(schema["required"]), set(default))` оставить без изменений. Запрет неизвестных ключей сохраняется: новый ключ явно описан в `properties`, но намеренно отсутствует в `required`.

- [ ] **Step 2: Написать падающие тесты Configurator**

Расширить `FakeRepository` журналом загрузок и проверить, что старый отсутствующий путь не блокирует выбор:

```python
def test_missing_previous_application_can_be_replaced(self):
    repository = FakeRepository(config())
    service = ApplicationConfigurator(
        repository,
        FakePicker(r"C:\Program Files\Vendor\New.exe"),
        file_exists=lambda path: path.endswith("New.exe"),
        is_elevated=lambda: True,
    )

    self.assertTrue(service.run())
    self.assertEqual([False], repository.load_requirements)
    saved, require_existing = repository.saved[0]
    self.assertTrue(require_existing)
    self.assertTrue(saved["allowedApplication"]["configured"])
```

- [ ] **Step 3: Запустить тесты и подтвердить RED**

```powershell
& 'C:\Users\impal\AppData\Local\Python38-32\python.exe' -m unittest `
  v2.tests.contracts.test_contract_documents `
  v2.tests.modern.test_runtime_settings `
  v2.tests.modern.test_configurator -v
& 'C:\Users\impal\AppData\Local\Python27-x86-portable\python.exe' -m unittest discover -s v2/tests/legacy -p 'test_*.py' -v
```

Expected: отсутствует поле `configured`, runtime не имеет `application_configured`, Configurator не записывает признак и требует существование старого EXE.

- [ ] **Step 4: Реализовать минимальный контракт**

Добавить в schema необязательное свойство:

```json
"configured": {"type": "boolean"}
```

Добавить в свежую конфигурацию:

```json
"configured": false
```

Добавить `application_configured` в `RuntimeSettings.__slots__`, конструктор и factory:

```python
application_configured = bool(application_data.get("configured", True))
```

В обоих Configurator заменить загрузку:

```python
config = self.repository.load(require_existing_app=False)
```

Перед сохранением добавить:

```python
config["allowedApplication"]["configured"] = True
```

- [ ] **Step 5: Запустить тесты Task 1 и подтвердить GREEN**

Повторить команды Step 3. Expected: все выбранные тесты `OK`.

### Task 2: Безопасный runtime без разрешенного приложения

**Files:**
- Modify: `v2/modern/kiosk_v2_modern/app/bootstrap.py`
- Modify: `v2/legacy/kiosk_v2_legacy/app/bootstrap.py`
- Modify: `v2/modern/kiosk_v2_modern/app/session.py`
- Modify: `v2/legacy/kiosk_v2_legacy/app/session.py`
- Modify: `v2/modern/kiosk_v2_modern/launcher.py`
- Modify: `v2/legacy/kiosk_v2_legacy/launcher.py`
- Test: `v2/tests/test_launcher_composition.py`

- [ ] **Step 1: Написать падающие parity-тесты bootstrap**

Изменить ожидаемую загрузку на безопасную структурную проверку:

```python
self.assertEqual(("config", False), calls[0])
```

Добавить тест адаптера для обеих реализаций:

```python
from kiosk_v2_modern.app.session import (
    UnconfiguredApplication as ModernUnconfiguredApplication,
    select_application as modern_select_application,
)
from kiosk_v2_legacy.app.session import (
    UnconfiguredApplication as LegacyUnconfiguredApplication,
    select_application as legacy_select_application,
)


def test_unconfigured_application_never_starts_or_controls_processes(self):
    for application_class in (ModernUnconfiguredApplication, LegacyUnconfiguredApplication):
        application = application_class(r"F:\Missing\Telegram.exe")
        self.assertFalse(application.configured)
        self.assertFalse(application.enabled)
        self.assertIsNone(application.start())
        self.assertIsNone(application.tick())
        self.assertIsNone(application.restore_application())
        self.assertIsNone(application.bring_to_front())
        self.assertIsNone(application.resume_supervision())
```

Добавить тест чистого выбора:

```python
class SelectionSettings(object):
    def __init__(self, configured):
        self.application_configured = configured
        self.application = type("Application", (), {"path": r"F:\Missing\Telegram.exe"})()


for select in (modern_select_application, legacy_select_application):
    selected = select(
        SelectionSettings(True),
        file_exists=lambda _path: False,
        configured_factory=lambda _settings: self.fail("must not build supervisor"),
    )
    self.assertFalse(selected.configured)
```

И симметричный тест существующего настроенного EXE:

```python
for select in (modern_select_application, legacy_select_application):
    sentinel = object()
    selected = select(
        SelectionSettings(True),
        file_exists=lambda _path: True,
        configured_factory=lambda _settings: sentinel,
    )
    self.assertIs(sentinel, selected)
```

- [ ] **Step 2: Запустить parity-тест и подтвердить RED**

```powershell
& 'C:\Users\impal\AppData\Local\Python38-32\python.exe' -m unittest v2.tests.test_launcher_composition -v
```

Expected: bootstrap еще требует `True`, классы и функция выбора отсутствуют.

- [ ] **Step 3: Реализовать `UnconfiguredApplication` и `select_application`**

В Modern и Legacy `app/session.py` добавить:

```python
class UnconfiguredApplication(object):
    configured = False

    def __init__(self, application_path):
        self.application_path = application_path
        self.latest_result = None

    @property
    def enabled(self):
        return False

    def start(self): return None
    def tick(self, **_context): return None
    def restore_application(self, **_context): return None
    def bring_to_front(self, **_context): return None
    def stop_supervision(self): return None
    def resume_supervision(self): return None


def select_application(runtime_settings, file_exists, configured_factory):
    path = runtime_settings.application.path
    if not runtime_settings.application_configured or not file_exists(path):
        return UnconfiguredApplication(path)
    return configured_factory(runtime_settings)
```

В `ObservedApplication` добавить `configured = True`.

- [ ] **Step 4: Разрешить bootstrap создавать оболочку без существующего EXE**

В обоих `app/bootstrap.py` использовать:

```python
config = self.config_repository.load(require_existing_app=False)
```

В обоих launcher импортировать `select_application`, оставить существующее создание supervisor в `build_configured_application`, затем выбирать:

```python
def build_application(runtime_settings):
    return select_application(
        runtime_settings,
        os.path.isfile,
        build_configured_application,
    )
```

- [ ] **Step 5: Сохранить корректную замену приложения в текущей сессии**

После завершения Configurator перечитать конфигурацию без требования старого файла, затем построить replacement и сравнить путь вместе с признаком настройки:

```python
updated = settings_factory.build(
    repository.load(require_existing_app=False)
)
replacement = build_application(updated)
same_path = updated_path == current_path
same_state = bool(replacement.configured) == bool(
    holder["session"].application.configured
)
if same_path and same_state:
    return None
return replacement
```

Это позволяет запустить тот же текстовый путь, если файл появился и состояние изменилось с `configured=False` на `True`, и не создает ложную замену после отмены Configurator.

- [ ] **Step 6: Запустить parity-тест и подтвердить GREEN**

Повторить команду Step 2. Expected: `OK`.

### Task 3: Отобразить состояние «Приложение не настроено»

**Files:**
- Modify: `v2/modern/kiosk_v2_modern/app/session.py`
- Modify: `v2/legacy/kiosk_v2_legacy/app/session.py`
- Modify: `v2/modern/kiosk_v2_modern/ui/scene.py`
- Modify: `v2/legacy/kiosk_v2_legacy/ui/scene.py`
- Modify: `v2/modern/kiosk_v2_modern/ui/tk_view.py`
- Modify: `v2/legacy/kiosk_v2_legacy/ui/tk_view.py`
- Test: `v2/tests/test_view_scene.py`
- Test: `v2/tests/test_launcher_composition.py`

- [ ] **Step 1: Написать падающий тест модели и сцены**

```python
def test_unconfigured_scene_guides_admin_without_exposing_picker(self):
    for build in SCENE_BUILDERS:
        items = by_name(build(
            r"F:\Missing\Telegram.exe",
            application_configured=False,
        ))
        self.assertEqual("Не выбрано", items["application_name"]["text"])
        self.assertEqual("Не настроено", items["application_status"]["text"])
        self.assertEqual(
            "Надзор: ожидает настройки",
            items["supervision_status"]["text"],
        )
        actions = {item.get("action") for item in items}
        self.assertEqual({"unlock", None}, actions)
```

Для админ-сцены проверить наличие `changeApplication` и отсутствие `toggleSupervision` при `application_configured=False`.

В session parity-тесте проверить:

```python
self.assertFalse(session.model()["application_configured"])
```

- [ ] **Step 2: Запустить UI/parity-тесты и подтвердить RED**

```powershell
& 'C:\Users\impal\AppData\Local\Python38-32\python.exe' -m unittest `
  v2.tests.test_view_scene `
  v2.tests.test_launcher_composition -v
```

Expected: scene не принимает `application_configured`, модель не содержит поле.

- [ ] **Step 3: Передать состояние из session в scene**

В `LauncherSession.model()` добавить:

```python
"application_configured": bool(getattr(self.application, "configured", True)),
```

В обоих `tk_view.refresh()` передать:

```python
application_configured=model.get("application_configured", True),
```

- [ ] **Step 4: Отрисовать безопасное состояние**

Добавить `application_configured=True` в сигнатуру `build_operator_scene`. Для `False` использовать тексты:

```python
application_name = "Не выбрано"
application_path_text = "Разрешенное приложение не настроено."
status_text = "Не настроено"
supervision_text = "Надзор: ожидает настройки"
hint_text = "Разблокируйте режим и выберите разрешенное приложение."
```

Передать `application_configured` в `_admin_session_items` и добавлять кнопку `toggleSupervision` только при `True`. Кнопки `changeApplication`, `returnToKiosk`, `unlockDesktop` и `restore` остаются доступны только в авторизованной админ-сессии.

- [ ] **Step 5: Запустить UI/parity-тесты и подтвердить GREEN**

Повторить команду Step 2. Expected: `OK`.

### Task 4: Полная регрессия, сборка и безопасная проверка

**Files:**
- Verify: `v2/dist/modern/RezhimKioska-V2-Modern.exe`
- Verify: `v2/dist/legacy/RezhimKioska-V2-Legacy.exe`
- Verify: `v2/dist/SHA256SUMS.txt`

- [ ] **Step 1: Проверить diff и оба набора тестов**

```powershell
git diff --check
& 'C:\Users\impal\AppData\Local\Python38-32\python.exe' -m unittest discover -s v2/tests -p 'test_*.py'
& 'C:\Users\impal\AppData\Local\Python27-x86-portable\python.exe' -m unittest discover -s v2/tests/legacy -p 'test_*.py'
```

Expected: `git diff --check` без ошибок; Modern/parity и Legacy завершаются `OK`.

- [ ] **Step 2: Пересобрать оба комплекта**

```powershell
& 'v2\scripts\build-modern.ps1'
& 'v2\scripts\build-legacy.ps1'
```

Expected: exit code 0, обновлены оба launcher и `SHA256SUMS.txt`.

- [ ] **Step 3: Проверить свежую конфигурацию и старый отсутствующий путь**

Во временной копии комплекта установить `configured: false`, запустить Modern и подтвердить: оболочка открылась, разрешенный процесс не запущен, кнопка выбора отсутствует до авторизации. Затем проверить предоставленный сценарий с `configured` отсутствующим и путем `F:\Telegram Desktop\Telegram.exe`: оболочка также открывается без fatal traceback.

- [ ] **Step 4: Проверить персистентность выбора**

Через Configurator выбрать тестовый EXE после повышения прав, подтвердить сохраненные `configured: true`, `path` и `workingDirectory`. Повторный запуск должен сразу открыть ровно один выбранный процесс без повторного выбора.

- [ ] **Step 5: Обязательно восстановить ноутбук**

После живого теста остановить только процессы тестового launcher и созданного им приложения, запустить `%WINDIR%\explorer.exe`, проверить один Explorer текущей сессии, видимую панель задач и отсутствие Modern/Legacy kiosk-процессов. Службы, драйверы и автозагрузку не изменять.

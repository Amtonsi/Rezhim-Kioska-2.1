# Компоненты бинарных комплектов

Код киоска распространяется по лицензии [MIT](../../LICENSE). Для каждой сборки храним уведомления CPython, PyInstaller, Tcl и Tk. При упаковке копируем их в `licenses` рядом с программой. Для самораспаковывающегося контейнера используем штатный модуль 7-Zip 26.06 x86. В архив также помещаем лицензию из дистрибутива 7-Zip.

| Сборка | CPython | PyInstaller | Tcl/Tk |
|---|---|---|---|
| current-x64 | 3.14.10 | 6.22.3 | 9.0.4 |
| compat-x86 | 3.8.10 | 6.22.3 | 8.6.9 |
| legacy-x86 | 2.7.18 | 3.2.1 | 8.5.19 |

Исходные проекты и условия распространения: [CPython](https://github.com/python/cpython), [PyInstaller](https://github.com/pyinstaller/pyinstaller), [Tcl](https://github.com/tcltk/tcl), [Tk](https://github.com/tcltk/tk), [7-Zip 26.06 и исходники](https://github.com/ip7z/7zip/releases/tag/26.06).

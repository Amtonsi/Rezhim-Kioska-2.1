# Kiosk V2 UI and Dual Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render the approved Russian kiosk interface from V2 runtimes and produce separate Modern and Legacy x86 executables without importing V1.

**Architecture:** Each build has an independent Tk view and composition root. Both consume the versioned 1440x900 UI contract and implement the same pure uniform layout transform. Frozen launcher and Restore entry points are separate; release packaging remains side-by-side with V1 until VM acceptance.

**Tech Stack:** Tkinter/Canvas, Python 3.8 x86, Python 2.7 x86, ctypes DPI APIs, PyInstaller, PowerShell/CMD, `unittest`.

---

### Task 1: Uniform Layout and Exact Brand Contract

- [x] Write failing Modern and Legacy tests for 800x600, 1024x768, 1366x768, and 1920x1080. Assert one scale `min(width/1440,height/900)`, centred offsets, and no independent X/Y stretch.
- [x] Implement independent `LayoutTransform` classes under both `ui/layout.py` modules using only arithmetic available in Python 2.7.
- [x] Add contract tests for exact `РК`, `Режим киоска`, `2026`, and `разработал: Абдрахманов Амаль Даулетович` UTF-8 values.
- [x] Run Python 2.7 and Python 3.8 tests; commit `feat: add kiosk v2 responsive layout`.

### Task 2: Operator and Administrator Views

- [x] Write fake-canvas tests for operator status, minimized notice/restore button, unlock button, admin-session controls, and degraded isolation message.
- [x] Implement independent Tk/Canvas views that render the approved dark interface, square blue `РК` logo, fixed year badge, allowed-app panel, unlock panel, safety footer, and developer line.
- [x] Implement the modal local-username/password dialog with visible username input and `*` masking. Keep the keyboard guard running while the dialog is open.
- [x] Bind buttons once, keep the kiosk background below the allowed app and dialog, and expose only controller commands.
- [x] Run view tests and screenshot layout checks; commit `feat: render kiosk v2 Russian interface`.

### Task 3: Modern and Legacy Composition Roots

- [x] Write startup-order tests proving DPI setup precedes Tk, guards start before the allowed app, config is validated, and controller owns transitions.
- [x] Compose Modern adapters and independent Legacy adapters into launcher entry points. Do not import V1 or the other build.
- [x] Compose separate Restore entry points using backup/registry/ACL/artifact/recovery adapters without launcher/UI imports.
- [x] Add bounded periodic ticks for desktop isolation, process supervision, admin timeout, and UI status.
- [x] Run all runtime tests; commit `feat: compose kiosk v2 launchers`.

### Task 4: Frozen Builds and Release Package

- [ ] Add separate PyInstaller specs and build scripts for Python 3.8 x86 Modern and Python 2.7 x86 Legacy.
- [ ] Build launcher and Restore EXEs for each family, inspect PE machine type, and verify wrong-family guards without applying kiosk state.
- [ ] Package config defaults, scripts, documentation, build manifest, SHA-256 sums, source listing, and GitHub ZIP without logs/backups/state/cache.
- [ ] Run static import, frozen startup, config-load, and dry-run smoke tests; commit `build: package kiosk v2 dual release`.

### Task 5: VM Acceptance and Final Restore

- [ ] Test Modern on Windows 7 SP1 and available Windows 10/11; test Legacy on XP SP1/SP3 and Server 2003 snapshots.
- [ ] Execute the full keyboard, input, application lifecycle, admin auth, install/repair/test-mode/restore matrix at required resolutions and DPI.
- [ ] Compare services, drivers, startup, main-account shell, and operator-account baselines before/after.
- [ ] Run Restore after every test and retain sanitized logs/screenshots. Do not mark an unavailable platform ready.
- [ ] Complete the final report and only then mark both remaining install-plan verification items complete.

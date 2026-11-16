"""Create a portable ZIP and a self-extracting Windows EXE from a V2 build."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[2]
TARGETS = {
    "current-x64": ("modern-x64", "Modern", 0x8664, "Windows10-11-x64"),
    "compat-x86": ("modern", "Modern", 0x14C, "Windows7-Compat-x86"),
    "legacy-x86": ("legacy", "Legacy", 0x14C, "WindowsXP-Legacy-x86"),
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def machine(path):
    with path.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise ValueError("Invalid EXE: " + str(path))
        stream.seek(0x3C)
        stream.seek(struct.unpack("<I", stream.read(4))[0])
        if stream.read(4) != b"PE\0\0":
            raise ValueError("Missing PE header: " + str(path))
        return struct.unpack("<H", stream.read(2))[0]


def manifest(directory):
    return {
        path.relative_to(directory).as_posix(): sha256(path)
        for path in sorted(directory.rglob("*")) if path.is_file()
    }


def run(*args, **kwargs):
    subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def package(args, scratch):
    folder, family, architecture, name = TARGETS[args.target]
    build = ROOT / "v2/dist" / folder
    stage = scratch / "files"
    launcher = "RezhimKioska-V2-" + family + ".exe"
    required = [launcher, "Restore.exe", "Configurator.exe"]
    for component in ("Restore", "Configurator"):
        versioned = "{}-V2-{}.exe".format(component, family)
        required.append(versioned)
        if sha256(build / versioned) != sha256(build / (component + ".exe")):
            raise ValueError("Invalid alias for " + component)
    for exe in required:
        if machine(build / exe) != architecture:
            raise ValueError("Wrong EXE architecture: " + exe)
    default = ROOT / "config/kiosk.v2.default.json"
    config = build / "config/kiosk.v2.json"
    if config.read_bytes() != default.read_bytes():
        raise ValueError("The build config differs from the tracked release template")
    if json.loads(default.read_text(encoding="utf-8-sig"))["allowedApplication"]["configured"] is not False:
        raise ValueError("A new release must start without a selected application")
    if family == "Legacy":
        if not (build / "python27.dll").is_file() or not (build / "tcl").is_dir():
            raise ValueError("Incomplete Legacy runtime")
        shutil.copytree(build, stage)
    else:
        (stage / "config").mkdir(parents=True)
        shutil.copy2(default, stage / "config/kiosk.v2.json")
        for exe in required:
            shutil.copy2(build / exe, stage / exe)
    if any((stage / name).exists() for name in ("state", "Logs", "logs")):
        raise ValueError("Local backup or log directory in build")
    shutil.copy2(ROOT / "LICENSE", stage / "LICENSE.txt")
    shutil.copytree(ROOT / "docs/distribution-licenses" / args.target, stage / "licenses")
    shutil.copy2(args.sevenzip.parent / "License.txt", stage / "licenses/7-Zip.txt")
    instructions = (ROOT / "docs/FIRST-RUN.txt").read_text(encoding="utf-8-sig")
    (stage / "START-HERE.txt").write_bytes(instructions.replace("\n", "\r\n").encode("utf-8-sig"))
    contents = manifest(stage)
    lines = ["{}  {}".format(digest, path) for path, digest in contents.items()]
    (stage / "FILES-SHA256.txt").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    contents = manifest(stage)
    stem = "RezhimKioska-2.1.0-" + name
    archive = scratch / (stem + ".zip")
    executable = scratch / (stem + ".exe")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=8) as output:
        for path in contents:
            output.write(stage / path, path)
    sfx = args.sevenzip.with_name("7z.sfx")
    if args.target != "current-x64" and machine(sfx) != 0x14C:
        raise ValueError("Use the x86 7-Zip SFX module for x86 targets")
    run(args.sevenzip, "a", "-t7z", "-sfx" + str(sfx), "-mx=5", "-bd", "-y",
        executable, ".", cwd=stage, stdout=subprocess.DEVNULL)
    for container in (archive, executable):
        extracted = scratch / ("test-" + container.suffix[1:])
        run(args.sevenzip, "x", "-bd", "-y", "-o" + str(extracted), container,
            stdout=subprocess.DEVNULL)
        if manifest(extracted) != contents:
            raise ValueError("Packaged files failed verification: " + container.name)
    args.out.mkdir(parents=True, exist_ok=True)
    for verified in (archive, executable):
        destination = args.out / verified.name
        os.replace(str(verified), str(destination))
        print("{}  {}".format(sha256(destination), destination.name))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=TARGETS, required=True)
    parser.add_argument("--sevenzip", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "release")
    args = parser.parse_args()
    args.sevenzip = args.sevenzip.resolve()
    args.out = args.out.resolve()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(args.out.parent)) as temporary:
        package(args, Path(temporary))

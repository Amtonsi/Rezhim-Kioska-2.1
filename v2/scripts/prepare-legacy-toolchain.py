"""Prepare an isolated PyInstaller 3.2.1 toolchain for 32-bit CPython 2.7.18."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = [
    ("PyInstaller", "3.2.1", "PyInstaller-3.2.1.tar.bz2", "f08ca806bc26e62034bca181a4b85de22568a3d39bdb062f05927c6e86c2a48c"),
    ("dis3", "0.1.3", "dis3-0.1.3-py2-none-any.whl", "61f7720dd0d8749d23fda3d7227ce74d73da11c2fade993a67ab2f9852451b14"),
    ("setuptools", "44.1.1", "setuptools-44.1.1-py2.py3-none-any.whl", "27a714c09253134e60a6fa68130f78c7037e5562c4f21f8f318f2ae900d152d5"),
    ("future", "0.18.2", "future-0.18.2.tar.gz", "b1bead90b70cf6ec3f0710ae53a525360fa360d306a86583adc6bf83a4db537d"),
    ("pefile", "2017.11.5", "pefile-2017.11.5.tar.gz", "675c35ee0e1677db9e80d2f48d8a7ff2cf38e6207e8cd5e2a2c6d126db025854"),
    ("pywin32", "223", "pywin32-223-cp27-cp27m-win32.whl", "42f48567e36b787901ff3da20de5a134cd9880cc90832e2aad60951f058699f0"),
    ("pypiwin32", "223", "pypiwin32-223.tar.gz", "71be40c1fbd28594214ecaecb58e7aa8b708eabfa0125c8a109ebd51edbd776a"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python27", type=Path, required=True)
    parser.add_argument("--target", type=Path, default=ROOT / "v2/toolchain/pyinstaller-3.2.1")
    args = parser.parse_args()
    destination = args.target.resolve()
    if destination.exists() and any(destination.iterdir()):
        parser.error("choose an empty destination for this toolchain")
    python = str(args.python27.resolve())
    subprocess.run([python, "-c", "import struct, sys; assert sys.version_info[:3] == (2,7,18) and struct.calcsize('P') == 4"], check=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, version, filename, checksum in ARTIFACTS:
            with urlopen("https://pypi.org/pypi/{}/{}/json".format(name, version), timeout=60) as response:
                files = json.load(response)["urls"]
            url = next(item["url"] for item in files if item["filename"] == filename)
            with urlopen(url, timeout=120) as response:
                contents = response.read()
            if hashlib.sha256(contents).hexdigest() != checksum:
                raise ValueError("SHA-256 mismatch for " + filename)
            (Path(tmp) / filename).write_bytes(contents)
        subprocess.run([python, "-m", "pip", "--disable-pip-version-check", "install",
                        "--no-index", "--no-deps", "--find-links", tmp, "--target", str(destination),
                        "-r", str(ROOT / "requirements-legacy-build.txt"), "dis3==0.1.3"], check=True)


if __name__ == "__main__":
    main()

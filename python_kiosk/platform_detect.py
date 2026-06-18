import platform
import subprocess


class WindowsInfo(object):
    def __init__(self, major, minor, build, edition, product_name=""):
        self.major = int(major)
        self.minor = int(minor)
        self.build = int(build)
        self.edition = edition or ""
        self.product_name = product_name or ""

    @property
    def edition_lower(self):
        return (self.edition + " " + self.product_name).lower()


def _parse_version(version_text):
    parts = (version_text or "0.0.0").split(".")
    while len(parts) < 3:
        parts.append("0")
    numbers = []
    for part in parts[:3]:
        try:
            numbers.append(int(part))
        except ValueError:
            numbers.append(0)
    return numbers[0], numbers[1], numbers[2]


def _read_windows_caption():
    try:
        process = subprocess.Popen(
            ["wmic", "os", "get", "Caption", "/value"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = process.communicate()
    except (OSError, ValueError):
        return ""
    try:
        text = stdout.decode("utf-8", "ignore")
    except AttributeError:
        text = stdout
    for line in text.splitlines():
        if line.startswith("Caption="):
            return line.split("=", 1)[1].strip()
    return ""


def detect_windows_info():
    version = platform.version()
    major, minor, build = _parse_version(version)
    caption = _read_windows_caption()
    edition = caption.replace("Microsoft Windows", "").strip()
    return WindowsInfo(
        major=major,
        minor=minor,
        build=build,
        edition=edition,
        product_name=caption,
    )


def select_policy_profile(info):
    edition = info.edition_lower

    if info.major <= 5:
        return "xp_legacy"

    if "home" in edition:
        return "home_fallback"

    if info.major == 6 and info.minor <= 1:
        return "win7_srp"

    if info.major >= 10:
        if (
            "enterprise" in edition
            or "education" in edition
            or "iot" in edition
        ):
            return "win10_shelllauncher"
        return "win10_applocker"

    return "win7_srp"

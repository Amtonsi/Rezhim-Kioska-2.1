import platform
import subprocess


class WindowsInfo(object):
    def __init__(
        self,
        major,
        minor,
        build,
        edition,
        product_name="",
        service_pack_major=0,
        product_type=1,
        architecture="x86",
    ):
        self.major = int(major)
        self.minor = int(minor)
        self.build = int(build)
        self.edition = edition or ""
        self.product_name = product_name or ""
        self.service_pack_major = int(service_pack_major or 0)
        self.product_type = int(product_type or 1)
        self.architecture = (architecture or "x86").lower()

    @property
    def edition_lower(self):
        return (self.edition + " " + self.product_name).lower()


class CompatibilityResult(object):
    def __init__(self, supported, message=""):
        self.supported = bool(supported)
        self.message = message or ""


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


def _read_native_windows_info():
    if platform.system().lower() != "windows":
        return None

    try:
        import ctypes
        from ctypes import wintypes

        class OSVERSIONINFOEXW(ctypes.Structure):
            _fields_ = [
                ("dwOSVersionInfoSize", wintypes.DWORD),
                ("dwMajorVersion", wintypes.DWORD),
                ("dwMinorVersion", wintypes.DWORD),
                ("dwBuildNumber", wintypes.DWORD),
                ("dwPlatformId", wintypes.DWORD),
                ("szCSDVersion", wintypes.WCHAR * 128),
                ("wServicePackMajor", wintypes.WORD),
                ("wServicePackMinor", wintypes.WORD),
                ("wSuiteMask", wintypes.WORD),
                ("wProductType", wintypes.BYTE),
                ("wReserved", wintypes.BYTE),
            ]

        class SYSTEM_INFO_ARCH(ctypes.Structure):
            _fields_ = [
                ("wProcessorArchitecture", wintypes.WORD),
                ("wReserved", wintypes.WORD),
            ]

        class SYSTEM_INFO(ctypes.Structure):
            _fields_ = [
                ("arch", SYSTEM_INFO_ARCH),
                ("dwPageSize", wintypes.DWORD),
                ("lpMinimumApplicationAddress", wintypes.LPVOID),
                ("lpMaximumApplicationAddress", wintypes.LPVOID),
                ("dwActiveProcessorMask", ctypes.c_size_t),
                ("dwNumberOfProcessors", wintypes.DWORD),
                ("dwProcessorType", wintypes.DWORD),
                ("dwAllocationGranularity", wintypes.DWORD),
                ("wProcessorLevel", wintypes.WORD),
                ("wProcessorRevision", wintypes.WORD),
            ]

        rtl_get_version = ctypes.windll.ntdll.RtlGetVersion
        rtl_get_version.argtypes = [ctypes.POINTER(OSVERSIONINFOEXW)]
        rtl_get_version.restype = ctypes.c_long

        version = OSVERSIONINFOEXW()
        version.dwOSVersionInfoSize = ctypes.sizeof(version)
        if rtl_get_version(ctypes.byref(version)) != 0:
            return None

        system_info = SYSTEM_INFO()
        ctypes.windll.kernel32.GetNativeSystemInfo(ctypes.byref(system_info))
        architectures = {0: "x86", 9: "x64", 12: "arm64"}
        architecture = architectures.get(
            int(system_info.arch.wProcessorArchitecture),
            "unknown",
        )
        return {
            "major": int(version.dwMajorVersion),
            "minor": int(version.dwMinorVersion),
            "build": int(version.dwBuildNumber),
            "service_pack_major": int(version.wServicePackMajor),
            "product_type": int(version.wProductType),
            "architecture": architecture,
        }
    except (AttributeError, OSError, ValueError):
        return None


def detect_windows_info():
    native = _read_native_windows_info()
    if native:
        major = native["major"]
        minor = native["minor"]
        build = native["build"]
        service_pack_major = native["service_pack_major"]
        product_type = native["product_type"]
        architecture = native["architecture"]
    else:
        version = platform.version()
        major, minor, build = _parse_version(version)
        service_pack_major = 0
        product_type = 1
        machine = platform.machine().lower()
        architecture = {
            "amd64": "x64",
            "x86_64": "x64",
            "x86": "x86",
            "i386": "x86",
            "i686": "x86",
            "arm64": "arm64",
            "aarch64": "arm64",
        }.get(machine, machine or "unknown")
    caption = _read_windows_caption()
    edition = caption.replace("Microsoft Windows", "").strip()
    return WindowsInfo(
        major=major,
        minor=minor,
        build=build,
        edition=edition,
        product_name=caption,
        service_pack_major=service_pack_major,
        product_type=product_type,
        architecture=architecture,
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


def validate_modern_platform(info):
    if info.product_type != 1:
        return CompatibilityResult(
            False,
            "Эта сборка не поддерживает Windows Server.",
        )

    if info.architecture not in ("x86", "x64", "amd64"):
        return CompatibilityResult(
            False,
            "Архитектура Windows не поддерживается этой сборкой.",
        )

    if info.major < 6 or (info.major == 6 and info.minor < 1):
        return CompatibilityResult(
            False,
            "Используйте RezhimKioska-Legacy.exe.",
        )

    if (
        info.major == 6
        and info.minor == 1
        and info.service_pack_major < 1
    ):
        return CompatibilityResult(
            False,
            "Для Windows 7 требуется Service Pack 1.",
        )

    return CompatibilityResult(True)

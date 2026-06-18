# -*- coding: utf-8 -*-

import ctypes
from ctypes import wintypes


VER_NT_WORKSTATION = 1
PROCESSOR_ARCHITECTURE_INTEL = 0
PROCESSOR_ARCHITECTURE_AMD64 = 9
PROCESSOR_ARCHITECTURE_ARM64 = 12


class LegacyWindowsInfo(object):
    def __init__(
        self,
        major,
        minor,
        build,
        service_pack_major,
        product_type,
        architecture,
    ):
        self.major = int(major)
        self.minor = int(minor)
        self.build = int(build)
        self.service_pack_major = int(service_pack_major)
        self.product_type = int(product_type)
        self.architecture = architecture


class LegacyCompatibility(object):
    def __init__(self, supported, profile="", message=u""):
        self.supported = bool(supported)
        self.profile = profile
        self.message = message


class _OSVERSIONINFOEXW(ctypes.Structure):
    _fields_ = (
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
    )


class _SYSTEM_INFO_PROCESSOR(ctypes.Structure):
    _fields_ = (
        ("wProcessorArchitecture", wintypes.WORD),
        ("wReserved", wintypes.WORD),
    )


class _SYSTEM_INFO_UNION(ctypes.Union):
    _fields_ = (
        ("dwOemId", wintypes.DWORD),
        ("processor", _SYSTEM_INFO_PROCESSOR),
    )


class _SYSTEM_INFO(ctypes.Structure):
    _anonymous_ = ("info",)
    _fields_ = (
        ("info", _SYSTEM_INFO_UNION),
        ("dwPageSize", wintypes.DWORD),
        ("lpMinimumApplicationAddress", wintypes.LPVOID),
        ("lpMaximumApplicationAddress", wintypes.LPVOID),
        ("dwActiveProcessorMask", ctypes.c_size_t),
        ("dwNumberOfProcessors", wintypes.DWORD),
        ("dwProcessorType", wintypes.DWORD),
        ("dwAllocationGranularity", wintypes.DWORD),
        ("wProcessorLevel", wintypes.WORD),
        ("wProcessorRevision", wintypes.WORD),
    )


class NativePlatformApi(object):
    def __init__(self, kernel32=None):
        self.kernel32 = kernel32 or ctypes.windll.kernel32
        self._configure_signatures()

    def _configure_signatures(self):
        self.kernel32.GetVersionExW.argtypes = [ctypes.POINTER(_OSVERSIONINFOEXW)]
        self.kernel32.GetVersionExW.restype = wintypes.BOOL
        self.kernel32.GetNativeSystemInfo.argtypes = [ctypes.POINTER(_SYSTEM_INFO)]
        self.kernel32.GetNativeSystemInfo.restype = None

    def get_version_info(self):
        version = _OSVERSIONINFOEXW()
        version.dwOSVersionInfoSize = ctypes.sizeof(version)
        if not self.kernel32.GetVersionExW(ctypes.byref(version)):
            raise ctypes.WinError()
        return (
            version.dwMajorVersion,
            version.dwMinorVersion,
            version.dwBuildNumber,
            version.wServicePackMajor,
            version.wProductType,
        )

    def get_native_architecture(self):
        system_info = _SYSTEM_INFO()
        self.kernel32.GetNativeSystemInfo(ctypes.byref(system_info))
        architecture = system_info.processor.wProcessorArchitecture
        return {
            PROCESSOR_ARCHITECTURE_INTEL: "x86",
            PROCESSOR_ARCHITECTURE_AMD64: "x64",
            PROCESSOR_ARCHITECTURE_ARM64: "arm64",
        }.get(architecture, "unknown")


def detect_windows_info(api=None):
    api = api or NativePlatformApi()
    major, minor, build, service_pack_major, product_type = api.get_version_info()
    return LegacyWindowsInfo(
        major=major,
        minor=minor,
        build=build,
        service_pack_major=service_pack_major,
        product_type=product_type,
        architecture=api.get_native_architecture(),
    )


def validate_legacy_platform(info):
    if info.architecture != "x86":
        return LegacyCompatibility(
            False,
            message=u"Legacy-сборка поддерживает только 32-битную Windows x86.",
        )

    if info.major == 5 and info.minor == 1 and info.product_type == VER_NT_WORKSTATION:
        if info.service_pack_major < 1:
            return LegacyCompatibility(
                False,
                message=u"Требуется Windows XP Service Pack 1 или новее.",
            )
        return LegacyCompatibility(True, profile="xp_legacy")

    if info.major == 5 and info.minor == 2 and info.product_type != VER_NT_WORKSTATION:
        return LegacyCompatibility(True, profile="server2003_legacy")

    return LegacyCompatibility(
        False,
        message=(
            u"Эта Legacy-сборка предназначена только для Windows XP SP1+ "
            u"и Windows Server 2003 x86."
        ),
    )


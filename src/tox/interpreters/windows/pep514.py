"""Implement https://www.python.org/dev/peps/pep-0514/ to discover interpreters - Windows only"""
from __future__ import unicode_literals

import os
import re

import six
from six.moves import winreg

from tox import reporter
from tox.interpreters.py_spec import PythonSpec


def enum_keys(key):
    at = 0
    while True:
        try:
            yield winreg.EnumKey(key, at)
        except OSError:
            break
        at += 1


def get_value(key, value_name):
    try:
        return winreg.QueryValueEx(key, value_name)[0]
    except OSError:
        return None


def discover_pythons():
    for hive, hive_name, key, flags, default_arch in [
        (winreg.HKEY_CURRENT_USER, "HKEY_CURRENT_USER", r"Software\Python", 0, 64),
        (
            winreg.HKEY_LOCAL_MACHINE,
            "HKEY_LOCAL_MACHINE",
            r"Software\Python",
            winreg.KEY_WOW64_64KEY,
            64,
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            "HKEY_LOCAL_MACHINE",
            r"Software\Python",
            winreg.KEY_WOW64_32KEY,
            32,
        ),
    ]:
        yield from process_set(hive, hive_name, key, flags, default_arch)


def process_set(hive, hive_name, key, flags, default_arch):
    try:
        with winreg.OpenKeyEx(hive, key, 0, winreg.KEY_READ | flags) as root_key:
            for company in enum_keys(root_key):
                if company == "PyLauncher":  # reserved
                    continue
                yield from process_company(hive_name, company, root_key, default_arch)
    except OSError:
        pass


def process_company(hive_name, company, root_key, default_arch):
    with winreg.OpenKeyEx(root_key, company) as company_key:
        for tag in enum_keys(company_key):
            yield from process_tag(hive_name, company, company_key, tag, default_arch)


def process_tag(hive_name, company, company_key, tag, default_arch):
    with winreg.OpenKeyEx(company_key, tag) as tag_key:
        major, minor = load_version_data(hive_name, company, tag, tag_key)
        if major is None:
            return
        arch = load_arch_data(hive_name, company, tag, tag_key, default_arch)
    exe, args = load_exe(hive_name, company, company_key, tag)
    if exe is not None:
        name = "python" if company == "PythonCore" else company
        yield PythonSpec(name, major, minor, arch, exe, args)


def load_exe(hive_name, company, company_key, tag):
    key_path = f"{hive_name}/{company}/{tag}"
    try:
        with winreg.OpenKeyEx(company_key, f"{tag}\InstallPath") as ip_key:
            with ip_key:
                exe = get_value(ip_key, "ExecutablePath")
                if exe is None:
                    ip = get_value(ip_key, None)
                    if ip is None:
                        msg(key_path, "no ExecutablePath or default for it")

                    else:
                        exe = os.path.join(ip, "python.exe")
                if os.path.exists(exe):
                    args = get_value(ip_key, "ExecutableArguments")
                    return exe, args
                else:
                    msg(key_path, f"exe does not exists {exe}")
    except OSError:
        msg(f"{key_path}/InstallPath", "missing")
    return None, None


def load_arch_data(hive_name, company, tag, tag_key, default_arch):
    arch_str = get_value(tag_key, "SysArchitecture")
    if arch_str is not None:
        key_path = f"{hive_name}/{company}/{tag}/SysArchitecture"
        try:
            return parse_arch(arch_str)
        except ValueError as sys_arch:
            msg(key_path, sys_arch)
    return default_arch


def parse_arch(arch_str):
    if not isinstance(arch_str, six.string_types):
        raise ValueError("arch is not string")
    if match := re.match(r"(\d+)bit", arch_str):
        return int(next(iter(match.groups())))
    raise ValueError(f"invalid format {arch_str}")


def load_version_data(hive_name, company, tag, tag_key):
    version_str = get_value(tag_key, "SysVersion")
    major, minor = None, None
    if version_str is not None:
        key_path = f"{hive_name}/{company}/{tag}/SysVersion"
        try:
            major, minor = parse_version(get_value(tag_key, "SysVersion"))
        except ValueError as sys_version:
            msg(key_path, sys_version)
    if major is None:
        key_path = f"{hive_name}/{company}/{tag}"
        try:
            major, minor = parse_version(tag)
        except ValueError as tag_version:
            msg(key_path, tag_version)
    return major, minor


def parse_version(version_str):
    if not isinstance(version_str, six.string_types):
        raise ValueError("key is not string")
    if match := re.match(r"(\d+)\.(\d+).*", version_str):
        return tuple(int(i) for i in match.groups())
    raise ValueError(f"invalid format {version_str}")


def msg(path, what):
    reporter.verbosity1(
        f"PEP-514 violation in Windows Registry at {path} error: {what}"
    )


def _run():
    reporter.update_default_reporter(0, reporter.Verbosity.DEBUG)
    for spec in discover_pythons():
        print(repr(spec))


if __name__ == "__main__":
    _run()

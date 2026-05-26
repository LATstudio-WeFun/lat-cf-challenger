# latcf / agent

import platform
import subprocess
import os
import json
import re
from typing import Optional, List


def _plat_token() -> str:
    s = platform.system()
    if s == "Darwin":
        return "Macintosh; Intel Mac OS X 10_15_7"
    if s == "Linux":
        return "X11; Linux x86_64"
    return "Windows NT 10.0; Win64; x64"


def _parse_ver(text: str) -> Optional[str]:
    m = re.search(r"\d+(?:\.\d+){1,3}", text)
    return m.group(0) if m else None


def _read_chrome_ver(executable: str) -> Optional[str]:
    if platform.system() == "Windows":
        try:
            script = f'(Get-Item -LiteralPath {json.dumps(executable)}).VersionInfo.ProductVersion'
            out = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", script],
                capture_output=True, text=True, timeout=10,
            )
            return _parse_ver(out.stdout or "")
        except Exception:
            return None
    try:
        out = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=10)
        return _parse_ver((out.stdout or "") + " " + (out.stderr or ""))
    except Exception:
        return None


def _chrome_paths(channel: str = "") -> List[str]:
    if platform.system() != "Windows":
        if "edge" in channel:
            return ["microsoft-edge", "microsoft-edge-stable"]
        return ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "microsoft-edge-stable"]
    dirs = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LocalAppData")]
    dirs = [d for d in dirs if d]
    subs = {
        "edge": os.path.join("Microsoft", "Edge", "Application", "msedge.exe"),
        "msedge": os.path.join("Microsoft", "Edge", "Application", "msedge.exe"),
        "canary": os.path.join("Google", "Chrome SxS", "Application", "chrome.exe"),
        "beta": os.path.join("Google", "Chrome Beta", "Application", "chrome.exe"),
        "dev": os.path.join("Google", "Chrome Dev", "Application", "chrome.exe"),
        "chrome": os.path.join("Google", "Chrome", "Application", "chrome.exe"),
    }
    variant = next((k for k in subs if k in channel), None)
    sub = subs[variant] if variant else subs["msedge"]
    if variant == "canary":
        return [os.path.join(os.environ.get("LocalAppData", ""), sub)]
    return [os.path.join(d, sub) for d in dirs]


def _read_bundled_ver() -> Optional[str]:
    try:
        import patchright._impl._driver as drv
        browsers_path = os.path.join(os.path.dirname(drv.__file__), "browsers.json")
        if os.path.exists(browsers_path):
            with open(browsers_path, "r") as f:
                data = json.load(f)
            for b in data.get("browsers", []):
                if b.get("name") == "chromium":
                    return b.get("browserVersion")
    except Exception:
        pass
    return None


def plate(executable_path: Optional[str] = None, channel: Optional[str] = None) -> Optional[str]:
    env = os.environ.get("LAT_CF_HEADLESS_UA")
    if env == "0":
        return None
    if env:
        return env
    version = None
    if executable_path:
        version = _read_chrome_ver(executable_path)
    if not version and channel:
        for p in _chrome_paths(channel):
            if os.path.exists(p):
                version = _read_chrome_ver(p)
                if version:
                    break
    if not version:
        for p in _chrome_paths(channel or ""):
            if os.path.exists(p):
                version = _read_chrome_ver(p)
                if version:
                    break
    if not version:
        version = _read_bundled_ver() or "148.0.0.0"
    major = version.split(".")[0]
    return " ".join([
        "Mozilla/5.0",
        f"({_plat_token()})",
        "AppleWebKit/537.36",
        "(KHTML, like Gecko)",
        f"Chrome/{major}.0.0.0",
        "Safari/537.36",
    ])


def plate_context(options: dict, headless: bool = True) -> dict:
    if not headless:
        return options
    if options.get("user_agent"):
        return options
    ua = plate(
        executable_path=options.get("executable_path"),
        channel=options.get("channel"),
    )
    if ua:
        options = {**options, "user_agent": ua}
    return options

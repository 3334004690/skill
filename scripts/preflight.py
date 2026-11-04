#!/usr/bin/env python3
"""Check local dependencies and key presence without making API requests.

Exit codes: 0 ready; 1 configuration/install error; 2 missing dependencies;
3 missing API key. --install-deps runs pip through this Python interpreter.
Credentials are never printed or written, and key validity is not tested.
"""

import argparse
import importlib
import importlib.util
from importlib import metadata
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared_config import find_api_key

REQUIREMENTS_PATH = Path(__file__).resolve().with_name("requirements.txt")
MODULE_NAMES = {"python-dotenv": "dotenv", "Pillow": "PIL"}


def check_dependencies():
    """Check the declared packages and minimum versions with stdlib tools."""
    dependencies = []
    for line in REQUIREMENTS_PATH.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)>=(\d+(?:\.\d+)*)", line)
        if not match:
            raise ValueError("requirements.txt 包含无法自检的依赖声明")
        package, minimum = match.groups()
        module = MODULE_NAMES.get(package, package.replace("-", "_"))
        available = importlib.util.find_spec(module) is not None
        try:
            version = metadata.version(package)
        except metadata.PackageNotFoundError:
            version = None
        current = re.match(r"\d+(?:\.\d+)*", version or "")
        actual_parts = tuple(int(part) for part in current.group().split(".")) if current else ()
        minimum_parts = tuple(int(part) for part in minimum.split("."))
        length = max(len(actual_parts), len(minimum_parts))
        version_ok = (
            bool(current)
            and actual_parts + (0,) * (length - len(actual_parts))
            >= minimum_parts + (0,) * (length - len(minimum_parts))
        )
        dependencies.append({
            "package": package,
            "minimum": minimum,
            "version": version,
            "ok": available and version_ok,
        })
    return dependencies


def run_check(install_deps=False):
    result = {
        "ready": False,
        "python": sys.executable,
        "dependencies": [],
        "api_key_configured": False,
        "api_key_verified": False,
        "network_auth_checked": False,
    }
    try:
        result["api_key_configured"] = bool(find_api_key())
        dependencies = check_dependencies()
        if install_deps and any(not item["ok"] for item in dependencies):
            command = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)]
            completed = subprocess.run(command, stdout=sys.stderr, stderr=sys.stderr, check=False)
            if completed.returncode:
                result.update(status="dependency_install_failed", exit_code=1,
                              dependencies=dependencies, pip_exit_code=completed.returncode)
                return result
            importlib.invalidate_caches()
            dependencies = check_dependencies()
        result["dependencies"] = dependencies
    except (OSError, ValueError) as exc:
        result.update(status="configuration_error", exit_code=1,
                      error_type=type(exc).__name__)
        return result

    if any(not item["ok"] for item in dependencies):
        result.update(status="missing_dependencies", exit_code=2)
    elif not result["api_key_configured"]:
        result.update(status="missing_api_key", exit_code=3)
    else:
        result.update(ready=True, status="ready", exit_code=0)
    return result


def main():
    parser = argparse.ArgumentParser(description="依赖与鉴权配置自检（不发送 API 请求）")
    parser.add_argument("--install-deps", action="store_true",
                        help="缺少依赖时，用当前 Python 的 pip 安装 scripts/requirements.txt")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出自检结果")
    args = parser.parse_args()
    result = run_check(args.install_deps)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("Python: " + result["python"])
        for item in result["dependencies"]:
            state = "OK" if item["ok"] else "MISSING/OUTDATED"
            print("{}: {} {} (要求 >= {})".format(
                state, item["package"], item["version"] or "未安装", item["minimum"]))
        print("AIMAXHUG_API_KEY: " + ("已配置" if result["api_key_configured"] else "未配置"))
        print("仅检查配置存在性，未联网验证密钥。")
        if result["status"] == "missing_dependencies":
            print("请执行：python scripts/preflight.py --install-deps")
        if not result["api_key_configured"]:
            print("需要用户或管理员预先配置环境变量或项目 .env；脚本不会创建或修改密钥配置。")
        if result["exit_code"] == 1:
            print("自检失败：" + result["status"])
            if result["status"] == "dependency_install_failed":
                print("请根据 pip 输出检查网络或包源；可执行恢复步骤见 AUTH.md。")
    return result["exit_code"]


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

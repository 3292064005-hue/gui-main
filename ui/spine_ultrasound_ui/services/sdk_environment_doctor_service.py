from __future__ import annotations

import os
import platform
import shutil
import sys
from importlib import metadata
from dataclasses import dataclass, field
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.runtime_version_policy import (
    check_cmake_version,
    check_protobuf_runtime_version,
    check_pyside6_version,
    check_ubuntu_2204,
)
from spine_ultrasound_ui.services.sdk_vendor_locator import SdkVendorLayout, SdkVendorLocator


@dataclass
class DoctorCheck:
    name: str
    ok: bool
    severity: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": bool(self.ok),
            "severity": self.severity,
            "detail": self.detail,
        }


@dataclass
class SdkEnvironmentDoctorSnapshot:
    summary_state: str = "unknown"
    summary_label: str = "环境未检查"
    detail: str = "尚未执行环境检查。"
    blockers: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    toolchain: dict[str, Any] = field(default_factory=dict)
    sdk_paths: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_state": self.summary_state,
            "summary_label": self.summary_label,
            "detail": self.detail,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "checks": list(self.checks),
            "toolchain": dict(self.toolchain),
            "sdk_paths": dict(self.sdk_paths),
        }


class SdkEnvironmentDoctorService:
    """Local environment preflight for the xCore desktop+core mainline."""

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = Path(root_dir or Path(__file__).resolve().parents[2])
        self.snapshot = SdkEnvironmentDoctorSnapshot()
        self.locator = SdkVendorLocator(self.root_dir)

    def _display_path(self, path: Path | str | None) -> str:
        """Render repository-local paths portably while keeping host paths explicit."""
        if path is None:
            return ''
        candidate = Path(path)
        try:
            resolved = candidate.resolve(strict=False)
            root_resolved = self.root_dir.resolve(strict=False)
        except Exception:
            resolved = candidate
            root_resolved = self.root_dir
        try:
            relative = resolved.relative_to(root_resolved)
        except ValueError:
            return str(candidate)
        return relative.as_posix()

    def _display_layout_dict(self, layout: SdkVendorLayout) -> dict[str, Any]:
        payload = layout.to_dict()
        for key in (
            'sdk_root', 'include_dir', 'external_dir', 'lib_dir',
            'static_lib', 'shared_lib', 'nomodel_shared_lib', 'xmate_model_lib',
        ):
            value = payload.get(key)
            if value:
                payload[key] = self._display_path(value)
        return payload

    def inspect(self, config: RuntimeConfig) -> dict[str, Any]:
        checks: list[DoctorCheck] = []
        python_ok = sys.version_info >= (3, 11)
        checks.append(self._check(
            "Python 版本",
            python_ok,
            "blocker",
            f"Python {platform.python_version()}" + ("" if python_ok else "，主线要求 3.11+"),
        ))
        ubuntu_check = check_ubuntu_2204()
        checks.append(self._check(
            "Ubuntu 22.04 基线",
            ubuntu_check.ok,
            "warning",
            ubuntu_check.detail or f"{platform.system()} {platform.release()} / {platform.version()}",
        ))
        checks.extend(self._toolchain_checks())
        checks.extend(self._protobuf_runtime_checks())
        checks.extend(self._protocol_asset_checks())
        checks.extend(self._sdk_mount_checks())
        checks.extend(self._tls_checks())
        checks.extend(self._network_checks(config))

        blockers = [item.to_dict() for item in checks if item.severity == "blocker" and not item.ok]
        warnings = [item.to_dict() for item in checks if item.severity == "warning" and not item.ok]
        summary_state = "ready"
        if blockers:
            summary_state = "blocked"
        elif warnings:
            summary_state = "warning"
        summary_label = {
            "ready": "环境主线就绪",
            "warning": "环境存在告警",
            "blocked": "环境主线阻塞",
        }[summary_state]
        detail = "本机已满足 xCore 桌面/核心主线前提。" if summary_state == "ready" else (
            "需要先补齐本机依赖、vendored SDK 结构或 TLS 材料，才能进入真实 robot_core 主线。" if summary_state == "blocked" else "存在非阻塞告警，建议在进入实机前修正。"
        )
        layout = self.locator.locate()
        self.snapshot = SdkEnvironmentDoctorSnapshot(
            summary_state=summary_state,
            summary_label=summary_label,
            detail=detail,
            blockers=blockers,
            warnings=warnings,
            checks=[item.to_dict() for item in checks],
            toolchain={
                "python": platform.python_version(),
                "cmake": shutil.which("cmake") or "",
                "g++": shutil.which("g++") or shutil.which("clang++") or "",
                "protoc": shutil.which("protoc") or "",
                "node": shutil.which("node") or "",
                "npm": shutil.which("npm") or "",
                "openssl": shutil.which("openssl") or "",
                "python_protobuf_runtime": self._python_protobuf_version(),
                "protobuf_impl": os.getenv("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", ""),
            },
            sdk_paths={
                **self._display_layout_dict(layout),
                "tls_runtime_dir": self._display_path(self.root_dir / "configs" / "tls" / "runtime"),
            },
        )
        return self.snapshot.to_dict()

    def _toolchain_checks(self) -> list[DoctorCheck]:
        openssl_header = Path("/usr/include/openssl/ssl.h")
        eigen_header = Path("/usr/include/eigen3/Eigen/Core")
        vendored_eigen_header = self.root_dir / "third_party" / "rokae_xcore_sdk" / "robot" / "external" / "Eigen" / "Core"
        eigen_ok = eigen_header.exists() or vendored_eigen_header.exists()
        eigen_detail = self._display_path(eigen_header if eigen_header.exists() else vendored_eigen_header if vendored_eigen_header.exists() else Path("/usr/include/eigen3/Eigen/Core"))
        cmake_path = shutil.which("cmake")
        cmake_raw_version = self._tool_version(cmake_path, "--version")
        cmake_check = check_cmake_version(cmake_raw_version)
        pyside6_version = self._distribution_version("PySide6")
        pyside6_check = check_pyside6_version(pyside6_version) if pyside6_version else None
        checks = [
            self._check("CMake", cmake_path is not None and cmake_check.ok, "blocker", cmake_path if cmake_path and cmake_check.ok else (cmake_check.detail if cmake_path else "未找到 cmake")),
            self._check("C++ 编译器", shutil.which("g++") is not None or shutil.which("clang++") is not None, "blocker", shutil.which("g++") or shutil.which("clang++") or "未找到 g++/clang++"),
            self._check("Protobuf schema tooling", shutil.which("protoc") is not None, "warning", shutil.which("protoc") or "未找到 protoc（当前 C++ 主线已使用仓库内置兼容 codec，可选）"),
            self._check("Eigen 头文件", eigen_ok, "blocker", eigen_detail if eigen_ok else "未找到 Eigen 头文件，也未发现 vendored SDK external/Eigen"),
            self._check("OpenSSL", shutil.which("openssl") is not None, "warning", shutil.which("openssl") or "未找到 openssl"),
            self._check("OpenSSL 开发头文件", openssl_header.exists(), "blocker", str(openssl_header) if openssl_header.exists() else "未找到 openssl 头文件"),
        ]
        if pyside6_check is None:
            checks.append(self._check("PySide6", False, "warning", "未安装 PySide6（桌面入口要求 >=6.7）"))
        else:
            checks.append(self._check("PySide6", pyside6_check.ok, "warning", pyside6_check.detail))
        return checks


    def _protobuf_runtime_checks(self) -> list[DoctorCheck]:
        version = self._python_protobuf_version()
        impl = os.getenv("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "")
        version_check = check_protobuf_runtime_version(version) if version else None
        return [
            self._check(
                "Python protobuf runtime",
                bool(version_check and version_check.ok),
                "warning",
                version_check.detail if version_check else "未安装 Python protobuf runtime",
            ),
            self._check(
                "protobuf Python 实现策略",
                impl == "python",
                "warning",
                impl or "未设置，默认将由 protobuf 自行选择实现",
            ),
        ]


    def _protocol_asset_checks(self) -> list[DoctorCheck]:
        proto = self.root_dir / "cpp_robot_core" / "proto" / "ipc_messages.proto"
        python_pb2 = self.root_dir / "spine_ultrasound_ui" / "services" / "ipc_messages_pb2.py"
        cpp_header = self.root_dir / "cpp_robot_core" / "include" / "ipc_messages.pb.h"
        cpp_source = self.root_dir / "cpp_robot_core" / "src" / "ipc_messages.pb.cpp"
        sync_script = self.root_dir / "scripts" / "check_protocol_sync.py"
        return [
            self._check("Protocol proto source", proto.exists(), "blocker", self._display_path(proto)),
            self._check("Python pb2 asset", python_pb2.exists(), "blocker", self._display_path(python_pb2)),
            self._check("C++ wire codec header", cpp_header.exists(), "blocker", self._display_path(cpp_header)),
            self._check("C++ wire codec source", cpp_source.exists(), "blocker", self._display_path(cpp_source)),
            self._check("Protocol sync gate script", sync_script.exists(), "warning", self._display_path(sync_script)),
        ]

    def _sdk_mount_checks(self) -> list[DoctorCheck]:
        layout = self.locator.locate()
        return [
            self._check("xCore SDK 根目录", layout.sdk_root is not None, "blocker", self._display_path(layout.sdk_root) if layout.sdk_root else "未找到 vendored SDK"),
            self._check("xCore SDK include", layout.include_dir is not None, "blocker", self._display_path(layout.include_dir) if layout.include_dir else "include 缺失"),
            self._check("xCore SDK external", layout.external_dir is not None, "blocker", self._display_path(layout.external_dir) if layout.external_dir else "external 缺失"),
            self._check("xCore SDK 静态库", layout.static_lib is not None, "blocker", self._display_path(layout.static_lib) if layout.static_lib else "libxCoreSDK.a 缺失"),
            self._check("xMateModel 静态库", layout.xmate_model_available, "warning", self._display_path(layout.xmate_model_lib) if layout.xmate_model_lib else "libxMateModel.a 缺失"),
        ]

    def _tls_checks(self) -> list[DoctorCheck]:
        runtime_dir = self.root_dir / "configs" / "tls" / "runtime"
        material = list(runtime_dir.glob("*.pem")) + list(runtime_dir.glob("*.crt")) + list(runtime_dir.glob("*.key"))
        return [
            self._check("TLS runtime 目录", runtime_dir.exists(), "blocker", self._display_path(runtime_dir)),
            self._check("TLS 证书材料", bool(material), "warning", f"{self._display_path(runtime_dir)} / {len(material)} files"),
        ]

    def _network_checks(self, config: RuntimeConfig) -> list[DoctorCheck]:
        same_subnet = self._same_subnet(config.remote_ip, config.local_ip)
        return [
            self._check("remote/local IP 配置", bool(config.remote_ip and config.local_ip), "blocker", f"remote={config.remote_ip}, local={config.local_ip}"),
            self._check("直连网段一致性", same_subnet, "warning", f"remote={config.remote_ip}, local={config.local_ip}"),
            self._check("主线链路", config.preferred_link == "wired_direct", "blocker", f"preferred_link={config.preferred_link}"),
        ]

    @staticmethod
    def _check(name: str, ok: bool, severity: str, detail: str) -> DoctorCheck:
        return DoctorCheck(name=name, ok=bool(ok), severity=severity, detail=detail)

    @staticmethod
    def _same_subnet(remote_ip: str, local_ip: str) -> bool:
        try:
            remote = IPv4Address(remote_ip)
            local = IPv4Address(local_ip)
        except Exception:
            return False
        return remote.packed[:3] == local.packed[:3]

    @staticmethod
    def _python_protobuf_version() -> str:
        return SdkEnvironmentDoctorService._distribution_version("protobuf")

    @staticmethod
    def _distribution_version(distribution_name: str) -> str:
        try:
            return metadata.version(distribution_name)
        except metadata.PackageNotFoundError:
            return ""
        except Exception:
            return ""

    @staticmethod
    def _tool_version(executable: str | None, *args: str) -> str:
        if not executable:
            return ""
        import subprocess

        try:
            completed = subprocess.run([executable, *args], check=True, capture_output=True, text=True, timeout=5)
        except Exception:
            return ""
        first_line = (completed.stdout or completed.stderr).splitlines()
        return first_line[0] if first_line else ""

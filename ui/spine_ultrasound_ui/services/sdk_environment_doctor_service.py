from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from importlib import metadata
from dataclasses import dataclass, field
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any, Mapping

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.runtime_version_policy import (
    check_cmake_version,
    check_protobuf_runtime_version,
    check_pyside6_version,
    check_ubuntu_2204,
)
from spine_ultrasound_ui.services.sdk_vendor_locator import SdkVendorLayout, SdkVendorLocator
from spine_ultrasound_ui.services.runtime_source_policy_service import RuntimeSourcePolicyService


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
        checks.extend(self._rt_host_checks())
        checks.extend(self._source_policy_checks(config))

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


    def _source_policy_checks(self, config: RuntimeConfig) -> list[DoctorCheck]:
        policy = RuntimeSourcePolicyService().build_snapshot(config=config)
        detail = (
            f"profile={policy.deployment_profile}, camera={policy.camera_source_tier}, "
            f"force={policy.force_source_tier}, shell={policy.shell_write_tier}"
        )
        return [
            self._check(
                "运行源分层策略",
                not bool(policy.blockers),
                "blocker" if policy.deployment_profile in {"research", "clinical"} else "warning",
                detail if not policy.blockers else detail + " / " + "; ".join(policy.blockers),
            ),
            self._check(
                "锁定会话数据源",
                bool(policy.session_lock_ready),
                "blocker" if policy.deployment_profile in {"lab", "research", "clinical"} else "warning",
                detail if policy.session_lock_ready else detail + " / session_lock blocked",
            ),
            self._check(
                "执行面写控制权",
                bool(policy.execution_write_ready),
                "blocker" if policy.deployment_profile in {"research", "clinical"} else "warning",
                detail if policy.execution_write_ready else detail + " / execution_write blocked",
            ),
        ]


    def _rt_host_checks(self) -> list[DoctorCheck]:
        repo_service_file = self.root_dir / "configs" / "systemd" / "spine-cpp-core.service"
        repo_env_file = self.root_dir / "configs" / "systemd" / "spine-cpp-core.env"
        deployed_service_file = Path("/etc/systemd/system/spine-cpp-core.service")
        deployed_env_file = Path("/etc/default/spine-cpp-core")
        service_file = deployed_service_file if deployed_service_file.exists() else repo_service_file
        env_file = deployed_env_file if deployed_env_file.exists() else repo_env_file
        bootstrap_header = self.root_dir / "cpp_robot_core" / "include" / "robot_core" / "rt_host_bootstrap.h"
        bootstrap_source = self.root_dir / "cpp_robot_core" / "src" / "rt_host_bootstrap.cpp"
        main_source = self.root_dir / "cpp_robot_core" / "src" / "main_ubuntu_rt.cpp"
        service_text = service_file.read_text(encoding="utf-8") if service_file.exists() else ""
        env_text = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
        main_text = main_source.read_text(encoding="utf-8") if main_source.exists() else ""
        env_map = self._parse_env_contract_text(env_text)
        contract_matrix = self._load_rt_host_contract_matrix()
        contract_matrix_path = self.root_dir / "configs" / "runtime" / "rt_host_profiles.json"
        selected_label, selected_profile = self._select_rt_host_contract_profile(env_map, contract_matrix)
        service_has_memlock = "LimitMEMLOCK=infinity" in service_text and "LimitRTPRIO=99" in service_text
        service_has_env = "EnvironmentFile=-/etc/default/spine-cpp-core" in service_text
        service_scheduler_policy = self._parse_systemd_scalar(service_text, "CPUSchedulingPolicy")
        service_scheduler_priority = self._parse_systemd_int(service_text, "CPUSchedulingPriority")
        env_scheduler_policy = str(env_map.get("SPINE_RT_SCHED_POLICY", "")).strip().lower()
        env_scheduler_priority = self._parse_optional_int(env_map.get("SPINE_RT_SCHED_PRIORITY", ""))
        service_has_scheduler = bool(
            service_scheduler_policy
            and env_scheduler_policy
            and service_scheduler_priority is not None
            and env_scheduler_priority is not None
            and service_scheduler_policy == env_scheduler_policy
            and service_scheduler_priority == env_scheduler_priority
        )
        service_cpu_affinity = self._parse_systemd_cpu_affinity(service_text)
        env_cpu_affinity = self._parse_cpu_affinity_csv(env_map.get("SPINE_RT_CPU_SET", ""))
        cpu_contract_aligned = bool(service_cpu_affinity and env_cpu_affinity and service_cpu_affinity == env_cpu_affinity)
        bootstrap_has_explicit_sched = "applyRtHostBootstrap" in main_text and "loadRtHostBootstrapConfigFromEnv" in main_text and "SPINE_RT_HOST_CONTRACT_VERSION" in bootstrap_source.read_text(encoding="utf-8") if bootstrap_source.exists() else False
        required_env_keys = {
            "SPINE_RT_HOST_CONTRACT_VERSION",
            "SPINE_RT_HOST_CONTRACT_LABEL",
            "SPINE_RT_SCHED_POLICY",
            "SPINE_RT_SCHED_PRIORITY",
            "SPINE_RT_CPU_SET",
            "SPINE_RT_FIXED_HOST_ID",
            "SPINE_RT_REQUIRE_SCHEDULER",
            "SPINE_RT_REQUIRE_AFFINITY",
            "SPINE_RT_REQUIRE_MEMORY_LOCK",
            "SPINE_RT_REQUIRE_PREEMPT_RT",
            "SPINE_RT_REQUIRE_FIXED_HOST_ID",
        }
        env_complete = required_env_keys.issubset(set(env_map))
        profile_selected = bool(selected_label and selected_profile)
        env_label_matches = bool(selected_label and str(env_map.get("SPINE_RT_HOST_CONTRACT_LABEL", "")).strip() == selected_label)
        env_fixed_host_matches = bool(
            not bool(selected_profile.get("require_fixed_host_id", False))
            or (
                bool(str(env_map.get("SPINE_RT_FIXED_HOST_ID", "")).strip())
                and str(env_map.get("SPINE_RT_FIXED_HOST_ID", "")).strip() == str(selected_profile.get("fixed_host_id", "")).strip()
            )
        )
        fixed_host_topology_selected = bool(
            profile_selected
            and str(selected_profile.get("deployment_topology", "")).strip() == "single_fixed_workstation"
            and bool(selected_profile.get("require_fixed_host_id", False))
        )
        scheduler_matches_profile = bool(
            profile_selected
            and env_fixed_host_matches
            and service_scheduler_policy == str(selected_profile.get("scheduler_policy", ""))
            and env_scheduler_policy == str(selected_profile.get("scheduler_policy", ""))
            and service_scheduler_priority == selected_profile.get("scheduler_priority")
            and env_scheduler_priority == selected_profile.get("scheduler_priority")
        )
        cpu_matches_profile = bool(profile_selected and service_cpu_affinity == list(selected_profile.get("cpu_set", [])) and env_cpu_affinity == list(selected_profile.get("cpu_set", [])))
        env_requirements_match_profile = bool(
            profile_selected
            and bool(int(str(env_map.get("SPINE_RT_REQUIRE_SCHEDULER", "0") or "0"))) == bool(selected_profile.get("require_scheduler", False))
            and bool(int(str(env_map.get("SPINE_RT_REQUIRE_AFFINITY", "0") or "0"))) == bool(selected_profile.get("require_affinity", False))
            and bool(int(str(env_map.get("SPINE_RT_REQUIRE_MEMORY_LOCK", "0") or "0"))) == bool(selected_profile.get("require_memory_lock", False))
            and bool(int(str(env_map.get("SPINE_RT_REQUIRE_PREEMPT_RT", "0") or "0"))) == bool(selected_profile.get("require_preempt_rt", False))
            and bool(int(str(env_map.get("SPINE_RT_REQUIRE_FIXED_HOST_ID", "0") or "0"))) == bool(selected_profile.get("require_fixed_host_id", False))
        )
        realtime_flag = Path("/sys/kernel/realtime")
        realtime_ready = realtime_flag.exists() and realtime_flag.read_text(encoding="utf-8", errors="ignore").strip() == "1"
        grub_file = Path("/etc/default/grub")
        grub_text = grub_file.read_text(encoding="utf-8", errors="ignore") if grub_file.exists() else ""
        cpu_tokens = []
        if env_cpu_affinity:
            cpu_csv = ','.join(str(item) for item in env_cpu_affinity)
            cpu_tokens = [f"isolcpus={cpu_csv}", f"rcu_nocbs={cpu_csv}", f"nohz_full={cpu_csv}"]
        grub_cpu_isolation_required = bool(selected_profile.get("grub_cpu_isolation_required", bool(cpu_tokens))) if profile_selected else bool(cpu_tokens)
        grub_cpu_isolation_aligned = (not grub_cpu_isolation_required) or (bool(cpu_tokens) and all(token in grub_text for token in cpu_tokens))
        path_detail = f"service={self._display_path(service_file)} env={self._display_path(env_file)} profile={selected_label or '-'}"
        return [
            self._check("RT host contract matrix", bool(contract_matrix) and contract_matrix_path.exists(), "blocker", self._display_path(contract_matrix_path)),
            self._check("RT host contract profile", profile_selected and env_label_matches, "blocker", path_detail + (" / contract profile selected" if profile_selected and env_label_matches else " / env label missing or profile not found")),
            self._check("RT host bootstrap source", bootstrap_header.exists() and bootstrap_source.exists(), "blocker", f"{self._display_path(bootstrap_header)} / {self._display_path(bootstrap_source)}"),
            self._check("RT host explicit scheduler bootstrap", bootstrap_has_explicit_sched, "blocker", self._display_path(main_source)),
            self._check("RT host systemd env contract", service_has_env and env_file.exists() and env_complete, "blocker", path_detail + (" / contract keys present" if service_has_env and env_file.exists() and env_complete else " / missing EnvironmentFile or contract keys")),
            self._check("RT host systemd scheduler policy", service_has_scheduler, "blocker", self._display_path(service_file) + (f" / policy={service_scheduler_policy} priority={service_scheduler_priority}" if service_has_scheduler else f" / service policy={service_scheduler_policy or '-'} priority={service_scheduler_priority if service_scheduler_priority is not None else '-'} env policy={env_scheduler_policy or '-'} priority={env_scheduler_priority if env_scheduler_priority is not None else '-'}")),
            self._check("RT host fixed workstation identity", fixed_host_topology_selected and env_fixed_host_matches, "blocker", f"profile={selected_label or '-'} expected_host={selected_profile.get('fixed_host_id', '-') if selected_profile else '-'} env_host={env_map.get('SPINE_RT_FIXED_HOST_ID', '-') or '-'} topology={selected_profile.get('deployment_topology', '-') if selected_profile else '-'}"),
            self._check("RT host profile scheduler alignment", scheduler_matches_profile, "blocker", f"profile={selected_label or '-'} expected_policy={selected_profile.get('scheduler_policy', '-') if selected_profile else '-'} expected_priority={selected_profile.get('scheduler_priority', '-') if selected_profile else '-'}"),
            self._check("RT host systemd memlock/rtprio", service_has_memlock, "blocker", self._display_path(service_file) + (" / memlock+rtprio configured" if service_has_memlock else " / missing LimitMEMLOCK or LimitRTPRIO")),
            self._check("RT host CPU affinity contract", cpu_contract_aligned, "blocker", f"service={','.join(str(item) for item in service_cpu_affinity) or '-'} env={','.join(str(item) for item in env_cpu_affinity) or '-'}"),
            self._check("RT host profile CPU alignment", cpu_matches_profile, "blocker", f"profile={selected_label or '-'} expected={','.join(str(item) for item in selected_profile.get('cpu_set', [])) or '-'} service={','.join(str(item) for item in service_cpu_affinity) or '-'} env={','.join(str(item) for item in env_cpu_affinity) or '-'}"),
            self._check("RT host profile requirement flags", env_requirements_match_profile, "blocker", f"profile={selected_label or '-'} require_scheduler={selected_profile.get('require_scheduler', '-') if selected_profile else '-'} require_affinity={selected_profile.get('require_affinity', '-') if selected_profile else '-'} require_memory_lock={selected_profile.get('require_memory_lock', '-') if selected_profile else '-'} require_preempt_rt={selected_profile.get('require_preempt_rt', '-') if selected_profile else '-'} require_fixed_host_id={selected_profile.get('require_fixed_host_id', '-') if selected_profile else '-'}"),
            self._check("RT host GRUB CPU isolation", grub_cpu_isolation_aligned, "warning", self._display_path(grub_file) + (f" / {' '.join(cpu_tokens)}" if grub_cpu_isolation_aligned else " / CPU isolation tokens missing or not aligned with SPINE_RT_CPU_SET")),
            self._check("RT kernel flag", realtime_ready, "warning", str(realtime_flag) if realtime_flag.exists() else "host missing /sys/kernel/realtime; PREEMPT_RT must be verified on target machine"),
        ]


    def _load_rt_host_contract_matrix(self) -> dict[str, Any]:
        matrix_path = self.root_dir / "configs" / "runtime" / "rt_host_profiles.json"
        if not matrix_path.exists():
            return {}
        try:
            payload = json.loads(matrix_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        return payload

    @staticmethod
    def _normalize_rt_host_profile(profile: Mapping[str, Any] | None) -> dict[str, Any]:
        payload = dict(profile or {})
        cpu_set = payload.get("cpu_set", [])
        normalized_cpu: list[int] = []
        if isinstance(cpu_set, (list, tuple)):
            for item in cpu_set:
                try:
                    normalized_cpu.append(int(item))
                except (TypeError, ValueError):
                    return {}
        payload["cpu_set"] = normalized_cpu
        payload["scheduler_policy"] = str(payload.get("scheduler_policy", "")).strip().lower()
        payload["scheduler_priority"] = SdkEnvironmentDoctorService._parse_optional_int(payload.get("scheduler_priority"))
        payload["fixed_host_id"] = str(payload.get("fixed_host_id", "") or "").strip()
        payload["deployment_topology"] = str(payload.get("deployment_topology", "") or "").strip()
        for key in ("require_scheduler", "require_affinity", "require_memory_lock", "require_preempt_rt", "require_fixed_host_id", "grub_cpu_isolation_required"):
            payload[key] = bool(payload.get(key, False))
        return payload

    def _select_rt_host_contract_profile(self, env_map: Mapping[str, str], matrix: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
        profiles = dict(matrix.get("profiles") or {})
        requested_label = str(env_map.get("SPINE_RT_HOST_CONTRACT_LABEL", "")).strip()
        if requested_label and requested_label in profiles:
            return requested_label, self._normalize_rt_host_profile(profiles.get(requested_label))
        if profiles:
            label = next(iter(profiles))
            return label, self._normalize_rt_host_profile(profiles.get(label))
        return requested_label, {}

    @staticmethod
    def _parse_env_contract_text(text: str) -> dict[str, str]:
        payload: dict[str, str] = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            payload[key.strip()] = value.strip()
        return payload

    @staticmethod
    def _parse_cpu_affinity_csv(value: str) -> list[int]:
        items: list[int] = []
        for token in (part.strip() for part in str(value or '').split(',')):
            if not token:
                continue
            try:
                items.append(int(token))
            except ValueError:
                return []
        return items

    @staticmethod
    def _parse_optional_int(value: object) -> int | None:
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_systemd_scalar(service_text: str, key: str) -> str:
        prefix = f"{key}="
        for raw_line in service_text.splitlines():
            line = raw_line.strip()
            if line.startswith(prefix):
                return line.split('=', 1)[1].strip().lower()
        return ""

    @staticmethod
    def _parse_systemd_int(service_text: str, key: str) -> int | None:
        return SdkEnvironmentDoctorService._parse_optional_int(SdkEnvironmentDoctorService._parse_systemd_scalar(service_text, key))

    @staticmethod
    def _parse_systemd_cpu_affinity(service_text: str) -> list[int]:
        for raw_line in service_text.splitlines():
            line = raw_line.strip()
            if not line.startswith('CPUAffinity='):
                continue
            return [int(token) for token in line.split('=', 1)[1].split() if token.strip().isdigit()]
        return []

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

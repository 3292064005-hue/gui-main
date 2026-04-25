from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.runtime_mode_policy import resolve_runtime_mode
from spine_ultrasound_ui.services.sdk_environment_doctor_service import SdkEnvironmentDoctorService


@dataclass(frozen=True)
class RuntimeReadinessManifestService:
    """Build a stable readiness manifest for sandbox/live verification boundaries.

    The manifest deliberately separates repository/static health from live runtime
    verification so callers cannot overstate readiness when SDK/TLS/materials are
    missing on the current host.
    """

    root_dir: Path

    SCHEMA_VERSION = "runtime.environment_readiness_manifest.v1"

    _REPOSITORY_CONTRACT_PATHS = {
        "architecture_fitness_script": Path("scripts/check_architecture_fitness.py"),
        "protocol_sync_script": Path("scripts/check_protocol_sync.py"),
        "repository_gates_script": Path("scripts/check_repository_gates.py"),
        "canonical_imports_script": Path("scripts/check_canonical_imports.py"),
        "proto_source": Path("cpp_robot_core/proto/ipc_messages.proto"),
        "python_pb2": Path("spine_ultrasound_ui/services/ipc_messages_pb2.py"),
        "cpp_wire_header": Path("cpp_robot_core/include/ipc_messages.pb.h"),
        "cpp_wire_source": Path("cpp_robot_core/src/ipc_messages.pb.cpp"),
    }

    def build(
        self,
        *,
        config: RuntimeConfig | None = None,
        surface: str = "desktop",
        explicit_mode: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        runtime_config = config or RuntimeConfig()
        env_map = dict(env) if env is not None else None
        doctor = SdkEnvironmentDoctorService(self.root_dir).inspect(runtime_config)
        profile_snapshot = DeploymentProfileService(env_map).build_snapshot(runtime_config)
        mode_decision = resolve_runtime_mode(
            explicit_mode=explicit_mode,
            surface=surface,
            config=runtime_config,
            env=env_map,
        )
        repository_contract = self._repository_contract_snapshot()
        static_ready = bool(repository_contract["ready"])
        blockers = list(doctor.get("blockers", []))
        warnings = list(doctor.get("warnings", []))
        doctor_state = str(doctor.get("summary_state", "unknown"))
        live_runtime_ready = bool(doctor_state == "ready")
        sandbox_validation_possible = bool(static_ready)
        if not static_ready:
            verification_boundary = "repository_contract_blocked"
        elif live_runtime_ready:
            verification_boundary = "live_runtime_unverified"
        else:
            verification_boundary = "environment_blocked"
        verification = {
            "static_contract_ready": static_ready,
            "sandbox_validation_possible": sandbox_validation_possible,
            "live_runtime_verified": False,
            "live_runtime_ready": live_runtime_ready,
            "verification_boundary": verification_boundary,
            "evidence_tier": (
                "static_and_sandbox" if static_ready else "blocked"
            ),
        }
        if not static_ready:
            summary_state = "blocked"
        elif live_runtime_ready:
            summary_state = "ready"
        else:
            summary_state = "warning"
        summary_label = {
            "ready": "运行资产已具备，仍需真实环境验证",
            "warning": "仓库/沙箱可验证，但当前 live 环境仍阻塞",
            "blocked": "当前环境阻塞主线验证",
        }[summary_state]
        detail = {
            "ready": "仓库静态门禁、模式决策与环境依赖均已满足；但是否真实控机成功仍需 HIL/实机证据。",
            "warning": "仓库静态契约与沙箱验证可继续，但当前环境医生仍报告 live 运行阻塞项，因此不得表述为真实环境已跑通。",
            "blocked": "当前环境缺少关键仓库契约或基础依赖，无法进入主线验证。",
        }[summary_state]
        return {
            "schema_version": self.SCHEMA_VERSION,
            "summary_state": summary_state,
            "summary_label": summary_label,
            "detail": detail,
            "surface": surface,
            "deployment_profile": profile_snapshot,
            "runtime_mode_decision": mode_decision.to_dict(),
            "verification": verification,
            "repository_contract": repository_contract,
            "doctor_snapshot": doctor,
            "blockers": blockers,
            "warnings": warnings,
            "host_requirements": {
                "requires_live_sdk": bool(mode_decision.requires_live_sdk),
                "requires_hil_gate": bool(profile_snapshot.get("requires_hil_gate", False)),
                "preferred_link": runtime_config.preferred_link,
                "remote_ip": runtime_config.remote_ip,
                "local_ip": runtime_config.local_ip,
                "rt_host_bootstrap": {
                    "env_policy_keys": [
                        "SPINE_RT_SCHED_POLICY",
                        "SPINE_RT_SCHED_PRIORITY",
                        "SPINE_RT_CPU_SET",
                        "SPINE_RT_FIXED_HOST_ID",
                        "SPINE_RT_REQUIRE_SCHEDULER",
                        "SPINE_RT_REQUIRE_AFFINITY",
                        "SPINE_RT_REQUIRE_MEMORY_LOCK",
                        "SPINE_RT_REQUIRE_FIXED_HOST_ID",
                    ],
                    "systemd_unit": "configs/systemd/spine-cpp-core.service",
                    "contract_matrix": "configs/runtime/rt_host_profiles.json",
                    "contract_label_env": "SPINE_RT_HOST_CONTRACT_LABEL",
                },
            },
        }

    def _repository_contract_snapshot(self) -> dict[str, Any]:
        checks = {
            name: (self.root_dir / rel_path).exists()
            for name, rel_path in self._REPOSITORY_CONTRACT_PATHS.items()
        }
        missing = [name for name, ok in checks.items() if not ok]
        return {
            "ready": not missing,
            "checks": checks,
            "missing": missing,
        }

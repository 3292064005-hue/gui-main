# P2 Acceptance Checklist

## P2-1 Session / Postprocess / Evidence stage 化
- [x] `PostprocessService` 拥有显式 stage registry
- [x] 生成 `postprocess_stage_manifest` 工件
- [x] `SessionFinalizeService` 生成 `session_intelligence_manifest` 工件
- [x] manifest 中包含输入/输出、retryability、performance budget、owner domain

## P2-2 Canonical module registry
- [x] 旧 shim 文件已退役
- [x] `docs/CANONICAL_MODULE_REGISTRY.md` 已声明 canonical 路径
- [x] `scripts/check_canonical_imports.py` 能阻止旧导入回流

## P2-3 Repository hard gates
- [x] `.github/CODEOWNERS` 已加入仓库
- [x] workflow 中具备稳定 job 名称，供 protected branch 作为 required checks
- [x] `scripts/check_repository_gates.py` 能校验 CODEOWNERS 与 workflow jobs

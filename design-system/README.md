# K-CIA Design System

이 폴더는 `K-CIA` 구현 레포가 직접 소비하는 디자인 시스템 산출물입니다.

현재 source of truth:

- `brand_profile.json`
- `system_spec.md`
- `token_schema.json`
- `component_inventory.json`
- `system_ontology.json`

생성 워크플로:

1. 하네스 워크스페이스 수정: `.design-ontology/brand_profile.json`
2. KB 기반 재생성:

```bash
cd <design-ontology-harness-repo>
uv run design-ontology run-project --project-dir <implementation-repo>/.design-ontology
```

3. 생성 결과 동기화:

- `.design-ontology/build/system/blueprint/system_spec.md` -> `design-system/system_spec.md`
- `.design-ontology/build/system/blueprint/token_schema.json` -> `design-system/token_schema.json`
- `.design-ontology/build/system/blueprint/component_inventory.json` -> `design-system/component_inventory.json`
- `.design-ontology/build/system/blueprint/system_ontology.json` -> `design-system/system_ontology.json`

에이전트 사용:

- Claude Code: `.claude/skills/design-system-*`, `.claude/agents/*`
- Codex: `plugins/design-system-harness/*`, `.agents/plugins/marketplace.json`

실제 UI 작업 전에는 항상 `system_spec.md`를 먼저 읽고, 토큰/컴포넌트 결정은 `token_schema.json`과 `component_inventory.json`을 기준으로 맞추는 것을 권장합니다.

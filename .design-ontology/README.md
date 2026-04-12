# K-CIA Lite

This folder is a self-contained harness project built on top of `design-ontology-harness`.

## Files

- `brand_profile.json`: your system identity and product context
- `seeds/seed_urls.txt`: curated reference entry points
- `project_manifest.json`: project metadata
- `agent_brief.md`: instructions for human or agent collaborators
- `build/`: generated outputs

## How To Run

```bash
uv run design-ontology run-project --project-dir /Users/sungwoon/ai-projects/K-CIA/.design-ontology
```

## Recommended Flow

1. Fill in `brand_profile.json`
2. Set or override the KB path if needed
3. Run the project
4. Review `build/system/blueprint/system_spec.md`

# K-CIA Intelligence System Spec

## 1. Positioning

- **Brand**: K-CIA Lite
- **Product**: 성수동 하이퍼로컬 상권 분석을 지도, 지표, 대화형 인사이트로 연결하는 AI 플랫폼
- **Audience**: 성수동에 매장을 열거나 운영 전략을 검토하는 예비 창업자, 입지 판단과 상권 변화를 빠르게 읽어야 하는 상권 컨설턴트와 운영자, 지역 흐름을 근거 기반으로 파악하려는 로컬 비즈니스 의사결정자
- **Platforms**: web
- **Accessibility floor**: WCAG 2.2 AA

## 2. Identity Guardrails

- **Brand keywords**: analytical, editorial, trustworthy, decisive
- **Anti-keywords**: generic, noisy, gamified, ambiguous
- **Tone of voice**: clear, evidence-led, calm, confident
- **Visual direction**: cartographic depth, editorial dashboard hierarchy, intelligence briefing panels, measured navy-ochre accents
- **Interaction direction**: progressive disclosure, contextual overlays, confident comparison, low-noise motion

## 3. Design Principles

- **Analytical**: `analytical`를 시각적 선택과 인터랙션 선택의 기본 기준으로 삼습니다.
- **Editorial Hierarchy**: 타이포그래피와 여백으로 위계를 만들고, 장식은 의미를 돕는 범위에서만 사용합니다.
- **Trust Through Consistency**: 예측 가능한 인터랙션과 안정적인 시각 언어로 신뢰를 쌓습니다.
- **Decisive**: `decisive`를 시각적 선택과 인터랙션 선택의 기본 기준으로 삼습니다.

## 4. Foundation Priorities

- **Content design and microcopy rules** (high): signal 20
- **Icon family and stroke policy** (high): signal 10
- **Color tokens and semantic color policy** (high): signal 8
- **Accessibility rules and contrast baseline** (medium): signal 7
- **Grid, container, and page rhythm** (medium): signal 3

## 5. Token Strategy

- **Layering**: core -> semantic -> component
- **Core categories**: color, spacing, radius, typography, motion, elevation
- **Semantic categories**: surface, text, border, focus, feedback
- **Component categories**: button, input, navigation, overlay, editor
- **Typography families**: display, text, mono
- **Spacing scale**: 0, 2, 4, 8, 12, 16, 24, 32, 48, 64, 96

## 6. Color Reference

- **Source**: REFERENCE X Vol.1 - Color Reference (/Users/sungwoon/project/color/docs/color-reference.md)
- **Selection mode**: brand-guided
- **Preferred families**: Deep Reds, Standard Oranges, Pastel Oranges
- **Palette strategy**: temperature=warm, contrast=balanced, diversity=balanced, surface_style=tinted
- **Active palette**: signature-1
- **Active roles**:
  - `primary` -> Navy Blue #000080 / Deep Blues
  - `accent` -> Ochre #CC7722 / Standard Oranges
  - `surface_tint` -> Apricot #FFB27F / Natural Oranges
- **Selected colors**:
  - Navy Blue #000080 / Deep Blues / 저명도, 중채도, 차가운 온도감이 강한 블루 계열 / 신뢰, 권위, 집중, 전문성, 절제된 우아함
  - Ochre #CC7722 / Standard Oranges / 중명도, 중채도, 흙기 섞인 따뜻한 오렌지 / 안정감, 내추럴, 신뢰감, 지속성
  - Apricot #FFB27F / Natural Oranges / 밝은 명도, 낮은 채도, 살짝 핑크빛이 도는 부드러운 오렌지 / 따뜻함, 부드러움, 친근함, 여유, 자연스러움
- **Palette candidates**:
  - signature-1 (Signature): primary=Navy Blue, accent=Ochre, surface_tint=Apricot / Navy Blue matches brand tone keywords.; Ochre is inside preferred families.
  - soft-spread-2 (Soft Spread): primary=Ochre, accent=Amber, surface_tint=Peach Puff / Ochre is inside preferred families.; Amber matches brand tone keywords.
- **Notes**: intelligence dashboard tone first, avoid beauty-like pastel dominance
- **Application rule**: 레퍼런스 컬러는 semantic token으로 번역해서 사용하고, 접근성과 theme 호환성을 우선합니다.

## 7. Component Strategy

- **Product primitives**: geo intelligence shell, map filter controls, metric briefing cards, quarter comparison panels, risk gauges and decomposition bars, ai consultant chat, evidence tables
- **Required families**: button, feedback, input, navigation, overlay

- **button**: primary-button, secondary-button, ghost-button, icon-button, cta-button
- **feedback**: inline-alert, empty-state, toast
- **input**: text-field, search-field, segmented-control
- **navigation**: mobile-topbar, mobile-tab-bar, back-button, section-tabs
- **overlay**: bottom-sheet, modal-dialog

## 8. Implementation Guardrails

- 기존 핵심 화면, 진입점, 작업 흐름은 명시적 승인 없이 제거하거나 숨기지 않음
- 전면 셸 리라이트보다 토큰 -> primitive -> feature surface 순서의 점진적 롤아웃을 우선
- 새 시각 규칙은 지원 대상 테마와 breakpoint 전체에서 먼저 검증
- 기존 데이터 밀도와 업무 완료 경로를 유지한 상태에서 시각 품질을 높이는 방향을 우선
- 기능 위치 변경, 정보 구조 변경, 패널 제거는 별도의 migration plan이 있을 때만 수행

## 9. Reference Absorption Rule

- Analysed live reference sources: 22
- Rule: copy visuals from no single source; absorb patterns only when they reinforce brand keywords and avoid anti-keywords.
- Use references to validate structure, accessibility, token discipline, and documentation quality.

## 10. Ontology Targets

- **content**: 20
- **design_system**: 19
- **iconography**: 10
- **color**: 8
- **accessibility**: 7
- **pattern**: 6
- **layout**: 3
- **brand**: 3

## 11. Profile Validation

- No validation issues.

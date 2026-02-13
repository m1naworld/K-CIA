# K-CIA Lite 컬러 시스템 분석 보고서

> 작성일: 2026-02-07

---

## 1. 프로그램 배경 설명

### 개요
**K-CIA Lite**는 서울 성수동 지역의 하이퍼로컬 상권 분석 AI 플랫폼입니다.

- **한 줄 정의**: "성수동의 어제와 오늘을 3D 지도와 대화로 읽어주는 AI 컨설턴트"
- **핵심 기능**: 
  - 3D 헥사곤 맵 (Deck.gl + H3 그리드)
  - AI 챗봇 (LangGraph 멀티에이전트)
  - 공공데이터 기반 인사이트
- **타겟 유저**: 예비 창업자, 브랜드/마케팅 실무자, 상권 컨설턴트, 임대/투자자

### 기술 스택
| 영역 | 기술 |
|------|------|
| Frontend | Next.js 14, Deck.gl, TailwindCSS, shadcn/ui, Recharts |
| State | Zustand |
| UI Theme | **Dark Mode 전용** (맵 시각화 최적화) |

---

## 2. 컬러 시스템 구조

### 2.1 Theme 설정 (CSS Variables)

**파일**: `globals.css` + `tailwind.config.ts`

shadcn/ui 기반으로 CSS 변수를 사용하지만, **실제 앱은 Dark Mode만 사용** 중입니다.

#### Light Theme (`:root`) — 사용 안 함
```css
--background: 0 0% 100%           /* 흰색 */
--foreground: 0 0% 3.9%           /* 거의 검정 */
--primary: 0 0% 9%                /* 어두운 회색 */
--destructive: 0 84.2% 60.2%      /* 빨강 */
```

#### Dark Theme (`.dark`) — 앱 전체 적용
```css
--background: 0 0% 3.9%           /* 거의 검정 (#0a0a0a) */
--foreground: 0 0% 98%            /* 거의 흰색 */
--primary: 0 0% 98%               /* 흰색 */
--secondary: 0 0% 14.9%           /* 어두운 회색 */
--muted: 0 0% 14.9%               /* 어두운 회색 */
--muted-foreground: 0 0% 63.9%    /* 중간 회색 */
--destructive: 0 62.8% 30.6%      /* 어두운 빨강 */
--border: 0 0% 14.9%              /* 어두운 회색 */
```

#### Chart Colors (Dark)
```css
--chart-1: 220 70% 50%    /* 파랑 */
--chart-2: 160 60% 45%    /* 초록 */
--chart-3: 30 80% 55%     /* 주황 */
--chart-4: 280 65% 60%    /* 보라 */
--chart-5: 340 75% 55%    /* 핑크 */
```

---

## 3. 컴포넌트별 컬러 배색 상세

### 3.1 HexMap (3D 지도 컴포넌트)

**파일**: `components/map/HexMap.tsx`

#### 배경
| 요소 | 컬러 | 값 |
|------|------|-----|
| 맵 배경 | Mapbox Dark | `mapbox://styles/mapbox/dark-v11` |
| 로딩 화면 | gray-900 | `#111827` |
| 컨트롤 패널 | gray-900/80 | `rgba(17,24,39,0.8)` |

#### 행정동 색상 (하드코딩)
| 행정동 | 컬러 | Hex |
|--------|------|-----|
| 성수1가1동 | Indigo | `#6366f1` |
| 성수1가2동 | Violet | `#8b5cf6` |
| 성수2가1동 | Cyan | `#06b6d4` |
| 성수2가3동 | Teal | `#14b8a6` |
| 기본 | Gray | `#888` |

#### 상권 유형 색상 (하드코딩)
| 상권 유형 | 컬러 | Hex |
|-----------|------|-----|
| 발달상권 | Blue | `#60a5fa` (blue-400) |
| 골목상권 | Green | `#4ade80` (green-400) |
| 전통시장 | Orange | `#fb923c` (orange-400) |

#### 헥사곤 색상 스케일 (동적 계산)

**QoQ 매출 증감 모드** (-30% ~ +30%):
```
감소(빨강) ─────────────────────────────> 증가(초록)
#c8323c → #ff6428 → #ffb43c → #afd228 → #28a050
```
- 빨강 영역: `rgb(200-255, 50-100, 30-40)`
- 주황 영역: `rgb(255, 100-180, 40-60)`
- 노랑 영역: `rgb(255-175, 180-210, 60-40)`
- 초록 영역: `rgb(175-40, 210-170, 40-80)`

**팝업 모드** (타겟 유동인구 비율 0~50%):
```
낮음(파랑) ─────────────────────────────> 높음(마젠타)
#3c82c8 → #8040d0 → #f032ff
```
- R: 60 → 240
- G: 130 → 50
- B: 200 → 255

#### 툴팁 & UI
| 요소 | Tailwind Class |
|------|----------------|
| 툴팁 배경 | `bg-gray-900/90 border-white/10` |
| 제목 텍스트 | `text-white` |
| 보조 텍스트 | `text-white/50`, `text-white/60`, `text-white/70` |
| 강조 (매출) | `text-amber-300` |
| 강조 (팝업) | `text-violet-300` |
| 상권명 (realName) | `text-emerald-400` |

#### 버튼 상태
| 상태 | 컬러 |
|------|------|
| 유동인구/매출 선택됨 | `bg-blue-600` |
| 행정동 선택됨 | `bg-indigo-600` |
| 상권 선택됨 | `bg-emerald-600` |
| 비활성 | `text-white/60 hover:bg-white/10` |

---

### 3.2 Sidebar (사이드바)

**파일**: `components/sidebar/Sidebar.tsx`

#### 기본 구조
| 요소 | Tailwind Class |
|------|----------------|
| 컨테이너 | `bg-gray-950 border-white/10` |
| 헤더 | `border-b border-white/10` |
| 제목 | `text-white` |
| 부제목 | `text-white/50` |

#### 배지 (Badge) 색상
| 용도 | 컬러 조합 |
|------|-----------|
| 기준 분기 | `border-blue-500/50 bg-blue-500/10 text-blue-300` |
| 영역 태그 | `bg-white/5 text-white/70` |

#### 성장률 표시
| 상태 | 컬러 |
|------|------|
| 증가 | `text-emerald-400` |
| 감소 | `text-red-400` |

#### 추천 등급 배지
| 등급 | 배경/텍스트 |
|------|-------------|
| S | `bg-emerald-500/20 text-emerald-400` |
| A | `bg-blue-500/20 text-blue-400` |
| B | `bg-amber-500/20 text-amber-400` |
| C | `bg-orange-500/20 text-orange-400` |
| D | `bg-red-500/20 text-red-400` |

---

### 3.3 MetricCard (지표 카드)

**파일**: `components/sidebar/MetricCard.tsx`

#### 카드 Variant
| Variant | Border 색상 |
|---------|-------------|
| default | `border-white/10` |
| warning | `border-amber-500/30` |
| danger | `border-red-500/30` |

#### 공통 스타일
| 요소 | 컬러 |
|------|------|
| 카드 배경 | `bg-gray-900/60 backdrop-blur-sm` |
| 제목 | `text-white/80` |
| 레이블 | `text-white/50`, `text-white/40` |
| 강조값 (highlight) | `text-amber-300` |
| 일반값 | `text-white` |

#### 차트 색상
| 차트 | Hex |
|------|-----|
| 유동인구 | `#60a5fa` (blue-400) |
| 매출 | `#fbbf24` (amber-400) |

#### 바 분포
| 요소 | 컬러 |
|------|------|
| 바 기본 | `bg-blue-500/60` |
| 바 호버 | `bg-blue-400` |
| 툴팁 | `bg-gray-800` |

#### 경고 목록
| 요소 | 컬러 |
|------|------|
| 경고 아이콘/텍스트 | `text-amber-300/90` |

---

### 3.4 FilterPanel (필터 패널)

**파일**: `components/filters/FilterPanel.tsx`

| 요소 | 컬러 |
|------|------|
| 패널 배경 | `bg-gray-900` |
| 제목 | `text-white` |
| 레이블 | `text-white/60` |
| 배지 | `text-white/50` |
| Select 트리거 | `border-white/20 bg-gray-800 text-white` |
| Select 드롭다운 | `bg-gray-800 text-white` |
| 구분선 | `border-white/10` |

---

### 3.5 ChatPanel (챗봇)

**파일**: `components/chat/ChatPanel.tsx`, `ChatMessage.tsx`, `ChatInput.tsx`

#### 패널
| 요소 | 컬러 |
|------|------|
| 배경 | `bg-gray-950 border-white/10` |
| 플로팅 버튼 | `bg-blue-600 hover:bg-blue-500` |
| 아이콘 | `text-blue-400` |
| 헤더 버튼 | `text-white/50 hover:bg-white/10 hover:text-white` |

#### 메시지
| 메시지 유형 | 컬러 |
|-------------|------|
| 유저 메시지 | `bg-blue-600 text-white` |
| AI 메시지 | `bg-gray-800/60 text-white/90` |
| 에러 메시지 | `border-red-500/30 bg-red-500/10 text-red-400` |
| 로딩 텍스트 | `text-white/60` |
| 기준일 배지 | `border-white/20 bg-gray-800/50 text-white/50` |

#### 입력창
| 요소 | 컬러 |
|------|------|
| 배경 | `bg-gray-800` |
| 텍스트 | `text-white` |
| Placeholder | `placeholder-white/40` |
| Focus ring | `focus:ring-blue-500` |
| 전송 버튼 | `text-blue-400 hover:bg-blue-500/10` |
| 취소 버튼 | `text-red-400 hover:bg-red-500/10` |

---

### 3.6 Insight Cards (인사이트 카드들)

**파일**: `components/chat/insight/*.tsx`

| 카드 | Border | Title | Accent |
|------|--------|-------|--------|
| **EvidenceCard** | `border-emerald-500/30` | `text-emerald-400` | `bg-emerald-500/20 text-emerald-400` |
| **RisksCard** | `border-amber-500/30` | `text-amber-400` | High: `text-red-400`, Medium: `text-amber-400`, Low: `text-yellow-400` |
| **RecommendationsCard** | `border-blue-500/30` | `text-blue-400` | `bg-blue-500 text-white` |
| **ActionItemsCard** | `border-emerald-500/30` | `text-emerald-400` | `bg-emerald-500/20 text-emerald-400` |
| **ChecklistCard** | `border-violet-500/30` | `text-violet-400` | `text-violet-400` |
| **SqlCard** | `border-cyan-500/30` | `text-cyan-400` | Code: `text-cyan-300/80` |
| **InsightsCard** | `border-amber-500/30 bg-amber-500/10` | `text-amber-400` | `text-amber-400` |
| **DataTableCard** | `border-blue-500/30 bg-blue-500/10` | `text-blue-400` | `text-blue-400` |

공통 배경: `bg-gray-900/60`

---

### 3.7 추가 컴포넌트

#### DemoCard (인구통계)
| 요소 | 컬러 |
|------|------|
| 남성 | `text-blue-400`, `bg-blue-500` |
| 여성 | `text-pink-400`, `bg-pink-500` |
| 피크 연령대 | `bg-amber-500/80 text-amber-300` |
| 일반 연령대 | `bg-violet-500/50` |

#### TimeSlotCard (시간대)
| 요소 | 컬러 |
|------|------|
| 배지 | `border-violet-500/50 bg-violet-500/10 text-violet-300` |
| 피크 바 | `bg-amber-500/70` |
| 일반 바 | `bg-violet-500/40` |

#### FacilityCard (집객시설)
- MetricCard 기본 스타일 사용

---

## 4. 컬러 팔레트 요약

### 주요 색상 (Semantic Usage)

| 용도 | 색상 계열 | Tailwind Class | Hex 예시 |
|------|-----------|----------------|----------|
| **Primary Action** | Blue | `blue-400`~`blue-600` | `#60a5fa`, `#2563eb` |
| **Positive/Success** | Emerald/Green | `emerald-400` | `#34d399` |
| **Warning/Highlight** | Amber/Yellow | `amber-300`~`amber-500` | `#fcd34d`, `#f59e0b` |
| **Negative/Error** | Red | `red-400`~`red-500` | `#f87171` |
| **Special Mode** | Violet/Purple | `violet-300`~`violet-500` | `#c4b5fd`, `#8b5cf6` |
| **Data/SQL** | Cyan | `cyan-400` | `#22d3ee` |
| **Female Demo** | Pink | `pink-400` | `#f472b6` |

### 배경 (Grayscale)

| 용도 | Tailwind Class | Hex |
|------|----------------|-----|
| 가장 어두운 배경 | `gray-950` | `#030712` |
| 컴포넌트 배경 | `gray-900` | `#111827` |
| 카드/입력 배경 | `gray-800` | `#1f2937` |
| 반투명 오버레이 | `gray-900/60`, `gray-900/80` | - |

### 텍스트 (White Opacity)

| 용도 | Opacity |
|------|---------|
| 제목/강조 | `text-white` (100%) |
| 본문 | `text-white/90`, `text-white/80` |
| 보조 정보 | `text-white/70`, `text-white/60` |
| 레이블/힌트 | `text-white/50`, `text-white/40` |
| 비활성 | `text-white/30` |

### Border

| 용도 | Opacity |
|------|---------|
| 기본 테두리 | `border-white/10` |
| 입력 필드 | `border-white/20` |
| 강조 테두리 | `border-{color}-500/30` ~ `border-{color}-500/50` |

---

## 5. 문제점 및 개선 제안

### 발견된 이슈

1. **하드코딩된 색상 다수**
   - HexMap의 행정동/상권 색상
   - 차트 색상 (`#60a5fa`, `#fbbf24`)
   - RGB 스케일 계산

2. **중앙화된 색상 정의 부재**
   - 색상이 여러 파일에 분산
   - 일관성 유지 어려움

3. **shadcn/ui 테마 변수 미활용**
   - CSS 변수 정의는 있지만 대부분 Tailwind 클래스 직접 사용
   - `chart-1`~`chart-5` 변수 거의 사용 안 함

### 권장 개선안

1. **색상 상수 파일 생성**: `/src/lib/colors.ts`
2. **Tailwind 테마 확장**: 도메인별 커스텀 색상 추가
3. **RGB 스케일 함수 분리**: 시각화 전용 유틸리티로 추출

---

## 6. 파일 참조

| 파일 | 설명 |
|------|------|
| `frontend/src/app/globals.css` | CSS 변수 정의 (Light/Dark) |
| `frontend/tailwind.config.ts` | Tailwind 테마 설정 |
| `frontend/src/components/map/HexMap.tsx` | 3D 맵 시각화 |
| `frontend/src/components/sidebar/Sidebar.tsx` | 사이드바 메인 |
| `frontend/src/components/sidebar/MetricCard.tsx` | 지표 카드 |
| `frontend/src/components/filters/FilterPanel.tsx` | 필터 패널 |
| `frontend/src/components/chat/ChatPanel.tsx` | 챗봇 패널 |
| `frontend/src/components/chat/ChatMessage.tsx` | 챗 메시지 |
| `frontend/src/components/chat/insight/*.tsx` | 인사이트 카드들 |

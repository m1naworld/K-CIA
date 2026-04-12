import dynamic from "next/dynamic";
import FilterPanel from "@/components/filters/FilterPanel";
import { Badge } from "@/components/ui/badge";

const HexMap = dynamic(() => import("@/components/map/HexMap"), {
  ssr: false,
  loading: () => (
    <div className="intel-shell intel-grid flex h-screen flex-1 items-center justify-center bg-background text-foreground">
      <div className="intel-panel rounded-[1.75rem] px-6 py-5 text-center">
        <div className="intel-kicker">Geo Intelligence Canvas</div>
        <p className="mt-3 text-base font-medium">지도를 불러오는 중입니다.</p>
        <p className="mt-1 text-sm text-muted-foreground">
          상권 흐름과 브리핑 패널을 연결할 준비를 하고 있어요.
        </p>
      </div>
    </div>
  ),
});

const Sidebar = dynamic(() => import("@/components/sidebar/Sidebar"), {
  ssr: false,
});

const ChatPanel = dynamic(() => import("@/components/chat/ChatPanel"), {
  ssr: false,
});

export default function Home() {
  return (
    <div className="intel-shell intel-grid flex h-screen w-screen overflow-hidden">
      <FilterPanel />
      <div className="relative min-w-0 flex-1 overflow-hidden">
        <div className="pointer-events-none absolute inset-x-4 top-4 z-20 flex flex-col gap-3 lg:inset-x-6 lg:top-6">
          <div className="flex items-start justify-between gap-4">
            <div className="intel-panel pointer-events-auto max-w-2xl rounded-[1.75rem] px-5 py-4 lg:px-6">
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  variant="outline"
                  className="intel-badge-primary rounded-full px-3 py-1 text-[10px] font-medium uppercase tracking-[0.18em]"
                >
                  K-CIA Intelligence System
                </Badge>
                <Badge
                  variant="outline"
                  className="intel-badge-accent rounded-full px-3 py-1 text-[10px] font-medium uppercase tracking-[0.18em]"
                >
                  Seongsu Hyperlocal Briefing
                </Badge>
              </div>
              <h1 className="intel-title mt-4 text-xl font-semibold text-foreground md:text-2xl">
                상권의 흐름을 지도, 지표, 대화형 브리핑으로 읽는 인텔리전스 캔버스
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                업종과 분기를 바꾸면 지도, 비교 패널, AI 컨설턴트가 같은 컨텍스트로 함께
                업데이트됩니다. 감이 아니라 근거로 판단하는 입지 분석 워크플로를 목표로 합니다.
              </p>
            </div>

            <div className="hidden xl:grid xl:w-[22rem] xl:grid-cols-3 xl:gap-3">
              {[
                ["Map", "3D 헥사곤", "현장 맥락"],
                ["Brief", "리스크 분해", "근거 우선"],
                ["AI", "대화형 조언", "의사결정 가속"],
              ].map(([label, title, caption]) => (
                <div key={label} className="intel-panel pointer-events-auto rounded-[1.5rem] px-4 py-4">
                  <p className="intel-kicker">{label}</p>
                  <p className="mt-2 text-sm font-semibold text-foreground">{title}</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">{caption}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
        <HexMap />
      </div>
      <Sidebar />
      <ChatPanel />
    </div>
  );
}

import dynamic from "next/dynamic";
import FilterPanel from "@/components/filters/FilterPanel";

const HexMap = dynamic(() => import("@/components/map/HexMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-screen flex-1 items-center justify-center bg-gray-900 text-white">
      <p>지도 로딩 중...</p>
    </div>
  ),
});

const Sidebar = dynamic(() => import("@/components/sidebar/Sidebar"), {
  ssr: false,
});

const ChatPanel = dynamic(() => import("@/components/chat/ChatPanel"), {
  ssr: false,
});

const StoryMode = dynamic(() => import("@/components/content/StoryMode"), {
  ssr: false,
});

const PortfolioPanel = dynamic(
  () => import("@/components/portfolio/PortfolioPanel"),
  { ssr: false }
);

export default function Home() {
  return (
    <div className="flex h-screen w-screen">
      <FilterPanel />
      <div className="relative flex-1">
        <HexMap />
        {/* Story Mode floating panel */}
        <div className="absolute bottom-4 left-1/2 z-20 w-96 -translate-x-1/2">
          <StoryMode />
        </div>
      </div>
      <Sidebar />
      <PortfolioPanel />
      <ChatPanel />
    </div>
  );
}

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

export default function Home() {
  return (
    <div className="flex h-screen w-screen">
      <FilterPanel />
      <div className="relative flex-1">
        <HexMap />
      </div>
      <Sidebar />
      <ChatPanel />
    </div>
  );
}

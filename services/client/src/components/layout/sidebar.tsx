'use client';

import { useSidebarStore, getSidebarWidth } from '@/stores/sidebar-store';
import {
  History,
  ArrowLeft,
  PanelLeftClose,
  Maximize2,
} from 'lucide-react';

interface SidebarProps {
  children?: React.ReactNode;
  onHistoryClick?: () => void;
  onBackClick?: () => void;
  showBackButton?: boolean;
}

export function Sidebar({
  children,
  onHistoryClick,
  onBackClick,
  showBackButton = false,
}: SidebarProps) {
  const { state, toggle, expand, collapse } = useSidebarStore();

  const isCollapsed = state === 'collapsed';
  const isExpanded = state === 'expanded';
  const width = getSidebarWidth(state);

  return (
    <aside
      className="relative bg-white h-full rounded-md p-1.5 flex flex-col transition-all duration-600 ease-in-out overflow-hidden"
      style={{
        width,
        minWidth: isCollapsed ? '100px' : '300px',
        maxWidth: isExpanded ? '1000px' : isCollapsed ? '100px' : '600px',
        flex: `0 0 ${width}`,
      }}
    >
      {/* Collapsed state - show open button */}
      {isCollapsed ? (
        <div className="flex flex-col items-center pt-4">
          <button
            onClick={() => toggle()}
            className="flex flex-col items-center justify-center bg-white w-9 h-9 border border-grey-2 rounded-sm cursor-pointer hover:bg-btn-hover"
            aria-label="사이드바 열기"
          >
            <PanelLeftClose className="w-5 h-5 text-grey-4 rotate-180" />
          </button>
        </div>
      ) : (
        <>
          {/* Sidebar header buttons */}
          <div className="flex items-center justify-between w-full h-11 mt-2.5 px-1.5">
            {/* Left button group */}
            <div className="flex items-center gap-1">
              {/* History button */}
              <button
                onClick={onHistoryClick}
                className="flex justify-center items-center bg-white w-9 h-9 rounded-pill border border-grey-2 cursor-pointer hover:bg-btn-hover"
                aria-label="히스토리"
              >
                <History className="w-5 h-5 text-grey-4" />
              </button>

              {/* Back button - conditionally shown */}
              {showBackButton && (
                <button
                  onClick={onBackClick}
                  className="flex justify-center items-center bg-white w-9 h-9 rounded-pill border border-grey-2 cursor-pointer hover:bg-btn-hover"
                  aria-label="뒤로가기"
                >
                  <ArrowLeft className="w-5 h-5 text-grey-4" />
                </button>
              )}
            </div>

            {/* Right button group */}
            <div className="flex items-center gap-1">
              {/* Expand button */}
              <button
                onClick={() => expand()}
                className="flex justify-center items-center bg-white w-9 h-9 rounded-pill border border-grey-2 cursor-pointer hover:bg-btn-hover"
                aria-label={isExpanded ? '축소' : '확장'}
              >
                <Maximize2
                  className={`w-5 h-5 text-grey-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                />
              </button>

              {/* Close button */}
              <button
                onClick={() => collapse()}
                className="flex justify-center items-center bg-white w-9 h-9 rounded-pill border border-grey-2 cursor-pointer hover:bg-btn-hover pr-2"
                aria-label="사이드바 닫기"
              >
                <PanelLeftClose className="w-5 h-5 text-grey-4" />
              </button>
            </div>
          </div>

          {/* Sidebar content */}
          <div className="flex-1 overflow-y-auto overflow-x-hidden mt-4 px-1.5 hide-scrollbar">
            {children}
          </div>
        </>
      )}
    </aside>
  );
}

'use client';

import { ReactNode } from 'react';
import { Header } from './header';
import { Sidebar } from './sidebar';
import { MobileWarning } from './mobile-warning';

interface MainLayoutProps {
  children: ReactNode;
  sidebarContent?: ReactNode;
  onHistoryClick?: () => void;
  showBackButton?: boolean;
  onBackClick?: () => void;
}

export function MainLayout({
  children,
  sidebarContent,
  onHistoryClick,
  showBackButton = false,
  onBackClick,
}: MainLayoutProps) {
  return (
    <>
      {/* Mobile warning overlay */}
      <MobileWarning />

      {/* Main container */}
      <div className="flex flex-col bg-key-1 h-screen py-1.5 px-4 box-border">
        {/* Header - now manages its own auth state */}
        <Header />

        {/* Sidebar + Chat container */}
        <div className="flex flex-row w-full flex-grow my-1 gap-4 overflow-hidden">
          {/* Sidebar */}
          <Sidebar
            onHistoryClick={onHistoryClick}
            showBackButton={showBackButton}
            onBackClick={onBackClick}
          >
            {sidebarContent}
          </Sidebar>

          {/* Main content area (Chat) */}
          <main className="bg-white h-full flex-grow min-w-[50px] p-1.5 rounded-md flex flex-col items-center">
            {children}
          </main>
        </div>
      </div>
    </>
  );
}

'use client';

import { User, FileText, Link, Building, Shield } from 'lucide-react';
import type { TabType } from './profile-modal';

interface ProfileTabsProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
}

interface TabConfig {
  id: TabType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const tabs: TabConfig[] = [
  { id: 'account', label: '계정', icon: User },
  { id: 'plan', label: '플랜', icon: FileText },
  { id: 'links', label: '링크', icon: Link },
  { id: 'company', label: '창플', icon: Building },
  { id: 'privacy', label: '개인정보 처리방침', icon: Shield },
];

export function ProfileTabs({ activeTab, setActiveTab }: ProfileTabsProps) {
  return (
    <div className="flex flex-col gap-0.5 mt-2.5 w-[190px] h-full mx-2.5 my-2.5 pt-10">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`
              flex flex-row items-center gap-2.5 h-12 px-2.5 py-3
              text-base font-light rounded-[10px]
              transition-colors
              ${isActive
                ? 'bg-btn-hover text-black'
                : 'text-grey-4 hover:bg-btn-hover'
              }
            `}
            role="tab"
            aria-selected={isActive}
          >
            <Icon
              className={`w-5 h-5 ${isActive ? 'text-black' : 'text-grey-4'}`}
            />
            <p className={`text-base font-${isActive ? '400' : '300'}`}>
              {tab.label}
            </p>
          </button>
        );
      })}
    </div>
  );
}

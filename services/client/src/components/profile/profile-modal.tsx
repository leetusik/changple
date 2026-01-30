'use client';

import { useEffect } from 'react';
import { X } from 'lucide-react';
import { ProfileTabs } from './profile-tabs';
import { TabAccount } from './tab-account';
import { TabPlan } from './tab-plan';
import { TabLinks } from './tab-links';
import { TabCompany } from './tab-company';
import { TabPrivacy } from './tab-privacy';

export type TabType = 'account' | 'plan' | 'links' | 'company' | 'privacy';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
}

export function ProfileModal({ isOpen, onClose, activeTab, setActiveTab }: ProfileModalProps) {
  // ESC key handler
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Background click handler
  const handleBackgroundClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className={`
        fixed inset-0 z-50 flex items-center justify-center
        bg-black/50
        transition-opacity duration-300 ease-in-out
        ${isOpen ? 'opacity-100' : 'opacity-0'}
      `}
      onClick={handleBackgroundClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      {/* Modal container */}
      <div
        className={`
          bg-white rounded-md shadow-2xl
          w-[750px] min-w-[750px] h-[530px]
          flex flex-col
          p-3.5
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? 'scale-100' : 'scale-95'}
        `}
      >
        {/* Close button area */}
        <div className="w-full h-9 flex justify-end pr-3.5 mt-0.5">
          <button
            onClick={onClose}
            className="flex items-center justify-center w-[30px] h-[30px]
              bg-white border border-grey-2 rounded-btn-small
              hover:bg-btn-hover transition-colors"
            aria-label="닫기"
          >
            <X className="w-2.5 h-2.5 text-black" />
          </button>
        </div>

        {/* Modal content area - two columns */}
        <div className="flex flex-row w-full flex-1 overflow-hidden">
          {/* Left column - Tabs */}
          <div className="w-[200px] h-full flex flex-col items-center border-r border-grey-2">
            <ProfileTabs activeTab={activeTab} setActiveTab={setActiveTab} />
          </div>

          {/* Right column - Content */}
          <div className="flex-1 h-full flex flex-col items-center overflow-hidden">
            <div className="w-[520px] h-full mx-2.5 my-2.5 overflow-hidden">
              {activeTab === 'account' && <TabAccount onClose={onClose} />}
              {activeTab === 'plan' && <TabPlan />}
              {activeTab === 'links' && <TabLinks />}
              {activeTab === 'company' && <TabCompany />}
              {activeTab === 'privacy' && <TabPrivacy />}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

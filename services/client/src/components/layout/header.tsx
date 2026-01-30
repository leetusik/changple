'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useAuth, getLoginUrl } from '@/hooks/use-auth';
import { useState } from 'react';
import { ProfileModal, type TabType } from '@/components/profile/profile-modal';

export function Header() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('account');

  const handleLogin = () => {
    window.location.href = getLoginUrl();
  };

  const handleOpenModal = () => {
    setActiveTab('account'); // Always open to account tab
    setShowProfileModal(true);
  };

  return (
    <header className="flex flex-row items-center h-[50px] w-full">
      {/* Logo - matching .mainLogo */}
      <Link href="/" className="cursor-pointer">
        <Image
          src="/icons/changpleHeader.svg"
          alt="창플 AI"
          width={140}
          height={32}
          className="h-auto"
          priority
        />
      </Link>

      {/* Right side - Profile/Login - matching .profileContainer */}
      <div className="flex flex-row items-center justify-end w-full h-fit">
        {isLoading ? (
          /* Loading state */
          <div className="w-[100px] h-[35px] bg-grey-1 rounded-pill animate-pulse" />
        ) : isAuthenticated && user ? (
          /* Logged in state - matching .user-profile */
          <>
            <div className="flex items-center">
              <span className="text-base leading-[0.4] text-black font-medium">
                {user.nickname}님
              </span>
              <span className="text-sm leading-[0.4] text-grey-3">
                {' '}| Pro 플랜 이용중
              </span>
            </div>
          </>
        ) : (
          /* Not logged in - matching .buttonLogin */
          <button
            onClick={handleLogin}
            className="flex flex-row items-center justify-center bg-white w-fit h-[35px]
              border border-[#E0E0E0] rounded-pill px-2.5 hover:bg-btn-hover transition-colors"
          >
            {/* Naver logo SVG */}
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 13 13" fill="none" className="w-[15px] h-[15px]">
              <path
                d="M9.00392 6.64095L4.54113 0.25H0.84375V12.1771H4.72009V5.79614L9.18282 12.1771H12.8802V0.25H9.00392V6.64095Z"
                fill="#03C75A"
              />
            </svg>
            <p className="text-[15px] leading-[0.4] text-grey-3 ml-1">
              네이버 로그인
            </p>
          </button>
        )}

        {/* 3-dot menu button - matching .buttonModal */}
        <button
          onClick={handleOpenModal}
          className="flex flex-col justify-center items-center w-9 h-9 bg-white
            rounded-pill border-none ml-3 hover:bg-btn-hover transition-colors"
          aria-label="메뉴"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="26" height="6" viewBox="0 0 26 6" fill="none" className="w-5 h-auto">
            <circle cx="3" cy="2.6875" r="2.5" fill="#323232" />
            <circle cx="13" cy="2.6875" r="2.5" fill="#323232" />
            <circle cx="23" cy="2.6875" r="2.5" fill="#323232" />
          </svg>
        </button>
      </div>

      {/* Profile Modal */}
      <ProfileModal
        isOpen={showProfileModal}
        onClose={() => setShowProfileModal(false)}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />
    </header>
  );
}

'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useAuth, useLogout, getLoginUrl } from '@/hooks/use-auth';
import { useState, useRef, useEffect } from 'react';

export function Header() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const logoutMutation = useLogout();
  const [showProfileModal, setShowProfileModal] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  const handleLogin = () => {
    window.location.href = getLoginUrl();
  };

  const handleLogout = () => {
    logoutMutation.mutate();
    setShowProfileModal(false);
  };

  // Close modal when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        setShowProfileModal(false);
      }
    };

    if (showProfileModal) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showProfileModal]);

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
        <div className="relative" ref={modalRef}>
          <button
            onClick={() => setShowProfileModal(!showProfileModal)}
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

          {/* Profile modal */}
          {showProfileModal && (
            <div className="absolute right-0 top-[44px] bg-white rounded-md shadow-lg border border-grey-2 p-4 min-w-[200px] z-50">
              {isAuthenticated && user ? (
                <>
                  {/* Profile info */}
                  <div className="flex items-center gap-3 mb-4 pb-4 border-b border-grey-2">
                    <Image
                      src={user.profile_image || '/icons/profileDefault.svg'}
                      alt={user.nickname}
                      width={48}
                      height={48}
                      className="rounded-full"
                    />
                    <div>
                      <p className="font-medium text-black">{user.nickname}</p>
                      <p className="text-sm text-grey-4">{user.email}</p>
                    </div>
                  </div>

                  {/* Logout button */}
                  <button
                    onClick={handleLogout}
                    disabled={logoutMutation.isPending}
                    className="w-full py-2 px-4 text-sm text-grey-5 hover:bg-btn-hover
                      rounded-pill border border-grey-3 transition-colors disabled:opacity-50"
                  >
                    {logoutMutation.isPending ? '로그아웃 중...' : '로그아웃'}
                  </button>

                  {/* Footer */}
                  <p className="mt-4 pt-4 text-xs text-grey-3 text-center border-t border-grey-2">
                    Developed by Armori
                  </p>
                </>
              ) : (
                <>
                  <p className="text-sm text-grey-4 mb-3">로그인이 필요합니다</p>
                  <button
                    onClick={handleLogin}
                    className="w-full py-2 px-4 text-sm text-white bg-blue-2 hover:bg-blue-3
                      rounded-pill transition-colors"
                  >
                    네이버 로그인
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

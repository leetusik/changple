'use client';

import Link from 'next/link';
import Image from 'next/image';
import { User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth, useLogout, getLoginUrl } from '@/hooks/use-auth';
import { useState } from 'react';

export function Header() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const logoutMutation = useLogout();
  const [showProfileMenu, setShowProfileMenu] = useState(false);

  const handleLogin = () => {
    // Redirect to Naver OAuth
    window.location.href = getLoginUrl();
  };

  const handleLogout = () => {
    logoutMutation.mutate();
    setShowProfileMenu(false);
  };

  return (
    <header className="flex flex-row items-center h-[50px] w-full">
      {/* Logo */}
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

      {/* Right side - Profile/Login */}
      <div className="flex flex-row items-center justify-end w-full h-fit">
        {isLoading ? (
          /* Loading state */
          <div className="w-[80px] h-[35px] bg-grey-1 rounded-pill animate-pulse" />
        ) : isAuthenticated && user ? (
          /* Logged in state */
          <div className="relative">
            <button
              onClick={() => setShowProfileMenu(!showProfileMenu)}
              className="flex flex-row items-center justify-center bg-white h-[35px] rounded-pill border-none px-2.5 hover:bg-btn-hover"
            >
              {user.profile_image ? (
                <Image
                  src={user.profile_image}
                  alt={user.nickname}
                  width={24}
                  height={24}
                  className="rounded-full"
                />
              ) : (
                <Image
                  src="/icons/profileDefault.svg"
                  alt="Profile"
                  width={24}
                  height={24}
                />
              )}
              <span className="text-[16px] text-black font-medium ml-1.5">
                {user.nickname}
              </span>
            </button>

            {/* Profile dropdown menu */}
            {showProfileMenu && (
              <div className="absolute right-0 top-[40px] bg-white rounded-md shadow-lg border border-grey-2 py-1 min-w-[120px] z-50">
                <button
                  onClick={handleLogout}
                  disabled={logoutMutation.isPending}
                  className="w-full px-4 py-2 text-left text-sm text-grey-5 hover:bg-btn-hover disabled:opacity-50"
                >
                  {logoutMutation.isPending ? '로그아웃 중...' : '로그아웃'}
                </button>
              </div>
            )}
          </div>
        ) : (
          /* Not logged in state */
          <Button
            variant="ghost"
            onClick={handleLogin}
            className="flex flex-row items-center justify-center bg-white h-[35px] rounded-pill border-none px-2.5 hover:bg-btn-hover"
          >
            <User className="w-[15px] h-[15px] text-grey-3" />
            <span className="text-[15px] text-grey-3 ml-1">로그인</span>
          </Button>
        )}
      </div>
    </header>
  );
}

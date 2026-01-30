'use client';

import Image from 'next/image';
import { useAuth, useLogout } from '@/hooks/use-auth';

interface TabAccountProps {
  onClose: () => void;
}

export function TabAccount({ onClose }: TabAccountProps) {
  const { user } = useAuth();
  const logoutMutation = useLogout();

  if (!user) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-grey-4">로그인이 필요합니다</p>
      </div>
    );
  }

  const handleLogout = () => {
    logoutMutation.mutate();
    onClose();
  };

  // Format date as YY.MM.DD
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const year = date.getFullYear().toString().slice(-2);
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}.${month}.${day}`;
  };

  // Capitalize provider name
  const capitalizeProvider = (provider: string) => {
    return provider.charAt(0).toUpperCase() + provider.slice(1).toLowerCase();
  };

  return (
    <div className="flex flex-col h-full w-full px-2.5">
      {/* Profile area - horizontal layout */}
      <div className="w-full h-20 flex flex-row items-center justify-start ml-2.5">
        {/* Profile image */}
        <div className="w-16 h-16 rounded-full border-none overflow-hidden ml-2.5">
          <Image
            src={user.profile_image || '/icons/profileDefault.svg'}
            alt={user.nickname}
            width={64}
            height={64}
            className="w-full h-full object-cover"
          />
        </div>

        {/* Profile text area */}
        <div className="flex flex-col justify-center items-start gap-1 flex-grow h-full ml-2.5">
          <p className="text-base font-medium text-black m-0">{user.nickname}</p>
          <p className="text-sm font-light text-grey-4 m-0">{user.email}</p>
        </div>

        {/* Logout button */}
        <button
          onClick={handleLogout}
          disabled={logoutMutation.isPending}
          className="bg-white flex flex-row justify-center items-center w-20 h-8
            rounded-btn-small border border-grey-2 ml-auto mr-[60px] mt-4
            hover:bg-btn-hover transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <p className="m-0 text-black text-sm">{logoutMutation.isPending ? '...' : '로그아웃'}</p>
        </button>
      </div>

      {/* Profile details */}
      <div className="flex flex-col justify-start items-start w-full h-[166px] mt-[18px]">
        <div className="flex flex-row justify-between items-center w-[380px] h-[35px] gap-[70px] border-b border-grey-2 ml-20">
          <p className="text-sm font-extralight text-grey-4">이름</p>
          <p className="text-sm font-normal text-black">{user.name || '-'}</p>
        </div>
        <div className="flex flex-row justify-between items-center w-[380px] h-[35px] gap-[70px] border-b border-grey-2 ml-20">
          <p className="text-sm font-extralight text-grey-4">전화번호</p>
          <p className="text-sm font-normal text-black">{user.mobile || '-'}</p>
        </div>
        <div className="flex flex-row justify-between items-center w-[380px] h-[35px] gap-[70px] border-b border-grey-2 ml-20">
          <p className="text-sm font-extralight text-grey-4">로그인 제공자</p>
          <p className="text-sm font-normal text-black">{capitalizeProvider(user.provider)}</p>
        </div>
        <div className="flex flex-row justify-between items-center w-[380px] h-[35px] gap-[70px] border-b border-grey-2 ml-20">
          <p className="text-sm font-extralight text-grey-4">가입일</p>
          <p className="text-sm font-normal text-black">{formatDate(user.date_joined)}</p>
        </div>
      </div>

      {/* Footer */}
      <div className="flex flex-col items-end w-full h-fit pr-[62px] box-border">
        {/* Delete account link */}
        <a
          href="#"
          className="text-grey-3 no-underline"
          onClick={(e) => {
            e.preventDefault();
            // TODO: Implement delete account functionality
            alert('회원 탈퇴 기능은 준비 중입니다.');
          }}
        >
          <p className="text-xs font-light text-grey-3 border-b border-grey-3 hover:text-black hover:border-black transition-colors">
            회원 탈퇴
          </p>
        </a>

        {/* Developed by Armori */}
        <a
          href="https://www.armori.io/"
          target="_blank"
          rel="noopener noreferrer"
          className="no-underline mt-[111px] mb-[5px]"
        >
          <p className="text-sm font-medium text-blue-1 hover:bg-gradient-to-r hover:from-blue-1 hover:via-blue-2 hover:via-blue-3 hover:via-blue-4 hover:to-blue-1 hover:bg-[length:250%_auto] hover:bg-clip-text hover:text-transparent hover:animate-[gradient-scroll_3s_linear_infinite] transition-all">
            Developed by <span className="text-base font-semibold">Armori</span>
          </p>
        </a>
      </div>
    </div>
  );
}

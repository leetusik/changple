'use client';

import { useRouter } from 'next/navigation';
import { useChatHistory } from '@/hooks/use-chat-history';

export function ChatHistory() {
  const router = useRouter();
  const { data, isLoading, error } = useChatHistory();
  const sessions = data?.results;

  const handleSessionClick = (nonce: string) => {
    router.push(`/chat/${nonce}`);
  };

  if (isLoading) {
    return (
      <div className="box-border flex flex-col gap-2.5 w-full mt-4 overflow-y-auto hide-scrollbar px-1.5">
        <div className="flex flex-row justify-start w-full mt-0.5">
          <p className="text-xl font-medium text-black m-0">지난 대화기록</p>
        </div>
        <div className="flex flex-col pt-2.5">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-10 bg-grey-1 rounded-md my-0.5 mx-3 animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="box-border flex flex-col gap-2.5 w-full mt-4 px-1.5">
        <div className="flex flex-row justify-start w-full mt-0.5">
          <p className="text-xl font-medium text-black m-0">지난 대화기록</p>
        </div>
        <p className="text-sm text-grey-4 py-2 px-3">
          대화 기록을 불러오는데 실패했습니다.
        </p>
      </div>
    );
  }

  if (!sessions || sessions.length === 0) {
    return (
      <div className="box-border flex flex-col gap-2.5 w-full mt-4 px-1.5">
        <div className="flex flex-row justify-start w-full mt-0.5">
          <p className="text-xl font-medium text-black m-0">지난 대화기록</p>
        </div>
        <p className="text-sm text-grey-4 py-2 px-3">
          아직 대화 기록이 없습니다.
        </p>
      </div>
    );
  }

  return (
    <div className="box-border flex flex-col gap-2.5 w-full mt-4 overflow-y-auto hide-scrollbar px-1.5">
      {/* Title - matching .historyTitle */}
      <div className="flex flex-row justify-start w-full mt-0.5">
        <p className="text-xl font-medium text-black m-0">지난 대화기록</p>
      </div>

      {/* History list - matching .historyList */}
      <div className="flex flex-col pt-2.5">
        {sessions.map((session) => (
          <p
            key={session.nonce}
            onClick={() => handleSessionClick(session.nonce)}
            className="font-light text-black whitespace-nowrap overflow-hidden text-ellipsis
              cursor-pointer py-2 px-3 my-0.5 rounded-md transition-colors duration-200
              hover:bg-btn-hover"
          >
            {session.title || '새 대화'}
          </p>
        ))}
      </div>
    </div>
  );
}

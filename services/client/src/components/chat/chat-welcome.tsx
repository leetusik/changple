'use client';

import { Button } from '@/components/ui/button';

const EXAMPLE_QUESTIONS = [
  '카페 창업시 준비해야 할 기본적인 것들은 무엇이 있나요?',
  '소규모 창업을 하려는데, 구체적인 창업 비용과 항목 별 금액도 알 수 있나요?',
  '창플의 창업 철학에 대해 얘기해주세요.',
];

interface ChatWelcomeProps {
  userName?: string;
  onExampleClick?: (question: string) => void;
}

export function ChatWelcome({ userName, onExampleClick }: ChatWelcomeProps) {
  return (
    <div className="flex flex-col items-center justify-center flex-1 w-full max-w-2xl px-4">
      {/* Greeting */}
      <div className="text-center mb-8">
        <h1 className="text-[32px] font-bold text-blue-2 mb-2">
          {userName ? `${userName}님, 안녕하세요` : '안녕하세요, 창플 AI입니다'}
        </h1>
        <p className="text-xl text-black">
          수만개의 창플 데이터, 이제 검색 말고{' '}
          <span className="font-semibold">질문</span>하세요
        </p>
      </div>

      {/* Example Questions */}
      <div className="w-full">
        <p className="text-grey-4 text-sm mb-3 text-center">
          이런 질문을 해보세요
        </p>
        <ul className="flex flex-col gap-2">
          {EXAMPLE_QUESTIONS.map((question, index) => (
            <li key={index}>
              <Button
                variant="outline"
                className="w-full h-auto py-3 px-4 text-left text-grey-5 bg-white border-grey-2 hover:bg-btn-hover rounded-pill justify-start font-normal whitespace-normal"
                onClick={() => onExampleClick?.(question)}
              >
                {question}
              </Button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

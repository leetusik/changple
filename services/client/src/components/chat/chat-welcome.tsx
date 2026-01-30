'use client';

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
    <div className="flex flex-col items-center justify-center h-full w-full">
      {/* Greeting - matching chatWelcomeMessage */}
      <h1
        className="text-blue-2 text-[32px] font-semibold text-center px-3 mt-auto mb-[15px] w-fit"
      >
        {userName ? `Hello, ${userName}님` : '안녕하세요'}
      </h1>

      {/* Sub-message - matching chatWelcomeMessage-2 */}
      <p className="text-black text-xl font-normal text-center px-3 mb-[54px] w-fit">
        많은 데이터, 이제 검색 말고{' '}
        <span className="text-blue-2 font-medium">질문</span>하세요
      </p>

      {/* Example Questions - matching chatExampleList */}
      <div className="flex flex-col items-start gap-[10px] pl-[10%] mb-[150px] w-fit">
        {/* Description - matching chatExampleDescription */}
        <p className="text-sm pl-3 text-grey-3">
          이런 질문을 해보세요
        </p>

        {/* Example buttons - matching chatExample */}
        {EXAMPLE_QUESTIONS.map((question, index) => (
          <button
            key={index}
            onClick={() => onExampleClick?.(question)}
            className="h-auto min-h-[36px] py-1.5 px-3 bg-white rounded-pill
              border border-grey-3 text-left text-sm max-w-full
              whitespace-normal break-words cursor-pointer
              transition-all duration-200 box-border text-black
              hover:bg-btn-hover"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}

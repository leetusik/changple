'use client';

export function MobileWarning() {
  return (
    <div className="mobile-message fixed inset-0 w-full h-full bg-white z-[9999] hidden flex-col justify-center items-center text-center text-lg leading-relaxed text-blue-2 md:!hidden max-md:!flex">
      <p>
        본 서비스는 PC환경에 최적화되어 있습니다.
        <br />
        <br />
        <strong>PC로 접속하여 사용해주세요.</strong>
      </p>
    </div>
  );
}

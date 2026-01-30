'use client';

import Image from 'next/image';

export function TabCompany() {
  return (
    <div className="w-full h-full overflow-y-auto overflow-x-hidden px-5 py-6 hide-scrollbar">
      <div className="flex flex-col items-center w-full gap-[58px]">
        {/* 창플의 확고한 철학 */}
        <section className="w-full flex flex-col items-center">
          <h3 className="text-sm font-medium text-blue-2 text-center mb-[7px]">창플의 확고한 철학</h3>
          <h2 className="text-[23px] font-semibold text-black text-center leading-[1.3] mb-2.5">
            초보 창업자들의 &apos;생존&apos;
          </h2>
          <p className="text-[13px] font-light text-black leading-[1.6] text-center mb-2.5">
            창플 비즈니스는 &apos;초보 창업자들의 생존&apos;을 위해 창업을 의뢰하는 플랫폼입니다.
            <br />
            우리는 대박 매출이 아닌 생존이 목표입니다. 일반인에서 자영업자로 신분 전환하는 것을
            목적으로 존재하며 선한 상생의 마음으로 동반 성장을 이룹니다.
          </p>
          <div className="w-full h-[200px] bg-grey-2 rounded-[10px] flex items-center justify-center overflow-hidden relative">
            <Image
              src="/company-info-01.jpg"
              alt="초보 창업자들의 생존"
              fill
              className="object-cover"
            />
            <div className="absolute inset-0 rounded-[10px] bg-gradient-to-b from-[rgba(102,102,102,0.33)] via-[rgba(34,34,34,0.33)] to-[rgba(0,0,0,0.33)] pointer-events-none"></div>
          </div>
        </section>

        {/* 창플의 핵심 사업 */}
        <section className="w-full flex flex-col items-center">
          <h3 className="text-sm font-medium text-blue-2 text-center mb-[7px]">창플의 핵심 사업</h3>
          <div className="w-full flex flex-row gap-2 mt-2">
            <div className="flex-[0.825] flex flex-col items-start gap-2 p-3 bg-grey-0 rounded-lg">
              <div className="text-2xl mb-0.5">💡</div>
              <h4 className="text-sm font-semibold text-black">아키프로젝트</h4>
              <p className="text-xs font-light text-black leading-[1.5]">
                남의 브랜드말고<br />나의 브랜드를<br />만들려는 분들께
              </p>
            </div>
            <div className="flex-[1.35] flex flex-col items-start gap-2 p-3 bg-grey-0 rounded-lg">
              <div className="text-2xl mb-0.5">⚖️</div>
              <h4 className="text-sm font-semibold text-black">팀비즈니스</h4>
              <p className="text-xs font-light text-black leading-[1.5]">
                생존에 성공한 고수 자영업자를<br />예비 사업가로 육성하고<br />초보 창업자들에게 전수하는 노하우
              </p>
            </div>
            <div className="flex-[0.825] flex flex-col items-start gap-2 p-3 bg-grey-0 rounded-lg">
              <div className="text-2xl mb-0.5">⚡</div>
              <h4 className="text-sm font-semibold text-black">프랜차이즈</h4>
              <p className="text-xs font-light text-black leading-[1.5]">
                검증된<br />브랜드들
              </p>
            </div>
          </div>
        </section>

        {/* 창플 사업의 모토 */}
        <section className="w-full flex flex-col items-center">
          <h3 className="text-sm font-medium text-blue-2 text-center mb-[7px]">창플 사업의 모토</h3>
          <h2 className="text-[23px] font-semibold text-black text-center leading-[1.3] mb-2.5">
            초보창업자의 생존을 도우며<br />사업가로서 나의 성장을 도모합니다
          </h2>
          <p className="text-[13px] font-light text-black leading-[1.6] text-center">
            예비사업가는 창플을 통해서 부족한 사업인프라를 갖추고 사업을 시작할수 있으며<br />
            예비창업자는 검증된 창플의 브랜드로 시행착오를 줄이면서 자영업자로 연착륙합니다.
          </p>
        </section>

        {/* 창플의 신뢰와 인프라 */}
        <section className="w-full flex flex-col items-center">
          <h3 className="text-sm font-medium text-blue-2 text-center mb-[7px]">창플의 신뢰와 인프라</h3>
          <div className="w-full flex flex-row flex-wrap gap-3 mt-2">
            {/* 사업 경력 */}
            <div className="flex-[0_0_calc(50%-6px)] flex flex-col items-center gap-3 text-center">
              <div className="w-[230px] h-[230px] bg-grey-2 rounded-[10px] flex items-center justify-center overflow-hidden relative mb-3">
                <Image
                  src="/사업경력.jpg"
                  alt="사업 경력"
                  fill
                  className="object-cover"
                />
                <div className="absolute inset-0 rounded-[10px] bg-gradient-to-b from-[rgba(102,102,102,0.33)] via-[rgba(34,34,34,0.33)] to-[rgba(0,0,0,0.33)] pointer-events-none z-[1]"></div>
                <h4 className="absolute top-4 left-4 right-4 z-10 text-white text-base font-semibold text-left drop-shadow-[0_1px_3px_rgba(0,0,0,0.5)]">사업 경력</h4>
                <p className="absolute bottom-4 left-4 right-4 z-10 text-white text-[11px] font-light leading-[1.5] text-left drop-shadow-[0_1px_3px_rgba(0,0,0,0.5)]">
                  (주)창플의 전신은 지난 10년간 총 7개브랜드 국내외 500호점 가맹점을 출점시킨 경험이 있는 프랜차이즈 회사였습니다.
                  본사매각후 진짜 창업자들을 돕겠다는 일념으로 운영하며 최근 3년간 만들어낸 신규브랜드는 50여개 이상, 실제 예비창업자들의
                  매장오픈은 150여개 이상 함께 도우며 만들어 왔습니다.
                </p>
              </div>
            </div>

            {/* 창업 인프라 */}
            <div className="flex-[0_0_calc(50%-6px)] flex flex-col items-center gap-3 text-center">
              <div className="w-[230px] h-[230px] bg-grey-2 rounded-[10px] flex items-center justify-center overflow-hidden relative mb-3">
                <Image
                  src="/창업 인프라.jpg"
                  alt="창업 인프라"
                  fill
                  className="object-cover"
                />
                <div className="absolute inset-0 rounded-[10px] bg-gradient-to-b from-[rgba(102,102,102,0.33)] via-[rgba(34,34,34,0.33)] to-[rgba(0,0,0,0.33)] pointer-events-none z-[1]"></div>
                <h4 className="absolute top-4 left-4 right-4 z-10 text-white text-base font-semibold text-left drop-shadow-[0_1px_3px_rgba(0,0,0,0.5)]">창업 인프라</h4>
                <p className="absolute bottom-[50px] left-4 right-4 z-10 text-white text-[11px] font-light leading-[1.5] text-left drop-shadow-[0_1px_3px_rgba(0,0,0,0.5)]">
                  현재 창플에서 활동하는 프랜차이즈와 팀비즈니스 브랜드는 20개 이상이며 YouTube 구독자 11만 명,
                  창플TV, 네이버 카페/블로그 합산 13만 명이
                  모여있는 명실공히 대한민국 창업플랫폼입니다.
                </p>
              </div>
            </div>

            {/* 전문 지원 */}
            <div className="flex-[0_0_calc(50%-6px)] flex flex-col items-center gap-3 text-center relative">
              <div className="w-[230px] h-[230px] bg-grey-2 rounded-[10px] flex items-center justify-center overflow-hidden relative mb-3">
                <Image
                  src="/전문지원.jpeg"
                  alt="전문 지원"
                  fill
                  className="object-cover"
                />
                <div className="absolute inset-0 rounded-[10px] bg-gradient-to-b from-[rgba(102,102,102,0.33)] via-[rgba(34,34,34,0.33)] to-[rgba(0,0,0,0.33)] pointer-events-none z-[1]"></div>
                <h4 className="absolute top-4 left-4 right-4 z-10 text-white text-base font-semibold text-left drop-shadow-[0_1px_3px_rgba(0,0,0,0.5)]">전문 지원</h4>
                <p className="absolute bottom-[65px] left-4 right-4 z-10 text-white text-[11px] font-light leading-[1.5] text-left drop-shadow-[0_1px_3px_rgba(0,0,0,0.5)]">
                  상권 개발/입지분석/견적조율, 브랜딩 기획, 로고 제작, 공간 기획, VMD 기획, 메뉴개발,자영업자 마케팅 등
                  창업에 필요한 모든 과정을 전문성을 갖춘 창플 팀이 지원합니다.
                </p>
              </div>
            </div>

            {/* Logo */}
            <div className="flex-[0_0_calc(50%-6px)] flex items-center justify-center">
              <Image
                src="/logo-vertical.svg"
                alt="창플 로고"
                width={100}
                height={100}
                className="opacity-90"
              />
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="w-full flex flex-col items-center gap-4 pt-2.5">
          <div className="flex flex-col items-center gap-2">
            <div className="text-xs font-light text-grey-3 text-center leading-[1.4]">(주)창플 | 283-88-00211 | 02-2054-3956</div>
          </div>
          <div className="text-[9px] font-light text-grey-3 text-center -mt-2.5">
            @Copyright @ ChangpleTeamBusiness Inc. All Rights Reserved.
          </div>
        </footer>
      </div>
    </div>
  );
}

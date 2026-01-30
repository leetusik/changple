'use client';

import { Check } from 'lucide-react';

export function TabPlan() {
  return (
    <div className="w-full h-full flex flex-col justify-start items-center gap-1.5 overflow-y-auto py-[5px] px-0 hide-scrollbar">
      {/* Free Plan */}
      <div className="flex flex-col justify-center items-start bg-grey-0 w-[500px] h-fit p-4 pb-3 pt-3 rounded-md">
        <div className="w-full h-[30px] text-lg font-semibold text-black flex flex-row justify-between items-center mb-1">
          <p>Free</p>
          <div className="bg-white w-[120px] h-[30px] rounded-btn-small border border-grey-2 text-sm font-medium text-black mr-2.5 flex flex-row justify-center items-center cursor-default">
            무료 플랜
          </div>
        </div>

        <div className="flex flex-row items-center justify-between items-center w-full h-fit mt-1">
          <div className="w-fit h-fit flex flex-row justify-center items-center gap-0.5 mt-0.5 ml-3.5">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 17 15" fill="none" className="w-3.5 h-auto">
              <path
                d="M16.0883 8.271H14.1883L13.1053 14.636H10.3503L9.93234 12.546C9.68534 11.33 9.36234 9.734 9.07734 8.271H7.51934C7.23434 9.734 6.93034 11.33 6.68334 12.546L6.26534 14.636H3.60534L2.46534 8.271H0.527344V6.808H2.19934L1.07834 0.5H3.56734L4.44134 6.808H6.15134C6.28434 6.143 6.55034 4.889 6.93034 3.065L7.29134 1.336H9.49534L9.83734 3.065C10.2173 4.889 10.4833 6.143 10.6163 6.808H12.3453L13.1623 0.5H15.4803L14.4163 6.808H16.0883V8.271ZM8.79234 6.808L8.31734 4.205L7.78534 6.808H8.79234ZM5.14434 11.9C5.16334 11.843 5.18234 11.691 5.23934 11.463C5.27734 11.254 5.37234 10.779 5.52434 10.038C5.65734 9.297 5.79034 8.727 5.88534 8.271H4.63134C4.65034 8.499 4.72634 9.069 4.85934 9.962C4.99234 10.855 5.04934 11.501 5.10634 11.9H5.14434ZM10.8823 8.271C10.9773 8.727 11.0533 9.164 11.1483 9.563C11.3003 10.38 11.3953 10.893 11.6043 11.9H11.6803C11.7373 11.501 11.8703 10.323 12.1173 8.271H10.8823Z"
                fill="#323232"
              />
            </svg>
            <p className="text-base font-normal text-black m-0">0</p>
            <span className="text-lg text-black">KRW / 월</span>
          </div>
        </div>

        <div className="w-full h-fit text-sm font-light text-grey-4 mb-2.5 mt-0.5">
          <p className="w-fit h-fit pl-[30px] m-0 mt-0.5 text-black">
            창플 AI로, 창플만의 창업 인사이트를 얻어보세요
          </p>
        </div>

        <div className="flex flex-row items-center justify-start gap-1.5 w-fit h-5 text-sm font-light text-grey-4 pl-10">
          <Check className="w-4 h-auto text-grey-4" />
          <p className="m-0">1일 10회 질문 가능</p>
        </div>
      </div>

      {/* Pro Plan */}
      <div className="flex flex-col justify-center items-start bg-grey-0 w-[500px] h-fit p-4 pb-3 pt-3 rounded-md">
        <div className="w-full h-[30px] text-lg font-semibold text-black flex flex-row justify-between items-center mb-1">
          <p>Pro</p>
          <div className="bg-grey-1 w-[120px] h-[30px] rounded-btn-small border border-grey-3 text-sm font-medium text-grey-3 mr-2.5 flex flex-row justify-center items-center cursor-default">
            나의 플랜
          </div>
        </div>

        <div className="flex flex-row items-center justify-between items-center w-full h-fit mt-1">
          <div className="w-fit h-fit flex flex-row justify-center items-center gap-0.5 mt-0.5 ml-3.5 line-through decoration-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 17 15" fill="none" className="w-3.5 h-auto">
              <path
                d="M16.0883 8.271H14.1883L13.1053 14.636H10.3503L9.93234 12.546C9.68534 11.33 9.36234 9.734 9.07734 8.271H7.51934C7.23434 9.734 6.93034 11.33 6.68334 12.546L6.26534 14.636H3.60534L2.46534 8.271H0.527344V6.808H2.19934L1.07834 0.5H3.56734L4.44134 6.808H6.15134C6.28434 6.143 6.55034 4.889 6.93034 3.065L7.29134 1.336H9.49534L9.83734 3.065C10.2173 4.889 10.4833 6.143 10.6163 6.808H12.3453L13.1623 0.5H15.4803L14.4163 6.808H16.0883V8.271ZM8.79234 6.808L8.31734 4.205L7.78534 6.808H8.79234ZM5.14434 11.9C5.16334 11.843 5.18234 11.691 5.23934 11.463C5.27734 11.254 5.37234 10.779 5.52434 10.038C5.65734 9.297 5.79034 8.727 5.88534 8.271H4.63134C4.65034 8.499 4.72634 9.069 4.85934 9.962C4.99234 10.855 5.04934 11.501 5.10634 11.9H5.14434ZM10.8823 8.271C10.9773 8.727 11.0533 9.164 11.1483 9.563C11.3003 10.38 11.3953 10.893 11.6043 11.9H11.6803C11.7373 11.501 11.8703 10.323 12.1173 8.271H10.8823Z"
                fill="#323232"
              />
            </svg>
            <p className="text-base font-normal text-black m-0">19,000</p>
            <span className="text-lg text-black">KRW / 월</span>
          </div>
        </div>

        <div className="w-full h-fit text-sm font-light text-grey-4 mb-2.5 mt-0.5">
          <p className="w-fit h-fit pl-[30px] m-0 mt-0.5 text-black">
            창플 AI의 고급 정보를 이용해 보세요
          </p>
        </div>

        <div className="flex flex-row items-center justify-start gap-1.5 w-fit h-5 text-sm font-light pl-10">
          <Check className="w-4 h-auto text-blue-2" />
          <p className="m-0 text-blue-2">무료 이벤트 기간</p>
        </div>
        <div className="flex flex-row items-center justify-start gap-1.5 w-fit h-5 text-sm font-light text-grey-4 pl-10">
          <Check className="w-4 h-auto text-grey-4" />
          <p className="m-0">무제한 질문 가능</p>
        </div>
        <div className="flex flex-row items-center justify-start gap-1.5 w-fit h-5 text-sm font-light text-grey-4 pl-10">
          <Check className="w-4 h-auto text-grey-4" />
          <p className="m-0">창플 맴버십회원 등록</p>
        </div>
      </div>

      {/* 1:1 Consulting */}
      <div className="flex flex-col justify-center items-start bg-grey-0 w-[500px] h-fit p-4 pb-3 pt-3 rounded-md">
        <div className="w-full h-[30px] text-lg font-semibold text-black flex flex-row justify-between items-center mb-1">
          <p>1:1 Consulting</p>
          <a
            href="https://naver.me/xXEHVSyQ"
            target="_blank"
            rel="noopener noreferrer"
            className="bg-white w-[120px] h-[30px] rounded-btn-small border border-grey-2 text-sm font-medium text-black mr-2.5 flex flex-row justify-center items-center hover:bg-btn-hover transition-colors no-underline"
          >
            상담 신청하기
          </a>
        </div>

        <div className="flex flex-row items-center justify-between items-center w-full h-fit mt-1">
          <div className="w-fit h-fit flex flex-row justify-center items-center gap-0.5 mt-0.5 ml-3.5">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 17 15" fill="none" className="w-3.5 h-auto">
              <path
                d="M16.0883 8.271H14.1883L13.1053 14.636H10.3503L9.93234 12.546C9.68534 11.33 9.36234 9.734 9.07734 8.271H7.51934C7.23434 9.734 6.93034 11.33 6.68334 12.546L6.26534 14.636H3.60534L2.46534 8.271H0.527344V6.808H2.19934L1.07834 0.5H3.56734L4.44134 6.808H6.15134C6.28434 6.143 6.55034 4.889 6.93034 3.065L7.29134 1.336H9.49534L9.83734 3.065C10.2173 4.889 10.4833 6.143 10.6163 6.808H12.3453L13.1623 0.5H15.4803L14.4163 6.808H16.0883V8.271ZM8.79234 6.808L8.31734 4.205L7.78534 6.808H8.79234ZM5.14434 11.9C5.16334 11.843 5.18234 11.691 5.23934 11.463C5.27734 11.254 5.37234 10.779 5.52434 10.038C5.65734 9.297 5.79034 8.727 5.88534 8.271H4.63134C4.65034 8.499 4.72634 9.069 4.85934 9.962C4.99234 10.855 5.04934 11.501 5.10634 11.9H5.14434ZM10.8823 8.271C10.9773 8.727 11.0533 9.164 11.1483 9.563C11.3003 10.38 11.3953 10.893 11.6043 11.9H11.6803C11.7373 11.501 11.8703 10.323 12.1173 8.271H10.8823Z"
                fill="#323232"
              />
            </svg>
            <p className="text-base font-normal text-black m-0">150,000</p>
            <span className="text-lg text-black">KRW / 1회</span>
          </div>
        </div>

        <div className="w-full h-fit text-sm font-light text-grey-4 mb-2.5 mt-0.5">
          <p className="w-fit h-fit pl-[30px] m-0 mt-0.5 text-black">
            최고 수준의 전문가와 상담하기
          </p>
        </div>

        <div className="flex flex-row items-center justify-start gap-1.5 w-fit h-5 text-sm font-light text-grey-4 pl-10">
          <Check className="w-4 h-auto text-grey-4" />
          <p className="m-0">창플지기와의 1:1 대면 상담(1회)</p>
        </div>
      </div>
    </div>
  );
}

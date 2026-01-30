'use client';

export function TabPrivacy() {
  return (
    <div className="w-full h-full overflow-y-auto overflow-x-hidden px-5 py-4 hide-scrollbar">
      <p className="text-base font-medium text-black mb-4">개인정보처리방침</p>

      <div className="text-[13px] text-black space-y-4 leading-relaxed font-light">
        <p>
          주식회사 창플(이하 &apos;회사&apos;)은 개인정보보호법에 따라 이용자의 개인정보 보호 및 권익을 보호하고 개인정보와 관련한 이용자의 고충을 원활하게 처리할 수
          있도록 다음과 같은 처리방침을 두고 있습니다.
        </p>

        <p>
          회사는 개인정보처리방침을 변경하는 경우 웹사이트 공지사항(또는 개별공지)을 통하여 공지할 것입니다.
        </p>

        <div>
          <p className="font-medium text-black mb-2">1. 개인정보의 처리 목적</p>
          <p className="mb-2">회사는 다음의 목적을 위하여 개인정보를 처리하고 있으며, 다음의 목적 이외의 용도로는 이용하지 않습니다.</p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>회원 가입 및 관리: 회원제 서비스 이용에 따른 본인확인, 개인 식별, 불량회원의 부정 이용 방지와 비인가 사용 방지, 가입 의사 확인</li>
            <li>서비스 제공: 챗봇 AI 서비스 제공, 맞춤형 콘텐츠 제공</li>
            <li>서비스 개선: 신규 서비스 개발, 기존 서비스 개선, AI 모델 학습 및 성능 향상</li>
          </ul>
        </div>

        <div>
          <p className="font-medium text-black mb-2">2. 처리하는 개인정보의 항목</p>
          <p className="mb-2">회사는 다음과 같은 개인정보 항목을 처리하고 있습니다.</p>
          <div className="space-y-2">
            <p>• 필수항목: 이메일 주소, 이름, 전화번호, 네이버 프로필 사진 - 회원 식별, 서비스 이용 및 상담 (보유기간: 회원 탈퇴 시까지)</p>
            <p>• 서비스 이용 과정에서 생성되는 정보: 챗봇과의 대화 내용 - 서비스 제공, AI 응답 생성 (보유기간: 회원 탈퇴 시까지)</p>
            <p>• 서비스 이용 기록: 접속 시간, 이용 기록, 쿠키, 세션 등 - 서비스 이용 분석 및 개선 (보유기간: 회원 탈퇴 시까지, 접속 기록은 3개월)</p>
          </div>
        </div>

        <div>
          <p className="font-medium text-black mb-2">3. 개인정보의 처리 및 보유 기간</p>
          <p className="mb-2">회사는 법령에 따른 개인정보 보유·이용기간 또는 정보주체로부터 개인정보 수집 시에 동의 받은 개인정보 보유·이용기간 내에서 개인정보를 처리·보유합니다.</p>
          <ul className="list-disc list-inside space-y-1">
            <li>회원 가입 및 관리: 회원 탈퇴 시까지</li>
            <li>챗봇 대화 내용: 회원 탈퇴 시까지</li>
            <li>다만, 관계 법령에 따라 보존할 필요가 있는 경우 해당 법령에서 정한 기간 동안 보존합니다.</li>
          </ul>
        </div>

        <div>
          <p className="font-medium text-black mb-2">4. 개인정보의 제3자 제공</p>
          <p>
            회사는 정보주체의 동의, 법률의 특별한 규정 등 개인정보 보호법 제17조 및 제18조에 해당하는 경우에만 개인정보를 제3자에게 제공합니다.
            현재 회사는 이용자의 개인정보를 제3자에게 제공하지 않습니다.
          </p>
        </div>

        <div>
          <p className="font-medium text-black mb-2">5. 개인정보처리 위탁</p>
          <p className="mb-2">회사는 서비스 제공을 위해 필요한 업무 중 일부를 외부 업체에 위탁하고 있으며, 위탁업무의 내용과 수탁자는 다음과 같습니다.</p>
          <ul className="list-disc list-inside space-y-1">
            <li>네이버(주): 유저 로그인 서비스</li>
            <li>토스페이먼츠 주식회사: 유료 서비스 제공을 위한 결제</li>
            <li>Oracle: 데이터보관 및 전산시스템 운용·관리</li>
            <li>OpenAI: API 서비스 제공</li>
            <li>Google: API 서비스 제공</li>
          </ul>
        </div>

        <div>
          <p className="font-medium text-black mb-2">6. 정보주체의 권리·의무 및 그 행사방법</p>
          <p className="mb-2">이용자는 개인정보주체로서 다음과 같은 권리를 행사할 수 있습니다.</p>
          <ul className="list-disc list-inside space-y-1">
            <li>개인정보 열람요구</li>
            <li>오류 등이 있을 경우 정정 요구</li>
            <li>삭제요구</li>
            <li>처리정지 요구</li>
          </ul>
          <p className="mt-2">
            위 권리 행사는 회사에 대해 서면, 전화, 이메일 등을 통하여 하실 수 있으며 회사는 이에 대해 지체 없이 조치하겠습니다.
            정보주체가 개인정보의 오류 등에 대한 정정 또는 삭제를 요구한 경우에는 회사는 정정 또는 삭제를 완료할 때까지 당해 개인정보를 이용하거나 제공하지 않습니다.
          </p>
        </div>

        <div>
          <p className="font-medium text-black mb-2">7. 개인정보의 안전성 확보 조치</p>
          <p className="mb-2">회사는 개인정보보호법 제29조에 따라 다음과 같이 안전성 확보에 필요한 기술적, 관리적, 물리적 조치를 하고 있습니다.</p>
          <ul className="list-disc list-inside space-y-1">
            <li>개인정보의 암호화: 이용자의 비밀번호와 같은 중요한 데이터는 암호화되어 저장 및 관리되고 있습니다.</li>
            <li>해킹 등에 대비한 기술적 대책: 회사는 해킹이나 컴퓨터 바이러스 등에 의한 개인정보 유출 및 훼손을 막기 위하여 보안프로그램을 설치하고 주기적인 갱신·점검을 하며 외부로부터 접근이 통제된 구역에 시스템을 설치하고 기술적/물리적으로 감시 및 차단하고 있습니다.</li>
            <li>개인정보에 대한 접근 제한: 개인정보를 처리하는 데이터베이스시스템에 대한 접근권한의 부여, 변경, 말소를 통하여 개인정보에 대한 접근통제를 위하여 필요한 조치를 하고 있습니다.</li>
          </ul>
        </div>

        <div>
          <p className="font-medium text-black mb-2">8. 개인정보 보호책임자</p>
          <p className="mb-2">회사는 개인정보 처리에 관한 업무를 총괄해서 책임지고, 개인정보 처리와 관련한 정보주체의 불만처리 및 피해구제 등을 위하여 아래와 같이 개인정보 보호책임자를 지정하고 있습니다.</p>
          <div className="space-y-1">
            <p>개인정보 보호책임자: 한범구</p>
            <p>직책: 대표이사</p>
            <p>개인정보 보호 담당부서: 개인정보보호팀</p>
            <p>이메일: tiger9@changple.com</p>
            <p>전화번호: 02-2054-3956</p>
          </div>
        </div>

        <div>
          <p className="font-medium text-black mb-2">9. 개인정보 처리방침 변경</p>
          <p>이 개인정보 처리방침은 2024년 5월 15일부터 적용됩니다.</p>
          <p className="mt-2">이전의 개인정보 처리방침은 해당 시행일자를 클릭하시면 확인하실 수 있습니다.</p>
        </div>
      </div>
    </div>
  );
}

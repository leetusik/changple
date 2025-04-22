//------------------------------------------------------------------------
//------ 뒤로가기 arrow  hover ------------------------------------------------
document.addEventListener("DOMContentLoaded", function () {
  // 로그아웃 버튼 요소 가져오기
  const arrowButton = document.querySelector(".arrow-block");

  // 원래 배경색 저장 (없으면 기본값 설정)
  const originalColor =
    window.getComputedStyle(arrowButton).backgroundColor || "transparent";

  // transition 효과 추가
  arrowButton.style.transition = "background-color 0.3s ease";

  // 마우스 오버 이벤트 처리
  arrowButton.addEventListener("mouseover", function () {
    // 배경색 변경
    this.style.backgroundColor = "#D2DBEB";
  });

  // 마우스 아웃 이벤트 처리
  arrowButton.addEventListener("mouseout", function () {
    // 원래 배경색으로 복원
    this.style.backgroundColor = originalColor;
  });
});

//------------------------------------------------------------------------
//------ 유료플랜 결제 hover ------------------------------------------------
document.addEventListener("DOMContentLoaded", function () {
  // 로그아웃 버튼 요소 가져오기
  const payplanButton = document.querySelector(
    ".pay_plan-block-content-btn-area"
  );

  // 원래 배경색 저장 (없으면 기본값 설정)
  const originalColor =
    window.getComputedStyle(payplanButton).backgroundColor || "transparent";

  // transition 효과 추가
  payplanButton.style.transition = "background-color 0.3s ease";

  // 마우스 오버 이벤트 처리
  payplanButton.addEventListener("mouseover", function () {
    // 배경색 변경
    this.style.backgroundColor = "#6985B7";
  });

  // 마우스 아웃 이벤트 처리
  payplanButton.addEventListener("mouseout", function () {
    // 원래 배경색으로 복원
    this.style.backgroundColor = originalColor;
  });
});

//------------------------------------------------------------------------
//------ 로그아웃 버튼 hover ------------------------------------------------
document.addEventListener("DOMContentLoaded", function () {
  // 로그아웃 버튼 요소 가져오기
  const logoutButton = document.querySelector(".buttons-block-logout-area");

  // 원래 배경색 저장 (없으면 기본값 설정)
  const originalColor =
    window.getComputedStyle(logoutButton).backgroundColor || "transparent";

  // transition 효과 추가
  logoutButton.style.transition = "background-color 0.3s ease";

  // 마우스 오버 이벤트 처리
  logoutButton.addEventListener("mouseover", function () {
    // 배경색 변경
    this.style.backgroundColor = "#EFF2FA";
  });

  // 마우스 아웃 이벤트 처리
  logoutButton.addEventListener("mouseout", function () {
    // 원래 배경색으로 복원
    this.style.backgroundColor = originalColor;
  });
});

//------------------------------------------------------------------------
//------ 회원탈퇴 버튼 hover ------------------------------------------------
document.addEventListener("DOMContentLoaded", function () {
  // 로그아웃 버튼 요소 가져오기
  const resignButton = document.querySelector(".buttons-block-resign-area");

  // 원래 배경색 저장 (없으면 기본값 설정)
  const originalColor =
    window.getComputedStyle(resignButton).backgroundColor || "transparent";

  // transition 효과 추가
  resignButton.style.transition = "background-color 0.3s ease";

  // 마우스 오버 이벤트 처리
  resignButton.addEventListener("mouseover", function () {
    // 배경색 변경
    this.style.backgroundColor = "#D2DBEB";
  });

  // 마우스 아웃 이벤트 처리
  resignButton.addEventListener("mouseout", function () {
    // 원래 배경색으로 복원
    this.style.backgroundColor = originalColor;
  });
});

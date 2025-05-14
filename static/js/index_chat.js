// Function to adjust textarea height
function adjustTextareaHeight() {
  const inputBox = document.querySelector(".input-box-unlocked");
  if (!inputBox) return; // 요소가 없을 경우 종료

  inputBox.style.height = "auto"; // Temporarily shrink height to calculate scrollHeight correctly
  let scrollHeight = inputBox.scrollHeight;
  const maxHeight = parseInt(window.getComputedStyle(inputBox).maxHeight, 10); // Get max-height from CSS

  // Apply scrollHeight if less than max-height, otherwise apply max-height
  if (scrollHeight <= maxHeight) {
    inputBox.style.height = scrollHeight + "px";
  } else {
    inputBox.style.height = maxHeight + "px";
  }
}

// 대화 메시지를 화면에 추가하는 함수
function addMessageToChat(
  role,
  content,
  showSpinner = false,
  messagePk = null
) {
  const promptContainer = document.querySelector(".prompt-wrapper");
  if (!promptContainer) return null; // ID를 반환해야 하므로 null 반환

  let messageId = ""; // 메시지 블록 ID
  let contentSpanId = null; // 내용 표시용 span ID (assistant 경우)

  // Generate unique IDs for the message
  const timestamp = Date.now();
  messageId = role + "-message-" + timestamp;
  contentSpanId = role + "-content-" + timestamp;

  // Check if a duplicate of this message already exists (for user messages only)
  if (role === "user") {
    // Simple check for duplicates by content
    const existingUserMessages = promptContainer.querySelectorAll(
      ".prompt-answer-block .prompt-text-area p"
    );
    for (const msg of existingUserMessages) {
      if (msg.textContent.trim() === content.trim()) {
        console.log(
          "Duplicate user message detected, skipping:",
          content.substring(0, 30)
        );
        return null; // Skip adding this message
      }
    }

    const userMessageHTML = `
      <div id="${messageId}" class="prompt-answer-block">
        <div class="prompt-text-area">
          <p>${content}</p> 
        </div>
      </div>
    `;
    promptContainer.insertAdjacentHTML("beforeend", userMessageHTML);
  } else if (role === "assistant") {
    // 마크다운 파싱 및 XSS 방지 적용
    let formattedContent = "";
    if (content && content.trim() !== "") {
      // 마크다운 렌더링 및 DOMPurify 적용
      formattedContent = DOMPurify.sanitize(marked.parse(content));
    }

    // Spinner HTML with node status display
    const spinnerHTML = showSpinner
      ? `<div class="spinner-container" style="display: flex; justify-content: flex-start; align-items: center; padding: 10px;"><div class="message-spinner"></div><span class="node-status"></span></div>`
      : "";

    // Add rating buttons for assistant messages
    const ratingHTML = `
      <div class="message-rating" data-message-pk="${messagePk || ""}">
        <button class="rating-btn rating-good" title="좋아요">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
          </svg>
        </button>
        <button class="rating-btn rating-bad" title="별로예요">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path>
          </svg>
        </button>
      </div>
    `;

    // 초기에는 spinner 또는 비어있는 span을 포함하여 추가
    const botMessageHTML = `
      <br>
      <div id="${messageId}" class="prompt-p" data-message-pk="${messagePk || ""
      }">
        ${spinnerHTML} 
        <span id="${contentSpanId}" ${showSpinner ? 'style="display: none;"' : ""
      }>${formattedContent}</span>
        ${!showSpinner ? ratingHTML : ""}
      </div>
    `;
    promptContainer.insertAdjacentHTML("beforeend", botMessageHTML);
  }

  // 새 메시지로 스크롤 (smoothly)
  const element = document.getElementById(messageId);
  if (element) {
    element.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // assistant 역할일 경우, 내용 span의 ID 반환
  return contentSpanId;
}

// 로딩 메시지 추가 (현재 사용되지 않음 - 스트리밍 UI로 대체)
function addLoadingMessage() {
  const loadingId = "loading-" + Date.now();
  // const promptContainer = document.querySelector('.prompt-wrapper');
  //  if (!promptContainer) return loadingId; // ID 반환은 유지

  // const loadingHTML = `
  //     <div id="${loadingId}" class="prompt-p">생성중...</div>
  // `;
  // promptContainer.insertAdjacentHTML('beforeend', loadingHTML);

  // 새 메시지로 스크롤 (smoothly)
  // const element = document.getElementById(loadingId);
  // if (element) {
  //     element.scrollIntoView({ behavior: 'smooth', block: 'center' });
  // }
  console.warn("addLoadingMessage is deprecated and replaced by streaming UI.");
  return loadingId; // 이전 코드 호환성을 위해 ID 반환
}

// 로딩 메시지 제거 (현재 사용되지 않음)
function removeLoadingMessage(loadingId) {
  // const loadingElement = document.getElementById(loadingId);
  // if (loadingElement) {
  //     loadingElement.remove();
  // }
  console.warn("removeLoadingMessage is deprecated.");
}

// 검색 결과 카드 업데이트
function updateSearchCards(searchResults) {
  const promptContainer = document.querySelector(".prompt-wrapper");
  if (!promptContainer || !searchResults || searchResults.length === 0) return;

  // 새로운 검색 결과 컨테이너 생성
  const newLinksContainer = document.createElement("div");
  newLinksContainer.className = "prompt-links-container";

  // 최대 3개까지만 표시
  const maxCardsToShow = Math.min(searchResults.length, 3);

  for (let i = 0; i < maxCardsToShow; i++) {
    const result = searchResults[i];
    const title = (result.metadata && result.metadata.title) || "제목 없음";
    // 타이틀 25자로 제한
    const shortTitle =
      title.length > 25 ? title.substring(0, 25) + "..." : title;
    const content = result.content || "";

    // content 첫 15자만 표시 (있을 경우)
    const shortContent =
      content.length > 15 ? content.substring(0, 15) + "..." : content;

    const url =
      (result.metadata && result.metadata.url) || "https://cafe.naver.com";

    // 카드 요소 생성
    const cardHTML = `
            <div class="prompt-links-cards">
                <a href="${url}" target="_blank" class="link-card">
                    <div class="card-content">
                        <div class="card-title">${shortTitle}</div>
                        <div class="card-description">${shortContent}</div>
                    </div>
                </a>
            </div>
        `;

    // 새 컨테이너에 카드 추가
    newLinksContainer.innerHTML += cardHTML;
  }

  // 각 대화 후 새 컨테이너를 추가
  promptContainer.appendChild(newLinksContainer);
}

// CSRF 토큰 가져오기 위한 함수
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// 상담 신청 모달 열기 함수 (sendConsultationRequest 함수는 HTML에 남아있으므로 호출 가능)
function openConsultationModal() {
  console.log("Opening consultation modal"); // Debug log

  // 모달이 이미 있는지 확인
  if (document.getElementById("consultation-modal")) {
    console.log("Modal already exists, showing it");
    document.getElementById("consultation-modal").style.display = "block";
    return;
  }

  console.log("Creating new modal");

  // 모달 HTML 생성
  const modalHTML = `
        <div id="consultation-modal" class="modal">
            <div class="modal-content">
                <span class="close">&times;</span>
                <h2>1:1 상담 신청</h2>
                <p>상담 요청을 위해 이메일 주소를 입력해주세요.</p>
                <form id="consultation-form">
                    <div class="form-group">
                        <label for="user-email">이메일 주소</label>
                        <input type="email" id="user-email" name="user-email" required>
                    </div>
                    <div class="form-group">
                        <label for="additional-message">추가 메시지 (선택사항)</label>
                        <textarea id="additional-message" name="additional-message" rows="4"></textarea>
                    </div>
                    <button type="submit" class="submit-btn">상담 신청하기</button>
                </form>
            </div>
        </div>
    `;

  // 모달을 body에 추가
  document.body.insertAdjacentHTML("beforeend", modalHTML);

  // Explicitly set the modal to be visible immediately after creating it
  const modal = document.getElementById("consultation-modal");
  if (modal) {
    modal.style.display = "block";
  }

  // 닫기 버튼 이벤트 리스너
  const closeButton = document.querySelector("#consultation-modal .close");
  if (closeButton) {
    closeButton.addEventListener("click", function () {
      const modal = document.getElementById("consultation-modal");
      if (modal) modal.style.display = "none";
    });
  }

  // 모달 외부 클릭시 닫기
  window.addEventListener("click", function (event) {
    const modal = document.getElementById("consultation-modal");
    if (event.target == modal) {
      modal.style.display = "none";
    }
  });

  // 폼 제출 이벤트 리스너
  const form = document.getElementById("consultation-form");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      // sendConsultationRequest 함수는 HTML 파일 내 <script>에 정의되어 있어야 함
      if (typeof sendConsultationRequest === "function") {
        sendConsultationRequest();
      } else {
        console.error("sendConsultationRequest function is not defined.");
      }
    });
  }
}

/**
 * 문서 목록을 기반으로 출처 토글 UI를 생성하고 채팅창에 렌더링합니다.
 * @param {Array<Object>} documents - 표시할 문서 객체의 배열. 각 객체는 title과 source 속성을 가져야 합니다.
 */
function renderSourceToggle(documents) {
  if (!documents || !Array.isArray(documents) || documents.length === 0) {
    console.log("No documents to display or invalid format.");
    return;
  }

  const promptContainer = document.querySelector(".prompt-wrapper");
  if (!promptContainer) {
    console.error(".prompt-wrapper element not found.");
    return;
  }

  // Create the source toggle container HTML
  const sourceToggleHTML = `
    <div class="source-toggle-container">
        <div class="toggle-area">
            <button class="toggle-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="17" height="10" viewBox="0 0 17 10" fill="none">
                <path d="M15.0547 1.03223L8.05469 8.03223L1.05469 1.03223" stroke="#617DAE" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>

            </button>
            <div class="toggle-text">
                <p>출처 보기</p>
            </div>
        </div>
        <div class="source-list-area" style="display: none;">
            ${documents
      .map(
        (doc, index) => `
                <div class="source-list-item-${index + 1}">
                    <p>[${index + 1}]</p>
                    <p>
                        <a href="${doc.source
          }" target="_blank" style="color: #617DAE; text-decoration: none;">
                            ${doc.title}
                        </a>
                    </p>
                </div>
            `
      )
      .join("")}
        </div>
    </div>`;

  // Insert the HTML
  promptContainer.insertAdjacentHTML("beforeend", sourceToggleHTML);

  // Scroll the new element into view
  const newToggle = promptContainer.lastElementChild;
  if (newToggle && newToggle.classList.contains("source-toggle-container")) {
    newToggle.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

// Function to handle message ratings
function setupRatingButtons() {
  const promptContainer = document.querySelector(".prompt-wrapper");
  if (!promptContainer) return;

  // First, mark any existing ratings from server
  document.querySelectorAll(".message-rating").forEach((container) => {
    const messagePk = container.dataset.messagePk;
    if (!messagePk) return;

    // Check if the parent element has any active class set
    const parentMessage = container.closest(".prompt-p");
    if (parentMessage && parentMessage.dataset.rating) {
      const rating = parentMessage.dataset.rating;
      const ratingBtn = container.querySelector(`.rating-${rating}`);
      if (ratingBtn) {
        ratingBtn.classList.add("active");
      }
    }
  });

  // Use event delegation for all rating buttons
  promptContainer.addEventListener("click", function (event) {
    const ratingBtn = event.target.closest(".rating-btn");
    if (!ratingBtn) return; // Not a rating button

    const ratingContainer = ratingBtn.closest(".message-rating");
    if (!ratingContainer) return;

    const messagePk = ratingContainer.dataset.messagePk;
    if (!messagePk) {
      console.error("Message ID not found for rating");
      return;
    }

    // Determine rating value
    const isGood = ratingBtn.classList.contains("rating-good");
    const isBad = ratingBtn.classList.contains("rating-bad");
    let ratingValue = null;

    // If clicking an already active button, clear the rating
    if (ratingBtn.classList.contains("active")) {
      ratingValue = null;
      ratingBtn.classList.remove("active");
    } else {
      // Otherwise set the new rating
      ratingValue = isGood ? "good" : "bad";

      // Remove active class from all buttons in this container
      ratingContainer.querySelectorAll(".rating-btn").forEach((btn) => {
        btn.classList.remove("active");
      });

      // Add active class to clicked button
      ratingBtn.classList.add("active");
    }

    // Temporarily disable buttons during API call
    ratingContainer.querySelectorAll(".rating-btn").forEach((btn) => {
      btn.classList.add("disabled");
    });

    // Send rating to API
    fetch("/api/rating/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({
        message_pk: messagePk,
        rating: ratingValue,
      }),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        console.log("Rating submitted successfully:", data);

        // Store rating in parent message element for persistence
        const parentMessage = ratingContainer.closest(".prompt-p");
        if (parentMessage) {
          parentMessage.dataset.rating = ratingValue;
        }

        // Re-enable buttons
        ratingContainer.querySelectorAll(".rating-btn").forEach((btn) => {
          btn.classList.remove("disabled");
        });
      })
      .catch((error) => {
        console.error("Error submitting rating:", error);

        // Re-enable buttons on error
        ratingContainer.querySelectorAll(".rating-btn").forEach((btn) => {
          btn.classList.remove("disabled");
        });

        // Reset the active state on error
        if (ratingValue !== null) {
          ratingBtn.classList.remove("active");
        }
      });
  });
}

// Initialize rating buttons when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  setupRatingButtons();
});

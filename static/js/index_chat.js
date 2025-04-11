// Function to adjust textarea height
function adjustTextareaHeight() {
    const inputBox = document.querySelector('.input-box-unlocked');
    if (!inputBox) return; // 요소가 없을 경우 종료

    inputBox.style.height = 'auto'; // Temporarily shrink height to calculate scrollHeight correctly
    let scrollHeight = inputBox.scrollHeight;
    const maxHeight = parseInt(window.getComputedStyle(inputBox).maxHeight, 10); // Get max-height from CSS

    // Apply scrollHeight if less than max-height, otherwise apply max-height
    if (scrollHeight <= maxHeight) {
        inputBox.style.height = scrollHeight + 'px';
    } else {
        inputBox.style.height = maxHeight + 'px';
    }
}

// 대화 메시지를 화면에 추가하는 함수
function addMessageToChat(role, content) {
    const promptContainer = document.querySelector('.prompt-wrapper');
    if (!promptContainer) return;

    if (role === 'user') {
        // 고유 ID 생성
        const messageId = 'user-message-' + Date.now();
        
        // 사용자 메시지 추가
        const userMessageHTML = `
            <div id="${messageId}" class="prompt-answer-block">
                <div class="prompt-text-area">
                    <p>${content}</p>
                </div>
            </div>
        `;
        promptContainer.insertAdjacentHTML('beforeend', userMessageHTML);
        
        // 새 메시지로 스크롤 (smoothly)
        const element = document.getElementById(messageId);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    } else if (role === 'assistant') {
        // 챗봇 응답에 고유 ID 부여
        const botMessageId = 'bot-message-' + Date.now();
        
        // 마크다운 렌더링 적용 (marked와 DOMPurify는 HTML에 로드되어 있다고 가정)
        const renderedContent = DOMPurify.sanitize(marked.parse(content));
        
        const botMessageHTML = `
            <br>
            <div id="${botMessageId}" class="prompt-p">${renderedContent}</div>
        `;
        promptContainer.insertAdjacentHTML('beforeend', botMessageHTML);
        
        // 새 메시지로 스크롤
        const element = document.getElementById(botMessageId);
         if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
}

// 로딩 메시지 추가
function addLoadingMessage() {
    const loadingId = 'loading-' + Date.now();
    const promptContainer = document.querySelector('.prompt-wrapper');
     if (!promptContainer) return loadingId; // ID 반환은 유지

    const loadingHTML = `
        <div id="${loadingId}" class="prompt-p">생성중...</div>
    `;
    promptContainer.insertAdjacentHTML('beforeend', loadingHTML);

    // 새 메시지로 스크롤 (smoothly)
    const element = document.getElementById(loadingId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    return loadingId;
}

// 로딩 메시지 제거
function removeLoadingMessage(loadingId) {
    const loadingElement = document.getElementById(loadingId);
    if (loadingElement) {
        loadingElement.remove();
    }
}

// 검색 결과 카드 업데이트
function updateSearchCards(searchResults) {
     const promptContainer = document.querySelector('.prompt-wrapper');
    if (!promptContainer || !searchResults || searchResults.length === 0) return;

    // 새로운 검색 결과 컨테이너 생성
    const newLinksContainer = document.createElement('div');
    newLinksContainer.className = 'prompt-links-container';
    
    // 최대 3개까지만 표시
    const maxCardsToShow = Math.min(searchResults.length, 3);
    
    for (let i = 0; i < maxCardsToShow; i++) {
        const result = searchResults[i];
        const title = result.metadata && result.metadata.title || '제목 없음';
        // 타이틀 25자로 제한
        const shortTitle = title.length > 25
            ? title.substring(0, 25) + '...' 
            : title;
        const content = result.content || '';
        
        // content 첫 15자만 표시 (있을 경우)
        const shortContent = content.length > 15 
            ? content.substring(0, 15) + '...' 
            : content;
        
        const url = result.metadata && result.metadata.url || 'https://cafe.naver.com';
        
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
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
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
    if (document.getElementById('consultation-modal')) {
        console.log("Modal already exists, showing it");
        document.getElementById('consultation-modal').style.display = 'block';
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
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Explicitly set the modal to be visible immediately after creating it
    const modal = document.getElementById('consultation-modal');
    if (modal) {
       modal.style.display = 'block';
    }
    
    // 닫기 버튼 이벤트 리스너
    const closeButton = document.querySelector('#consultation-modal .close');
    if (closeButton) {
        closeButton.addEventListener('click', function() {
            const modal = document.getElementById('consultation-modal');
            if(modal) modal.style.display = 'none';
        });
    }
    
    // 모달 외부 클릭시 닫기
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('consultation-modal');
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    });
    
    // 폼 제출 이벤트 리스너
    const form = document.getElementById('consultation-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            // sendConsultationRequest 함수는 HTML 파일 내 <script>에 정의되어 있어야 함
            if (typeof sendConsultationRequest === 'function') {
                sendConsultationRequest();
            } else {
                console.error('sendConsultationRequest function is not defined.');
            }
        });
    }
}

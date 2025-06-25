(function(window) {
    'use strict';

    let popup = null; 

    // 팝업 제거 함수
    function removePopup() {
        if (popup) {
            popup.remove();
            popup = null;
        }
    }

    /**
     * iframe 내에서 텍스트 선택 기능을 초기화하는 함수
     * @param {Window} iframeWindow - 대상 iframe의 window 객체
     */
    function initTextSelection(iframeWindow) {
        const doc = iframeWindow.document;

        // 이전 이벤트 리스너가 있다면 제거하여 중복 실행 방지
        doc.removeEventListener('mouseup', handleMouseUp);
        doc.removeEventListener('mousedown', handleMouseDown);
        iframeWindow.removeEventListener('scroll', removePopup, true);

        // 사용자가 텍스트 선택을 마쳤을 때 호출될 함수
        function handleMouseUp() {
            // selection 객체가 확정될 시간을 벌기 위해 짧은 지연 후 실행
            setTimeout(() => {
                const selection = iframeWindow.getSelection();
                const selectedText = selection.toString().trim();
                
                removePopup(); // 기존 팝업이 있다면 먼저 제거

                if (selectedText.length > 0) {
                    const range = selection.getRangeAt(0);
                    const rect = range.getBoundingClientRect();

                    // 팝업 요소 생성
                    popup = doc.createElement('div');
                    popup.className = 'selection-popup';
                    
                    // "채팅에 추가" 버튼 생성
                    const button = doc.createElement('button');
                    button.textContent = '채팅에 추가';
                    popup.appendChild(button);

                    // iframe 내부의 스크롤 위치를 고려하여 팝업 좌표 설정
                    popup.style.left = `${rect.left + iframeWindow.scrollX}px`;
                    popup.style.top = `${rect.bottom + iframeWindow.scrollY + 5}px`;

                    doc.body.appendChild(popup);

                    // 버튼 클릭 시 부모 창으로 메시지 전송
                    button.addEventListener('click', function(e) {
                        e.stopPropagation(); // mousedown 이벤트 전파 방지
                        window.parent.postMessage({
                            type: 'STW_ADD_TO_CHAT',
                            text: selectedText
                        }, '*'); // 보안을 위해 실제 운영 환경에서는 '*' 대신 특정 origin을 사용해야 합니다.
                        removePopup();
                    });
                }
            }, 10);
        }

        // iframe 내에서 마우스 클릭 시 팝업을 제거하는 로직
        function handleMouseDown(event) {
            if (popup && !popup.contains(event.target)) {
                 setTimeout(() => {
                    if (iframeWindow.getSelection().toString().trim() === '') {
                        removePopup();
                    }
                }, 0);
            }
        }

        // 이벤트 리스너 등록
        doc.addEventListener('mouseup', handleMouseUp);
        doc.addEventListener('mousedown', handleMouseDown);
        // scroll 이벤트는 캡처 단계에서 감지하여 빠르게 팝업을 제거
        iframeWindow.addEventListener('scroll', removePopup, true); 
    }
    
    // 외부에서 접근할 수 있도록 window 객체에 init 함수 노출
    window.TextSelection = {
        init: initTextSelection
    };

})(window); 
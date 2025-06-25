document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.sidebar-main-content');
    const toggleBtn = document.querySelector('.sidebar-toggle-btn');
    const contentContainer = document.querySelector('.sidebar-content-container');
    const loadingIndicator = document.querySelector('.sidebar-loading-indicator');

    let page = 1;
    let isLoading = false;
    let hasNextPage = true;

    // 1. Sidebar Toggle
    toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('sidebar-collapsed');
        if (sidebar.classList.contains('collapsed')) {
            toggleBtn.textContent = '▶';
        } else {
            toggleBtn.textContent = '◀';
        }
    });

    // 2. Data Fetching function
    async function fetchContents() {
        if (isLoading || !hasNextPage) return;

        isLoading = true;
        loadingIndicator.style.display = 'block';

        try {
            const response = await fetch(`/contents/api/notion-content-list/?page=${page}`);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            const data = await response.json();

            if (data.contents && data.contents.length > 0) {
                data.contents.forEach(content => {
                    if(content.thumbnail_url) {
                        const a = document.createElement('a');
                        a.href = content.view_url;
                        const img = document.createElement('img');
                        img.src = content.thumbnail_url;
                        img.alt = content.title;
                        a.appendChild(img);
                        contentContainer.appendChild(a);
                    }
                });
                page++;
            }
            
            hasNextPage = data.has_next;

            if (!hasNextPage) {
                const endMessage = document.createElement('p');
                endMessage.textContent = 'end';
                endMessage.style.textAlign = 'center';
                contentContainer.appendChild(endMessage);
            }

        } catch (error) {
            console.error('Failed to fetch contents:', error);
            const errorMessage = document.createElement('p');
            errorMessage.textContent = 'Error loading content.';
            errorMessage.style.color = 'red';
            contentContainer.appendChild(errorMessage);
        } finally {
            isLoading = false;
            loadingIndicator.style.display = 'none';
        }
    }

    // 3. Infinite Scrolling
    contentContainer.addEventListener('scroll', () => {
        // Check if the user is near the right edge of the content
        const { scrollLeft, scrollWidth, clientWidth } = contentContainer;
        if (scrollLeft + clientWidth >= scrollWidth - 5) { // 5px buffer
            fetchContents();
        }
    });

    // 4. Initial Load
    fetchContents();

    // 5. Handle clicks on content images to load in iframe and auto-scale it
    const iframe = document.getElementById('content-iframe');
    const iframeContainer = document.querySelector('.sidebar-iframe-container');

    iframe.addEventListener('load', function() {
        if (!iframe.src || iframe.src === 'about:blank') {
            return; // Do nothing for empty iframe
        }

        try {
            const iframeWindow = iframe.contentWindow;
            const iframeDoc = iframeWindow.document;

            // 1. 팝업을 위한 CSS 스타일을 iframe에 동적으로 주입합니다.
            // 사이트 테마와 어울리도록 스타일을 조정했습니다.
            const style = iframeDoc.createElement('style');
            style.textContent = `
                .selection-popup {
                    position: absolute;
                    background-color: #617dae;
                    color: white;
                    border: 1px solid #47639A;
                    padding: 5px 10px;
                    border-radius: 5px;
                    cursor: default;
                    box-shadow: 2px 2px 8px rgba(0,0,0,0.25);
                    z-index: 9999;
                    font-size: 14px;
                    font-family: sans-serif;
                }
                .selection-popup button {
                    background-color: transparent;
                    color: white;
                    border: none;
                    padding: 0;
                    margin: 0;
                    font-size: 14px;
                    cursor: pointer;
                    font-family: inherit;
                }
                .selection-popup button:hover {
                    text-decoration: underline;
                }
            `;
            iframeDoc.head.appendChild(style);

            // 2. iframe 내부에서 텍스트 선택 기능을 초기화합니다.
            if (window.TextSelection && typeof window.TextSelection.init === 'function') {
                window.TextSelection.init(iframeWindow);
            }

            // 3. 기존의 iframe 자동 크기 조절 로직을 실행합니다.
            const contentWidth = iframeDoc.body.scrollWidth;
            const containerWidth = iframeContainer.clientWidth;

            if (contentWidth > 0 && containerWidth > 0 && contentWidth > containerWidth) {
                const scale = containerWidth / contentWidth;
                iframe.style.transform = `scale(${scale})`;
                iframe.style.width = `${100 / scale}%`;
                iframe.style.height = `${100 / scale}%`;
            } else {
                // If content is smaller than container, no need to scale down
                iframe.style.transform = 'scale(1)';
                iframe.style.width = `100%`;
                iframe.style.height = `100%`;
            }
        } catch (e) {
            console.error("Could not access iframe content for scaling. Likely a cross-origin issue.", e);
        }
    });

    contentContainer.addEventListener('click', function(event) {
        const link = event.target.closest('a');

        if (link) {
            event.preventDefault(); // Prevent navigating to a new page
            
            // Reset styles before loading new content
            iframe.style.transform = 'scale(1)';
            iframe.style.width = '100%';
            iframe.style.height = '100%';

            iframe.src = link.href;
        }
    });
});

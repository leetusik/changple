'use client';

import { useSidebarStore, getSidebarWidth } from '@/stores/sidebar-store';
import { useUIStore } from '@/stores/ui-store';

// Custom SVG icons matching the original design
function HistoryIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 12 12" fill="currentColor">
      <path d="M1.37395 2.66434C1.31892 2.43637 1.11938 2.24749 0.870849 2.3233C0.622319 2.3991 0.509247 2.64075 0.573651 2.99908L0.939591 4.92877C1.0681 5.17307 1.37005 5.26709 1.6144 5.13873L3.25117 4.56364C3.69087 4.43445 3.75986 4.24873 3.69087 3.97442C3.62273 3.72011 3.33729 3.67936 3.01607 3.76543L2.3424 3.97442C2.81413 3.18266 3.3443 2.63023 3.87807 2.3233C4.84474 1.76745 5.98564 1.59702 7.0724 1.84674C8.15916 2.09651 9.11138 2.74789 9.73842 3.66998C10.3654 4.59205 10.6214 5.71697 10.4542 6.81939C10.2869 7.92194 9.70847 8.92065 8.83608 9.61529C7.96371 10.3098 6.8611 10.6494 5.74916 10.5655C4.6373 10.4815 3.5982 9.98071 2.83998 9.16314C2.08168 8.34547 1.66029 7.55256 1.66029 6.4374C1.66029 6.16125 1.43644 5.9374 1.16029 5.9374C0.884152 5.9374 0.660295 6.16125 0.660295 6.4374C0.660295 7.80465 1.17693 8.84028 2.10658 9.84283C3.0363 10.8453 4.3106 11.4596 5.67397 11.5626C7.03743 11.6654 8.38944 11.2492 9.45912 10.3975C10.5288 9.54579 11.2374 8.32166 11.4425 6.96978C11.6477 5.6179 11.3344 4.23821 10.5656 3.10748C9.79679 1.97697 8.62939 1.17844 7.29701 0.872126C5.9644 0.565849 4.56442 0.774515 3.37905 1.45611C2.51528 1.95287 2.01845 2.63221 1.54962 3.49417L1.37395 2.66434Z" />
      <path d="M5.375 3.42188C5.375 3.14573 5.59886 2.92188 5.875 2.92188C6.15114 2.92188 6.375 3.14573 6.375 3.42188V6.36719L7.95508 7.95703C8.14983 8.1528 8.14889 8.46931 7.95312 8.66406C7.75734 8.85862 7.44079 8.85781 7.24609 8.66211L5.375 6.78125V3.42188Z" />
    </svg>
  );
}

function BackIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 12H5" />
      <polyline points="12 19 5 12 12 5" />
    </svg>
  );
}

function ExpandIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" stroke="currentColor" viewBox="0 0 22 23" fill="none">
      <path d="M15.1717 1.22656V21.2266M15.1717 21.2266H16.9375C19.1466 21.2266 20.9375 19.4357 20.9375 17.2266V5.22656C20.9375 3.01742 19.1466 1.22656 16.9375 1.22656H4.9375C2.72836 1.22656 0.9375 3.01742 0.9375 5.22656V17.2266C0.9375 19.4357 2.72836 21.2266 4.9375 21.2266H15.1717Z" strokeWidth="1.6"/>
    </svg>
  );
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 17 15" fill="currentColor">
      <path fillRule="evenodd" clipRule="evenodd" d="M1.17969 0.890625C1.4449 0.890625 1.69926 0.995982 1.88679 1.18352C2.07433 1.37105 2.17969 1.62541 2.17969 1.89062V13.8906C2.17969 14.1558 2.07433 14.4102 1.88679 14.5977C1.69926 14.7853 1.4449 14.8906 1.17969 14.8906C0.914471 14.8906 0.660117 14.7853 0.472581 14.5977C0.285044 14.4102 0.179688 14.1558 0.179688 13.8906V1.89062C0.179688 1.62541 0.285044 1.37105 0.472581 1.18352C0.660117 0.995982 0.914471 0.890625 1.17969 0.890625ZM8.88669 4.18363C9.07416 4.37115 9.17947 4.62546 9.17947 4.89062C9.17947 5.15579 9.07416 5.4101 8.88669 5.59762L7.59369 6.89062H15.1797C15.4449 6.89062 15.6993 6.99598 15.8868 7.18352C16.0743 7.37105 16.1797 7.62541 16.1797 7.89062C16.1797 8.15584 16.0743 8.4102 15.8868 8.59773C15.6993 8.78527 15.4449 8.89062 15.1797 8.89062H7.59369L8.88669 10.1836C9.06885 10.3722 9.16964 10.6248 9.16736 10.887C9.16508 11.1492 9.05991 11.4 8.87451 11.5854C8.6891 11.7709 8.43829 11.876 8.17609 11.8783C7.91389 11.8806 7.66129 11.7798 7.47269 11.5976L4.47269 8.59762C4.28522 8.4101 4.1799 8.15579 4.1799 7.89062C4.1799 7.62546 4.28522 7.37115 4.47269 7.18363L7.47269 4.18363C7.66022 3.99615 7.91452 3.89084 8.17969 3.89084C8.44485 3.89084 8.69916 3.99615 8.88669 4.18363Z" />
    </svg>
  );
}

function OpenIcon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 17 15" fill="currentColor">
      <path fillRule="evenodd" clipRule="evenodd" d="M15.2969 0.890625C15.0317 0.890625 14.7773 0.995982 14.5898 1.18352C14.4022 1.37105 14.2969 1.62541 14.2969 1.89062V13.8906C14.2969 14.1558 14.4022 14.4102 14.5898 14.5977C14.7773 14.7853 15.0317 14.8906 15.2969 14.8906C15.5621 14.8906 15.8164 14.7853 16.004 14.5977C16.1915 14.4102 16.2969 14.1558 16.2969 13.8906V1.89062C16.2969 1.62541 16.1915 1.37105 16.004 1.18352C15.8164 0.995982 15.5621 0.890625 15.2969 0.890625ZM7.58988 4.18363C7.4024 4.37115 7.29709 4.62546 7.29709 4.89062C7.29709 5.15579 7.4024 5.4101 7.58988 5.59762L8.88288 6.89062H1.29688C1.03166 6.89062 0.777304 6.99598 0.589767 7.18352C0.402231 7.37105 0.296875 7.62541 0.296875 7.89062C0.296875 8.15584 0.402231 8.4102 0.589767 8.59773C0.777304 8.78527 1.03166 8.89062 1.29688 8.89062H8.88288L7.58988 10.1836C7.40772 10.3722 7.30692 10.6248 7.3092 10.887C7.31148 11.1492 7.41665 11.4 7.60206 11.5854C7.78746 11.7709 8.03828 11.876 8.30047 11.8783C8.56267 11.8806 8.81527 11.7798 9.00387 11.5976L12.0039 8.59762C12.1913 8.4101 12.2967 8.15579 12.2967 7.89062C12.2967 7.62546 12.1913 7.37115 12.0039 7.18363L9.00387 4.18363C8.81635 3.99615 8.56204 3.89084 8.29688 3.89084C8.03171 3.89084 7.7774 3.99615 7.58988 4.18363Z" />
    </svg>
  );
}

interface SidebarProps {
  children?: React.ReactNode;
  onHistoryClick?: () => void;
  onBackClick?: () => void;
  showBackButton?: boolean;
}

export function Sidebar({
  children,
  onHistoryClick,
  onBackClick,
  showBackButton = false,
}: SidebarProps) {
  const { state, toggle, expand, collapse } = useSidebarStore();
  const { sidebarView } = useUIStore();

  const isCollapsed = state === 'collapsed';
  const isExpanded = state === 'expanded';
  const width = getSidebarWidth(state);

  // Button visibility based on current view (matching old codebase behavior)
  const showHistoryButton = sidebarView === 'content'; // Only show on content list
  const showExpandButton = sidebarView === 'details'; // Only show on content details

  return (
    <aside
      className="relative bg-white h-full rounded-md p-1.5 flex flex-col transition-all duration-600 ease-in-out overflow-hidden"
      style={{
        width,
        minWidth: isCollapsed ? '100px' : '300px',
        maxWidth: isExpanded ? '1000px' : isCollapsed ? '100px' : '600px',
        flex: `0 0 ${width}`,
      }}
    >
      {/* Collapsed state - show open button */}
      {isCollapsed ? (
        <div className="flex flex-col items-center pt-4">
          <button
            onClick={() => toggle()}
            className="flex flex-col items-center justify-center bg-white w-9 h-9 border border-grey-2 rounded-full cursor-pointer hover:bg-btn-hover"
            aria-label="사이드바 열기"
          >
            <OpenIcon className="w-4 h-4 text-grey-4" />
          </button>
        </div>
      ) : (
        <>
          {/* Sidebar header buttons */}
          <div className="flex items-center justify-between w-full h-11 mt-2.5 px-1.5">
            {/* Left button group */}
            <div className="flex items-center gap-1">
              {/* History button - only on content list */}
              {showHistoryButton && (
                <button
                  onClick={onHistoryClick}
                  className="flex justify-center items-center bg-white w-9 h-9 rounded-full border border-grey-2 cursor-pointer hover:bg-btn-hover"
                  aria-label="히스토리"
                >
                  <HistoryIcon className="w-5 h-5 text-grey-4" />
                </button>
              )}

              {/* Back button - shown on history and details views */}
              {showBackButton && (
                <button
                  onClick={onBackClick}
                  className="flex justify-center items-center bg-white w-9 h-9 rounded-full border border-grey-2 cursor-pointer hover:bg-btn-hover"
                  aria-label="뒤로가기"
                >
                  <BackIcon className="w-5 h-5 text-grey-4" />
                </button>
              )}
            </div>

            {/* Right button group */}
            <div className="flex items-center gap-1">
              {/* Expand button - only on content details */}
              {showExpandButton && (
                <button
                  onClick={() => expand()}
                  className="flex justify-center items-center bg-white w-9 h-9 rounded-full border border-grey-2 cursor-pointer hover:bg-btn-hover"
                  aria-label={isExpanded ? '축소' : '확장'}
                >
                  <ExpandIcon className={`w-5 h-5 text-grey-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                </button>
              )}

              {/* Close button - always visible */}
              <button
                onClick={() => collapse()}
                className="flex justify-center items-center bg-white w-9 h-9 rounded-full border border-grey-2 cursor-pointer hover:bg-btn-hover"
                aria-label="사이드바 닫기"
              >
                <CloseIcon className="w-4 h-4 text-grey-4" />
              </button>
            </div>
          </div>

          {/* Sidebar content */}
          <div className="flex-1 overflow-y-auto overflow-x-hidden mt-4 px-1.5 hide-scrollbar">
            {children}
          </div>
        </>
      )}
    </aside>
  );
}

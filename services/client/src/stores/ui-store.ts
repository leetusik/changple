import { create } from 'zustand';

type SidebarView = 'content' | 'history' | 'details';

interface UIState {
  // Modal visibility
  profileModalOpen: boolean;
  loginRequiredModalOpen: boolean;

  // Sidebar view state
  sidebarView: SidebarView;
  selectedContentDetailId: number | null;

  // Modal actions
  openProfileModal: () => void;
  closeProfileModal: () => void;
  openLoginRequiredModal: () => void;
  closeLoginRequiredModal: () => void;

  // Sidebar view actions
  setSidebarView: (view: SidebarView) => void;
  showContentList: () => void;
  showHistory: () => void;
  showContentDetails: (contentId: number) => void;
}

export const useUIStore = create<UIState>((set) => ({
  // Initial state
  profileModalOpen: false,
  loginRequiredModalOpen: false,
  sidebarView: 'content',
  selectedContentDetailId: null,

  // Modal actions
  openProfileModal: () => set({ profileModalOpen: true }),
  closeProfileModal: () => set({ profileModalOpen: false }),
  openLoginRequiredModal: () => set({ loginRequiredModalOpen: true }),
  closeLoginRequiredModal: () => set({ loginRequiredModalOpen: false }),

  // Sidebar view actions
  setSidebarView: (view) => set({ sidebarView: view }),
  showContentList: () => set({ sidebarView: 'content', selectedContentDetailId: null }),
  showHistory: () => set({ sidebarView: 'history' }),
  showContentDetails: (contentId) =>
    set({ sidebarView: 'details', selectedContentDetailId: contentId }),
}));

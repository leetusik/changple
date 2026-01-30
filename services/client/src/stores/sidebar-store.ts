import { create } from 'zustand';

export type SidebarState = 'collapsed' | 'normal' | 'expanded';

interface SidebarStore {
  state: SidebarState;
  isOpen: boolean;
  setState: (state: SidebarState) => void;
  toggle: () => void;
  expand: () => void;
  collapse: () => void;
  close: () => void;
  open: () => void;
}

export const useSidebarStore = create<SidebarStore>((set) => ({
  state: 'normal',
  isOpen: true,

  setState: (state) => set({ state }),

  toggle: () =>
    set((store) => {
      if (store.state === 'collapsed') {
        return { state: 'normal' };
      }
      return { state: 'collapsed' };
    }),

  expand: () =>
    set((store) => {
      if (store.state === 'expanded') {
        return { state: 'normal' };
      }
      return { state: 'expanded' };
    }),

  collapse: () => set({ state: 'collapsed' }),

  close: () => set({ isOpen: false, state: 'collapsed' }),

  open: () => set({ isOpen: true, state: 'normal' }),
}));

/**
 * Get sidebar width based on state
 */
export function getSidebarWidth(state: SidebarState): string {
  switch (state) {
    case 'collapsed':
      return '100px';
    case 'normal':
      return '600px';
    case 'expanded':
      return '1000px';
    default:
      return '600px';
  }
}

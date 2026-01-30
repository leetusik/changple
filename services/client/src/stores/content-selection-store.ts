import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { SelectedContent } from '@/types';

interface ContentSelectionState {
  selectedIds: number[];
  selectedInfo: SelectedContent[];
  toggle: (content: SelectedContent) => void;
  add: (content: SelectedContent) => void;
  remove: (id: number) => void;
  clear: () => void;
  isSelected: (id: number) => boolean;
}

export const useContentSelectionStore = create<ContentSelectionState>()(
  persist(
    (set, get) => ({
      selectedIds: [],
      selectedInfo: [],

      toggle: (content) =>
        set((state) => {
          const exists = state.selectedIds.includes(content.id);
          if (exists) {
            return {
              selectedIds: state.selectedIds.filter((id) => id !== content.id),
              selectedInfo: state.selectedInfo.filter((c) => c.id !== content.id),
            };
          }
          return {
            selectedIds: [...state.selectedIds, content.id],
            selectedInfo: [...state.selectedInfo, content],
          };
        }),

      add: (content) =>
        set((state) => {
          if (state.selectedIds.includes(content.id)) {
            return state; // Already selected
          }
          return {
            selectedIds: [...state.selectedIds, content.id],
            selectedInfo: [...state.selectedInfo, content],
          };
        }),

      remove: (id) =>
        set((state) => ({
          selectedIds: state.selectedIds.filter((i) => i !== id),
          selectedInfo: state.selectedInfo.filter((c) => c.id !== id),
        })),

      clear: () => set({ selectedIds: [], selectedInfo: [] }),

      isSelected: (id) => get().selectedIds.includes(id),
    }),
    {
      name: 'content-selection',
      // Only persist selectedIds and selectedInfo
      partialize: (state) => ({
        selectedIds: state.selectedIds,
        selectedInfo: state.selectedInfo,
      }),
    }
  )
);

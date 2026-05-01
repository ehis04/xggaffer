import { useEffect } from 'react';

interface UseTacticsKeyboardShortcutsOptions {
  enabled?: boolean;
  hasDraft: boolean;
  hasSelectedDeletableItem: boolean;
  hasAnySelection: boolean;
  canUndo: boolean;
  canRedo: boolean;
  canSave: boolean;
  isPlaybackActive: boolean;
  isDeletingItem: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onDeleteSelectedItem: () => void;
  onCancelDraft: () => void;
  onDeselect: () => void;
  onSave: () => void;
}

const isTypingElement = (target: EventTarget | null): boolean => {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  const tagName = target.tagName.toLowerCase();

  return (
    tagName === 'input' ||
    tagName === 'textarea' ||
    tagName === 'select' ||
    target.isContentEditable
  );
};

export const useTacticsKeyboardShortcuts = ({
  enabled = true,
  hasDraft,
  hasSelectedDeletableItem,
  hasAnySelection,
  canUndo,
  canRedo,
  canSave,
  isPlaybackActive,
  isDeletingItem,
  onUndo,
  onRedo,
  onDeleteSelectedItem,
  onCancelDraft,
  onDeselect,
  onSave,
}: UseTacticsKeyboardShortcutsOptions) => {
  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (isTypingElement(event.target)) {
        return;
      }

      const isMetaOrCtrl = event.metaKey || event.ctrlKey;
      const key = event.key.toLowerCase();

      if (event.key === 'Escape') {
        if (hasDraft) {
          event.preventDefault();
          onCancelDraft();
          return;
        }

        if (hasAnySelection) {
          event.preventDefault();
          onDeselect();
        }

        return;
      }

      if (
        (event.key === 'Delete' || event.key === 'Backspace') &&
        !isPlaybackActive &&
        !isDeletingItem &&
        hasSelectedDeletableItem
      ) {
        event.preventDefault();
        onDeleteSelectedItem();
        return;
      }

      if (!isMetaOrCtrl) {
        return;
      }

      if (key === 'z' && event.shiftKey) {
        if (canRedo && !isPlaybackActive) {
          event.preventDefault();
          onRedo();
        }
        return;
      }

      if (key === 'z') {
        if (canUndo && !isPlaybackActive) {
          event.preventDefault();
          onUndo();
        }
        return;
      }

      if (key === 'y') {
        if (canRedo && !isPlaybackActive) {
          event.preventDefault();
          onRedo();
        }
        return;
      }

      if (key === 's') {
        if (canSave && !isPlaybackActive) {
          event.preventDefault();
          onSave();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    enabled,
    hasDraft,
    hasSelectedDeletableItem,
    hasAnySelection,
    canUndo,
    canRedo,
    canSave,
    isPlaybackActive,
    isDeletingItem,
    onUndo,
    onRedo,
    onDeleteSelectedItem,
    onCancelDraft,
    onDeselect,
    onSave,
  ]);
};

export default useTacticsKeyboardShortcuts;
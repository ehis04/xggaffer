import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import PitchCanvas from '../PitchCanvas';
import type { TacticsBoardFrame, TacticsBoardItem, TacticsDraftItem } from '../../../types/tactics';

const createPlayerItem = (overrides: Partial<TacticsBoardItem> = {}): TacticsBoardItem => ({
  id: 1,
  frame: 10,
  item_type: 'player',
  team_side: 'home',
  stable_id: 'player-1',
  linked_player: null,
  label: '',
  shirt_number: 9,
  position_label: 'ST',
  x: 50,
  y: 80,
  end_x: null,
  end_y: null,
  width: null,
  height: null,
  rotation: 0,
  z_index: 0,
  style: {},
  player_summary: null,
  ...overrides,
}) as TacticsBoardItem;

const createBallItem = (overrides: Partial<TacticsBoardItem> = {}): TacticsBoardItem => ({
  id: 2,
  frame: 10,
  item_type: 'ball',
  team_side: 'neutral',
  stable_id: 'ball-2',
  linked_player: null,
  label: '',
  shirt_number: null,
  position_label: '',
  x: 48,
  y: 55,
  end_x: null,
  end_y: null,
  width: null,
  height: null,
  rotation: 0,
  z_index: 1,
  style: {},
  player_summary: null,
  ...overrides,
}) as TacticsBoardItem;

const createArrowItem = (overrides: Partial<TacticsBoardItem> = {}): TacticsBoardItem => ({
  id: 3,
  frame: 10,
  item_type: 'arrow',
  team_side: 'neutral',
  stable_id: 'arrow-3',
  linked_player: null,
  label: '',
  shirt_number: null,
  position_label: '',
  x: 20,
  y: 20,
  end_x: 40,
  end_y: 40,
  width: null,
  height: null,
  rotation: 0,
  z_index: 2,
  style: {},
  player_summary: null,
  ...overrides,
}) as TacticsBoardItem;

const createLineItem = (overrides: Partial<TacticsBoardItem> = {}): TacticsBoardItem => ({
  id: 4,
  frame: 10,
  item_type: 'line',
  team_side: 'neutral',
  stable_id: 'line-4',
  linked_player: null,
  label: '',
  shirt_number: null,
  position_label: '',
  x: 60,
  y: 20,
  end_x: 70,
  end_y: 35,
  width: null,
  height: null,
  rotation: 0,
  z_index: 3,
  style: {},
  player_summary: null,
  ...overrides,
}) as TacticsBoardItem;

const createZoneItem = (overrides: Partial<TacticsBoardItem> = {}): TacticsBoardItem => ({
  id: 5,
  frame: 10,
  item_type: 'zone',
  team_side: 'neutral',
  stable_id: 'zone-5',
  linked_player: null,
  label: '',
  shirt_number: null,
  position_label: '',
  x: 10,
  y: 10,
  end_x: null,
  end_y: null,
  width: 20,
  height: 15,
  rotation: 0,
  z_index: 4,
  style: {},
  player_summary: null,
  ...overrides,
}) as TacticsBoardItem;

const createTextItem = (overrides: Partial<TacticsBoardItem> = {}): TacticsBoardItem => ({
  id: 6,
  frame: 10,
  item_type: 'text',
  team_side: 'neutral',
  stable_id: 'text-6',
  linked_player: null,
  label: 'Press high',
  shirt_number: null,
  position_label: '',
  x: 35,
  y: 60,
  end_x: null,
  end_y: null,
  width: null,
  height: null,
  rotation: 0,
  z_index: 5,
  style: {},
  player_summary: null,
  ...overrides,
}) as TacticsBoardItem;

const createFrame = (items: TacticsBoardItem[]): TacticsBoardFrame => ({
  id: 10,
  board: 1,
  frame_index: 0,
  label: '',
  duration_ms: 1500,
  notes: '',
  items,
});

describe('PitchCanvas', () => {
  it('renders a mixed tactical scene with all supported Phase D item types', () => {
    render(
      <PitchCanvas
        frame={createFrame([
          createPlayerItem(),
          createBallItem(),
          createArrowItem(),
          createLineItem(),
          createZoneItem(),
          createTextItem(),
        ])}
      />
    );

    expect(screen.getByLabelText(/Player marker/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Ball marker')).toBeInTheDocument();
    expect(screen.getByLabelText('Arrow annotation')).toBeInTheDocument();
    expect(screen.getByLabelText('Line annotation')).toBeInTheDocument();
    expect(screen.getByLabelText('Zone annotation')).toBeInTheDocument();
    expect(screen.getByLabelText(/Text annotation/i)).toBeInTheDocument();
  });

  it('calls onSelectItem when a non-player annotation is clicked', () => {
    const onSelectItem = vi.fn();

    render(
      <PitchCanvas
        frame={createFrame([createBallItem()])}
        onSelectItem={onSelectItem}
      />
    );

    fireEvent.pointerDown(screen.getByLabelText('Ball marker'));
    expect(onSelectItem).toHaveBeenCalledWith(2);
  });

  it('calls onStartDirectionalDraft on first background click in arrow mode', () => {
    const onStartDirectionalDraft = vi.fn();

    render(
      <PitchCanvas
        frame={createFrame([])}
        activeTool="arrow"
        onStartDirectionalDraft={onStartDirectionalDraft}
      />
    );

    fireEvent.pointerDown(screen.getByRole('img'));
    expect(onStartDirectionalDraft).toHaveBeenCalledTimes(1);
  });

  it('calls onCreatePointItem when background is used in ball mode', () => {
    const onCreatePointItem = vi.fn();

    render(
      <PitchCanvas
        frame={createFrame([])}
        activeTool="ball"
        onCreatePointItem={onCreatePointItem}
      />
    );

    fireEvent.pointerDown(screen.getByRole('img'));
    expect(onCreatePointItem).toHaveBeenCalledTimes(1);
    expect(onCreatePointItem.mock.calls[0][0]).toBe('ball');
  });

  it('renders a directional draft preview while an arrow draft exists', () => {
    const draftItem: TacticsDraftItem = {
      tool: 'arrow',
      startX: 10,
      startY: 15,
      currentX: 30,
      currentY: 45,
    };

    render(
      <PitchCanvas
        frame={createFrame([])}
        activeTool="arrow"
        draftItem={draftItem}
      />
    );

    expect(screen.getByLabelText('Arrow annotation')).toBeInTheDocument();
  });

  it('renders a zone draft preview while a zone draft exists', () => {
    const draftItem: TacticsDraftItem = {
      tool: 'zone',
      startX: 20,
      startY: 20,
      currentX: 35,
      currentY: 40,
    };

    render(
      <PitchCanvas
        frame={createFrame([])}
        activeTool="zone"
        draftItem={draftItem}
      />
    );

    expect(screen.getByLabelText('Zone annotation')).toBeInTheDocument();
  });
});
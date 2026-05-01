import { describe, expect, it } from 'vitest';
import type { TacticsBoardFrame, TacticsBoardItem } from '../../types/tactics';
import { interpolateFrames, matchItemsByStableId } from '../interpolateFrames';

const createPlayerItem = (
  overrides: Partial<TacticsBoardItem> = {}
): TacticsBoardItem =>
  ({
    id: 1,
    frame: 11,
    item_type: 'player',
    team_side: 'home',
    stable_id: 'stable-player',
    linked_player: null,
    label: '',
    shirt_number: 8,
    position_label: 'CM',
    x: 20,
    y: 30,
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

const createArrowItem = (
  overrides: Partial<TacticsBoardItem> = {}
): TacticsBoardItem =>
  ({
    id: 2,
    frame: 11,
    item_type: 'arrow',
    team_side: 'neutral',
    stable_id: 'stable-arrow',
    linked_player: null,
    label: 'Run',
    shirt_number: null,
    position_label: '',
    x: 10,
    y: 15,
    end_x: 30,
    end_y: 45,
    width: null,
    height: null,
    rotation: 0,
    z_index: 1,
    style: { stroke_width: 3 },
    player_summary: null,
    ...overrides,
  }) as TacticsBoardItem;

const createFrame = (
  items: TacticsBoardItem[],
  frameIndex = 0
): TacticsBoardFrame => ({
  id: 11 + frameIndex,
  board: 1,
  frame_index: frameIndex,
  label: `Frame ${frameIndex}`,
  duration_ms: 1500,
  notes: '',
  items,
});

describe('matchItemsByStableId', () => {
  it('matches source and target items using stable_id only', () => {
    const sourceFrame = createFrame([
      createPlayerItem({ id: 101, stable_id: 'same-stable-id', x: 10 }),
    ]);

    const targetFrame = createFrame(
      [createPlayerItem({ id: 202, stable_id: 'same-stable-id', x: 80 })],
      1
    );

    const matches = matchItemsByStableId(sourceFrame.items, targetFrame.items);

    expect(matches).toHaveLength(1);
    expect(matches[0].sourceItem?.id).toBe(101);
    expect(matches[0].targetItem?.id).toBe(202);
  });
});

describe('interpolateFrames', () => {
  it('returns source state at progress 0', () => {
    const sourceFrame = createFrame([
      createPlayerItem({ x: 20, y: 30 }),
      createArrowItem({ x: 10, y: 15, end_x: 30, end_y: 45 }),
    ]);
    const targetFrame = createFrame(
      [
        createPlayerItem({ id: 3, stable_id: 'stable-player', x: 80, y: 90 }),
        createArrowItem({
          id: 4,
          stable_id: 'stable-arrow',
          x: 50,
          y: 55,
          end_x: 70,
          end_y: 85,
          label: 'Next run',
        }),
      ],
      1
    );

    const result = interpolateFrames(sourceFrame, targetFrame, 0);

    const player = result.items.find((item) => item.stable_id === 'stable-player');
    const arrow = result.items.find((item) => item.stable_id === 'stable-arrow');

    expect(player?.x).toBe(20);
    expect(player?.y).toBe(30);
    expect(player?.opacity).toBe(1);

    expect(arrow?.x).toBe(10);
    expect(arrow?.y).toBe(15);
    expect(arrow?.end_x).toBe(30);
    expect(arrow?.end_y).toBe(45);
    expect(arrow?.label).toBe('Run');
  });

  it('returns target state at progress 1', () => {
    const sourceFrame = createFrame([
      createPlayerItem({ x: 20, y: 30 }),
      createArrowItem({ x: 10, y: 15, end_x: 30, end_y: 45 }),
    ]);
    const targetFrame = createFrame(
      [
        createPlayerItem({ id: 3, stable_id: 'stable-player', x: 80, y: 90 }),
        createArrowItem({
          id: 4,
          stable_id: 'stable-arrow',
          x: 50,
          y: 55,
          end_x: 70,
          end_y: 85,
          label: 'Next run',
        }),
      ],
      1
    );

    const result = interpolateFrames(sourceFrame, targetFrame, 1);

    const player = result.items.find((item) => item.stable_id === 'stable-player');
    const arrow = result.items.find((item) => item.stable_id === 'stable-arrow');

    expect(player?.x).toBe(80);
    expect(player?.y).toBe(90);
    expect(player?.opacity).toBe(1);

    expect(arrow?.x).toBe(50);
    expect(arrow?.y).toBe(55);
    expect(arrow?.end_x).toBe(70);
    expect(arrow?.end_y).toBe(85);
    expect(arrow?.label).toBe('Next run');
  });

  it('fades out source-only items', () => {
    const sourceFrame = createFrame([
      createPlayerItem({ stable_id: 'source-only-player' }),
    ]);
    const targetFrame = createFrame([], 1);

    const result = interpolateFrames(sourceFrame, targetFrame, 0.25);
    const item = result.items[0];

    expect(item.stable_id).toBe('source-only-player');
    expect(item.source_item_id).toBe(1);
    expect(item.target_item_id).toBeNull();
    expect(item.opacity).toBeCloseTo(0.75, 8);
  });

  it('fades in target-only items', () => {
    const sourceFrame = createFrame([]);
    const targetFrame = createFrame(
      [createPlayerItem({ stable_id: 'target-only-player' })],
      1
    );

    const result = interpolateFrames(sourceFrame, targetFrame, 0.25);
    const item = result.items[0];

    expect(item.stable_id).toBe('target-only-player');
    expect(item.source_item_id).toBeNull();
    expect(item.target_item_id).toBe(1);
    expect(item.opacity).toBeCloseTo(0.25, 8);
  });

  it('does not mutate the persisted source frame data', () => {
    const sourceItem = createArrowItem({
      stable_id: 'no-mutation-arrow',
      style: { stroke_width: 3 },
    });
    const targetItem = createArrowItem({
      id: 4,
      stable_id: 'no-mutation-arrow',
      x: 60,
      y: 65,
      end_x: 80,
      end_y: 85,
      style: { stroke_width: 5 },
    });

    const sourceFrame = createFrame([sourceItem]);
    const targetFrame = createFrame([targetItem], 1);

    const sourceSnapshot = JSON.stringify(sourceFrame);
    interpolateFrames(sourceFrame, targetFrame, 0.5);

    expect(JSON.stringify(sourceFrame)).toBe(sourceSnapshot);
  });
});
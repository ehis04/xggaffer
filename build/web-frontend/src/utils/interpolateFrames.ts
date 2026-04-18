import type {
    TacticsBoardFrame,
    TacticsBoardItem,
    TacticsRenderableFrame,
    TacticsRenderableItem,
} from '../types/tactics';
import { clampUnitInterval, easeInOutCubic } from './easing';

interface MatchedTacticsItems {
    stableId: string;
    sourceItem: TacticsBoardItem | null;
    targetItem: TacticsBoardItem | null;
}

const interpolateNumber = (
    sourceValue: number,
    targetValue: number,
    progress: number
): number => {
    return sourceValue + ((targetValue - sourceValue) * progress);
};

const snapAtMidpoint = <T>(
    sourceValue: T,
    targetValue: T,
    progress: number
): T => {
    return progress < 0.5 ? sourceValue : targetValue;
};

const cloneStyle = (
    style: TacticsBoardItem['style'] | undefined
): TacticsBoardItem['style'] => {
    return { ...(style ?? {}) };
};

const sortItemsForPlayback = (items: MatchedTacticsItems[]): MatchedTacticsItems[] => {
    return [...items].sort((left, right) => {
        const leftReference = left.sourceItem ?? left.targetItem;
        const rightReference = right.sourceItem ?? right.targetItem;

        const leftZIndex = leftReference?.z_index ?? 0;
        const rightZIndex = rightReference?.z_index ?? 0;

        if (leftZIndex !== rightZIndex) {
            return leftZIndex - rightZIndex;
        }

        const leftId = left.sourceItem?.id ?? left.targetItem?.id ?? Number.MAX_SAFE_INTEGER;
        const rightId = right.sourceItem?.id ?? right.targetItem?.id ?? Number.MAX_SAFE_INTEGER;

        return leftId - rightId;
    });
};

export const matchItemsByStableId = (
    sourceItems: TacticsBoardItem[],
    targetItems: TacticsBoardItem[]
): MatchedTacticsItems[] => {
    const sourceByStableId = new Map<string, TacticsBoardItem>();
    const targetByStableId = new Map<string, TacticsBoardItem>();

    sourceItems.forEach((item) => {
        sourceByStableId.set(item.stable_id, item);
    });

    targetItems.forEach((item) => {
        targetByStableId.set(item.stable_id, item);
    });

    const stableIds = new Set<string>([
        ...sourceByStableId.keys(),
        ...targetByStableId.keys(),
    ]);

    return sortItemsForPlayback(
        Array.from(stableIds).map((stableId) => ({
            stableId,
            sourceItem: sourceByStableId.get(stableId) ?? null,
            targetItem: targetByStableId.get(stableId) ?? null,
        }))
    );
};

const interpolateMatchedItem = (
    sourceItem: TacticsBoardItem,
    targetItem: TacticsBoardItem,
    progress: number
): TacticsRenderableItem => {
    const easedProgress = easeInOutCubic(progress);
    const referenceItem = progress < 0.5 ? sourceItem : targetItem;

    const hasInterpolatedEndCoordinates =
        sourceItem.end_x !== null &&
        sourceItem.end_y !== null &&
        targetItem.end_x !== null &&
        targetItem.end_y !== null;

    return {
        ...referenceItem,
        render_key: referenceItem.stable_id,
        source_item_id: sourceItem.id,
        target_item_id: targetItem.id,
        is_interpolated: true,
        opacity: 1,
        x: interpolateNumber(sourceItem.x, targetItem.x, easedProgress),
        y: interpolateNumber(sourceItem.y, targetItem.y, easedProgress),
        end_x: hasInterpolatedEndCoordinates
            ? interpolateNumber(sourceItem.end_x, targetItem.end_x, easedProgress)
            : snapAtMidpoint(sourceItem.end_x, targetItem.end_x, progress),
        end_y: hasInterpolatedEndCoordinates
            ? interpolateNumber(sourceItem.end_y, targetItem.end_y, easedProgress)
            : snapAtMidpoint(sourceItem.end_y, targetItem.end_y, progress),
        width: snapAtMidpoint(sourceItem.width, targetItem.width, progress),
        height: snapAtMidpoint(sourceItem.height, targetItem.height, progress),
        rotation: snapAtMidpoint(sourceItem.rotation, targetItem.rotation, progress),
        z_index: snapAtMidpoint(sourceItem.z_index, targetItem.z_index, progress),
        label: snapAtMidpoint(sourceItem.label, targetItem.label, progress),
        shirt_number: snapAtMidpoint(
            sourceItem.shirt_number,
            targetItem.shirt_number,
            progress
        ),
        position_label: snapAtMidpoint(
            sourceItem.position_label,
            targetItem.position_label,
            progress
        ),
        linked_player: snapAtMidpoint(
            sourceItem.linked_player,
            targetItem.linked_player,
            progress
        ),
        player_summary: snapAtMidpoint(
            sourceItem.player_summary,
            targetItem.player_summary,
            progress
        ),
        style:
            progress < 0.5
                ? cloneStyle(sourceItem.style)
                : cloneStyle(targetItem.style),
    } as TacticsRenderableItem;
};

const fadeOutSourceOnlyItem = (
    item: TacticsBoardItem,
    progress: number
): TacticsRenderableItem => {
    return {
        ...item,
        render_key: item.stable_id,
        source_item_id: item.id,
        target_item_id: null,
        is_interpolated: false,
        opacity: 1 - clampUnitInterval(progress),
        style: cloneStyle(item.style),
    };
};

const fadeInTargetOnlyItem = (
    item: TacticsBoardItem,
    progress: number
): TacticsRenderableItem => {
    return {
        ...item,
        render_key: item.stable_id,
        source_item_id: null,
        target_item_id: item.id,
        is_interpolated: false,
        opacity: clampUnitInterval(progress),
        style: cloneStyle(item.style),
    };
};

export const interpolateFrames = (
    sourceFrame: TacticsBoardFrame,
    targetFrame: TacticsBoardFrame,
    progress: number
): TacticsRenderableFrame => {
    const clampedProgress = clampUnitInterval(progress);
    const matchedItems = matchItemsByStableId(sourceFrame.items, targetFrame.items);

    const items = matchedItems.map(({ sourceItem, targetItem }) => {
        if (sourceItem && targetItem) {
            return interpolateMatchedItem(sourceItem, targetItem, clampedProgress);
        }

        if (sourceItem) {
            return fadeOutSourceOnlyItem(sourceItem, clampedProgress);
        }

        return fadeInTargetOnlyItem(targetItem!, clampedProgress);
    });

    return {
        frame_index: sourceFrame.frame_index,
        label: clampedProgress < 0.5 ? sourceFrame.label : targetFrame.label,
        duration_ms: sourceFrame.duration_ms,
        notes: clampedProgress < 0.5 ? sourceFrame.notes : targetFrame.notes,
        items,
    };
};

export default interpolateFrames;
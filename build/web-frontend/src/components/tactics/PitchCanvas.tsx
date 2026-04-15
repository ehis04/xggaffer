import React, { useMemo, useRef, useState } from 'react';
import type {
  MutableRefObject,
  PointerEvent as ReactPointerEvent,
} from 'react';
import type {
  TacticsActiveTool,
  TacticsArrowItem,
  TacticsBallItem,
  TacticsBoardFrame,
  TacticsBoardItem,
  TacticsDraftItem,
  TacticsLineItem,
  TacticsRenderableArrowItem,
  TacticsRenderableBallItem,
  TacticsRenderableItem,
  TacticsRenderableLineItem,
  TacticsRenderableTextItem,
  TacticsRenderableZoneItem,
  TacticsTextItem,
  TacticsZoneItem,
} from '../../types/tactics';
import {
  PITCH_VIEWBOX_HEIGHT,
  PITCH_VIEWBOX_WIDTH,
  svgToPitch,
  pitchToSvg,
} from '../../utils/pitchCoords';
import BoardArrow from './BoardArrow';
import BoardBall from './BoardBall';
import BoardLine from './BoardLine';
import BoardPlayerMarker from './BoardPlayerMarker';
import BoardTextLabel from './BoardTextLabel';
import BoardZone from './BoardZone';
import PitchMarkings from './PitchMarkings';

type CanvasSceneItem = TacticsBoardItem | TacticsRenderableItem;

interface PitchCanvasProps {
  frame: TacticsBoardFrame;
  renderItems?: TacticsRenderableItem[];
  isPlaybackMode?: boolean;
  activeTool?: TacticsActiveTool;
  draftItem?: TacticsDraftItem | null;
  selectedItemId?: number | null;
  svgElementRef?: MutableRefObject<SVGSVGElement | null>;
  onSelectItem?: (itemId: number | null) => void;
  onMoveItem?: (itemId: number, x: number, y: number) => void;
  onCommitMoveItem?: (
    frameIndex: number,
    itemId: number,
    initialX: number,
    initialY: number,
    finalX: number,
    finalY: number
  ) => void;
  onCreatePointItem?: (
    tool: Extract<TacticsActiveTool, 'ball' | 'text'>,
    x: number,
    y: number
  ) => void;
  onStartDirectionalDraft?: (
    tool: Extract<TacticsActiveTool, 'arrow' | 'line'>,
    x: number,
    y: number
  ) => void;
  onUpdateDirectionalDraft?: (x: number, y: number) => void;
  onCompleteDirectionalItem?: (
    tool: Extract<TacticsActiveTool, 'arrow' | 'line'>,
    startX: number,
    startY: number,
    endX: number,
    endY: number
  ) => void;
  onStartZoneDraft?: (x: number, y: number) => void;
  onUpdateZoneDraft?: (x: number, y: number) => void;
  onCompleteZoneItem?: (
    x: number,
    y: number,
    width: number,
    height: number
  ) => void;
  onCancelDraft?: () => void;
}

interface DragState {
  itemId: number;
  pointerId: number;
  offsetSvgX: number;
  offsetSvgY: number;
  initialPitchX: number;
  initialPitchY: number;
  currentPitchX: number;
  currentPitchY: number;
}

const MIN_ZONE_SIZE = 1.5;

const sortSceneItems = (items: CanvasSceneItem[]): CanvasSceneItem[] => {
  return [...items].sort((left, right) => {
    if (left.z_index !== right.z_index) {
      return left.z_index - right.z_index;
    }

    const leftId = 'id' in left ? left.id : Number.MAX_SAFE_INTEGER;
    const rightId = 'id' in right ? right.id : Number.MAX_SAFE_INTEGER;

    return leftId - rightId;
  });
};

const isDirectionalTool = (
  tool: TacticsActiveTool
): tool is Extract<TacticsActiveTool, 'arrow' | 'line'> => {
  return tool === 'arrow' || tool === 'line';
};

const getZoneRectangle = (
  startX: number,
  startY: number,
  currentX: number,
  currentY: number
) => {
  return {
    x: Math.min(startX, currentX),
    y: Math.min(startY, currentY),
    width: Math.abs(currentX - startX),
    height: Math.abs(currentY - startY),
  };
};

const getSceneItemKey = (item: CanvasSceneItem): string => {
  return 'render_key' in item ? item.render_key : String(item.id);
};

const getSceneItemId = (item: CanvasSceneItem): number | null => {
  return 'id' in item ? item.id : null;
};

const PitchCanvas: React.FC<PitchCanvasProps> = ({
  frame,
  renderItems,
  isPlaybackMode = false,
  activeTool = 'select',
  draftItem = null,
  selectedItemId = null,
  svgElementRef,
  onSelectItem,
  onMoveItem,
  onCommitMoveItem,
  onCreatePointItem,
  onStartDirectionalDraft,
  onUpdateDirectionalDraft,
  onCompleteDirectionalItem,
  onStartZoneDraft,
  onUpdateZoneDraft,
  onCompleteZoneItem,
  onCancelDraft,
}) => {
  const internalSvgRef = useRef<SVGSVGElement | null>(null);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [zoneDraftPointerId, setZoneDraftPointerId] = useState<number | null>(null);

  const setSvgNode = (node: SVGSVGElement | null) => {
    internalSvgRef.current = node;

    if (svgElementRef) {
      svgElementRef.current = node;
    }
  };

  const sceneItems = useMemo(() => {
    return sortSceneItems(renderItems ?? frame.items);
  }, [frame.items, renderItems]);

  const draftPreview = useMemo(() => {
    if (isPlaybackMode || !draftItem) {
      return null;
    }

    if (draftItem.tool === 'arrow') {
      const previewItem: TacticsArrowItem = {
        id: -1,
        frame: frame.id,
        item_type: 'arrow',
        team_side: 'neutral',
        stable_id: 'draft-arrow',
        linked_player: null,
        label: '',
        shirt_number: null,
        position_label: '',
        x: draftItem.startX,
        y: draftItem.startY,
        end_x: draftItem.currentX,
        end_y: draftItem.currentY,
        width: null,
        height: null,
        rotation: 0,
        z_index: Number.MAX_SAFE_INTEGER,
        style: {},
        player_summary: null,
      };

      return <BoardArrow key="draft-arrow" item={previewItem} isSelected={false} />;
    }

    if (draftItem.tool === 'line') {
      const previewItem: TacticsLineItem = {
        id: -1,
        frame: frame.id,
        item_type: 'line',
        team_side: 'neutral',
        stable_id: 'draft-line',
        linked_player: null,
        label: '',
        shirt_number: null,
        position_label: '',
        x: draftItem.startX,
        y: draftItem.startY,
        end_x: draftItem.currentX,
        end_y: draftItem.currentY,
        width: null,
        height: null,
        rotation: 0,
        z_index: Number.MAX_SAFE_INTEGER,
        style: {},
        player_summary: null,
      };

      return <BoardLine key="draft-line" item={previewItem} isSelected={false} />;
    }

    if (draftItem.tool === 'zone') {
      const rectangle = getZoneRectangle(
        draftItem.startX,
        draftItem.startY,
        draftItem.currentX,
        draftItem.currentY
      );

      const previewItem: TacticsZoneItem = {
        id: -1,
        frame: frame.id,
        item_type: 'zone',
        team_side: 'neutral',
        stable_id: 'draft-zone',
        linked_player: null,
        label: '',
        shirt_number: null,
        position_label: '',
        x: rectangle.x,
        y: rectangle.y,
        end_x: null,
        end_y: null,
        width: rectangle.width,
        height: rectangle.height,
        rotation: 0,
        z_index: Number.MAX_SAFE_INTEGER,
        style: {},
        player_summary: null,
      };

      return <BoardZone key="draft-zone" item={previewItem} isSelected={false} />;
    }

    return null;
  }, [draftItem, frame.id, isPlaybackMode]);

  const getLocalSvgPoint = (
    event: ReactPointerEvent<SVGSVGElement | SVGGElement | SVGRectElement>
  ) => {
    const svg = internalSvgRef.current;
    if (!svg) {
      return null;
    }

    if (typeof svg.getScreenCTM !== 'function') {
      return null;
    }

    const screenCtm = svg.getScreenCTM();
    if (!screenCtm) {
      return null;
    }

    if (typeof svg.createSVGPoint !== 'function') {
      return null;
    }

    const point = svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;

    return point.matrixTransform(screenCtm.inverse());
  };

  const handleMarkerPointerDown =
    (item: TacticsBoardItem) => (event: ReactPointerEvent<SVGGElement>) => {
      if (isPlaybackMode) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();

      const svgPoint = getLocalSvgPoint(event);
      if (!svgPoint) {
        return;
      }

      const markerSvgPoint = pitchToSvg(item.x, item.y);

      setDragState({
        itemId: item.id,
        pointerId: event.pointerId,
        offsetSvgX: markerSvgPoint.x - svgPoint.x,
        offsetSvgY: markerSvgPoint.y - svgPoint.y,
        initialPitchX: item.x,
        initialPitchY: item.y,
        currentPitchX: item.x,
        currentPitchY: item.y,
      });

      onSelectItem?.(item.id);
      internalSvgRef.current?.setPointerCapture(event.pointerId);
    };

  const handleSelectableItemPointerDown =
    (itemId: number) => (event: ReactPointerEvent<SVGGElement>) => {
      if (isPlaybackMode) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      onSelectItem?.(itemId);
    };

  const handleCanvasInteractionPointerDown = (
    event: ReactPointerEvent<SVGSVGElement>
  ) => {
    if (isPlaybackMode) {
      return;
    }

    event.preventDefault();

    if (dragState) {
      return;
    }

    const svgPoint = getLocalSvgPoint(event);
    const pitchPoint = svgPoint
      ? svgToPitch(svgPoint.x, svgPoint.y)
      : { x: 0, y: 0 };

    if (activeTool === 'ball' || activeTool === 'text') {
      onCreatePointItem?.(activeTool, pitchPoint.x, pitchPoint.y);
      return;
    }

    if (isDirectionalTool(activeTool)) {
      if (draftItem && draftItem.tool === activeTool) {
        onCompleteDirectionalItem?.(
          activeTool,
          draftItem.startX,
          draftItem.startY,
          pitchPoint.x,
          pitchPoint.y
        );
        return;
      }

      onStartDirectionalDraft?.(activeTool, pitchPoint.x, pitchPoint.y);
      return;
    }

    if (activeTool === 'zone') {
      onStartZoneDraft?.(pitchPoint.x, pitchPoint.y);
      setZoneDraftPointerId(event.pointerId);
      internalSvgRef.current?.setPointerCapture(event.pointerId);
      return;
    }

    onSelectItem?.(null);
  };

  const handlePointerMove = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (isPlaybackMode) {
      return;
    }

    if (dragState && event.pointerId === dragState.pointerId) {
      const svgPoint = getLocalSvgPoint(event);
      if (!svgPoint) {
        return;
      }

      const nextPitchPoint = svgToPitch(
        svgPoint.x + dragState.offsetSvgX,
        svgPoint.y + dragState.offsetSvgY
      );

      onMoveItem?.(dragState.itemId, nextPitchPoint.x, nextPitchPoint.y);
      setDragState((previousState) => {
        if (!previousState || previousState.pointerId !== event.pointerId) {
          return previousState;
        }

        return {
          ...previousState,
          currentPitchX: nextPitchPoint.x,
          currentPitchY: nextPitchPoint.y,
        };
      });
      return;
    }

    if (
      zoneDraftPointerId !== null &&
      event.pointerId === zoneDraftPointerId &&
      draftItem &&
      draftItem.tool === 'zone'
    ) {
      const svgPoint = getLocalSvgPoint(event);
      if (!svgPoint) {
        return;
      }

      const nextPitchPoint = svgToPitch(svgPoint.x, svgPoint.y);
      onUpdateZoneDraft?.(nextPitchPoint.x, nextPitchPoint.y);
      return;
    }

    if (
      !dragState &&
      draftItem &&
      (draftItem.tool === 'arrow' || draftItem.tool === 'line')
    ) {
      const svgPoint = getLocalSvgPoint(event);
      if (!svgPoint) {
        return;
      }

      const nextPitchPoint = svgToPitch(svgPoint.x, svgPoint.y);
      onUpdateDirectionalDraft?.(nextPitchPoint.x, nextPitchPoint.y);
    }
  };

  const endDrag = (pointerId: number) => {
    if (!dragState || dragState.pointerId !== pointerId) {
      return;
    }

    onCommitMoveItem?.(
      frame.frame_index,
      dragState.itemId,
      dragState.initialPitchX,
      dragState.initialPitchY,
      dragState.currentPitchX,
      dragState.currentPitchY
    );

    if (internalSvgRef.current?.hasPointerCapture(pointerId)) {
      internalSvgRef.current.releasePointerCapture(pointerId);
    }

    setDragState(null);
  };

  const endZoneDraft = (pointerId: number) => {
    if (zoneDraftPointerId !== pointerId) {
      return;
    }

    if (internalSvgRef.current?.hasPointerCapture(pointerId)) {
      internalSvgRef.current.releasePointerCapture(pointerId);
    }

    setZoneDraftPointerId(null);
  };

  const handlePointerUp = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (isPlaybackMode) {
      return;
    }

    if (
      zoneDraftPointerId !== null &&
      event.pointerId === zoneDraftPointerId &&
      draftItem &&
      draftItem.tool === 'zone'
    ) {
      const rectangle = getZoneRectangle(
        draftItem.startX,
        draftItem.startY,
        draftItem.currentX,
        draftItem.currentY
      );

      endZoneDraft(event.pointerId);

      if (rectangle.width < MIN_ZONE_SIZE || rectangle.height < MIN_ZONE_SIZE) {
        onCancelDraft?.();
        return;
      }

      onCompleteZoneItem?.(
        rectangle.x,
        rectangle.y,
        rectangle.width,
        rectangle.height
      );
      return;
    }

    endDrag(event.pointerId);
  };

  const handlePointerCancel = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (isPlaybackMode) {
      return;
    }

    if (zoneDraftPointerId !== null && event.pointerId === zoneDraftPointerId) {
      endZoneDraft(event.pointerId);
      onCancelDraft?.();
      return;
    }

    endDrag(event.pointerId);
  };

    const handleLostPointerCapture = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (isPlaybackMode) {
        return;
    }

    if (zoneDraftPointerId !== null && event.pointerId === zoneDraftPointerId) {
        endZoneDraft(event.pointerId);
        onCancelDraft?.();
        return;
    }

    endDrag(event.pointerId);
    };

  const renderSceneItem = (item: CanvasSceneItem) => {
    const itemId = getSceneItemId(item);
    const isSelected = !isPlaybackMode && itemId !== null && selectedItemId === itemId;
    const onPointerDown =
      !isPlaybackMode && itemId !== null
        ? handleSelectableItemPointerDown(itemId)
        : undefined;

    switch (item.item_type) {
      case 'player':
        return (
          <BoardPlayerMarker
            key={getSceneItemKey(item)}
            item={item}
            isSelected={isSelected}
            isDragging={!isPlaybackMode && dragState?.itemId === itemId}
            onPointerDown={
              !isPlaybackMode && itemId !== null && 'id' in item
                ? handleMarkerPointerDown(item)
                : undefined
            }
          />
        );

      case 'ball':
        return (
          <BoardBall
            key={getSceneItemKey(item)}
            item={item as TacticsBallItem | TacticsRenderableBallItem}
            isSelected={isSelected}
            onPointerDown={onPointerDown}
          />
        );

      case 'arrow':
        return (
          <BoardArrow
            key={getSceneItemKey(item)}
            item={item as TacticsArrowItem | TacticsRenderableArrowItem}
            isSelected={isSelected}
            onPointerDown={onPointerDown}
          />
        );

      case 'line':
        return (
          <BoardLine
            key={getSceneItemKey(item)}
            item={item as TacticsLineItem | TacticsRenderableLineItem}
            isSelected={isSelected}
            onPointerDown={onPointerDown}
          />
        );

      case 'zone':
        return (
          <BoardZone
            key={getSceneItemKey(item)}
            item={item as TacticsZoneItem | TacticsRenderableZoneItem}
            isSelected={isSelected}
            onPointerDown={onPointerDown}
          />
        );

      case 'text':
        return (
          <BoardTextLabel
            key={getSceneItemKey(item)}
            item={item as TacticsTextItem | TacticsRenderableTextItem}
            isSelected={isSelected}
            onPointerDown={onPointerDown}
          />
        );

      default:
        return null;
    }
  };

  return (
    <svg
      ref={setSvgNode}
      viewBox={`0 0 ${PITCH_VIEWBOX_WIDTH} ${PITCH_VIEWBOX_HEIGHT}`}
      role="img"
      aria-label={`Tactics pitch for frame ${frame.frame_index}`}
      onLostPointerCapture={handleLostPointerCapture}
      onPointerDown={handleCanvasInteractionPointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerCancel}
      style={{
        width: '100%',
        maxWidth: '1050px',
        height: 'auto',
        display: 'block',
        background:
          'linear-gradient(180deg, #1f7a3d 0%, #1d6f38 50%, #1b6633 100%)',
        borderRadius: '18px',
        border: '1px solid rgba(255,255,255,0.12)',
        touchAction: isPlaybackMode ? 'auto' : 'none',
        userSelect: 'none',
      }}
      preserveAspectRatio="xMidYMid meet"
    >
      <PitchMarkings />

      <rect
        x={0}
        y={0}
        width={PITCH_VIEWBOX_WIDTH}
        height={PITCH_VIEWBOX_HEIGHT}
        fill="transparent"
      />

      {sceneItems.map(renderSceneItem)}

      {draftPreview}
    </svg>
  );
};

export default PitchCanvas;
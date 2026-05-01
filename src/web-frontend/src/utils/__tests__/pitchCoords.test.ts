import { describe, expect, it } from 'vitest';

import {
    clampPitchCoordinate,
    clampPitchPoint,
    pitchToSvg,
    svgToPitch,
    PITCH_PADDING,
    INNER_PITCH_WIDTH,
    INNER_PITCH_HEIGHT,
} from '../pitchCoords';

describe('pitchCoords', () => {
    it('clamps individual coordinates to [0, 100]', () => {
        expect(clampPitchCoordinate(-5)).toBe(0);
        expect(clampPitchCoordinate(120)).toBe(100);
        expect(clampPitchCoordinate(42)).toBe(42);
        expect(clampPitchCoordinate(Number.NaN)).toBe(0);
    });

    it('clamps pitch points on both axes', () => {
        expect(clampPitchPoint({ x: -10, y: 150 })).toEqual({ x: 0, y: 100 });
        expect(clampPitchPoint({ x: 55, y: 45 })).toEqual({ x: 55, y: 45 });
    });

    it('maps pitch corners to svg corners', () => {
        expect(pitchToSvg(0, 0)).toEqual({
            x: PITCH_PADDING,
            y: PITCH_PADDING + INNER_PITCH_HEIGHT,
        });

        expect(pitchToSvg(100, 100)).toEqual({
            x: PITCH_PADDING + INNER_PITCH_WIDTH,
            y: PITCH_PADDING,
        });
    });

    it('round-trips representative points between pitch and svg space', () => {
        const points = [
            { x: 0, y: 0 },
            { x: 50, y: 50 },
            { x: 100, y: 100 },
            { x: 12.5, y: 87.5 },
        ];

        points.forEach((point) => {
            const svg = pitchToSvg(point.x, point.y);
            const roundTrip = svgToPitch(svg.x, svg.y);
            expect(roundTrip.x).toBeCloseTo(point.x, 8);
            expect(roundTrip.y).toBeCloseTo(point.y, 8);
        });
    });

    it('clamps out-of-bounds svg coordinates back to pitch bounds', () => {
        expect(svgToPitch(-9999, 9999)).toEqual({ x: 0, y: 0 });
        expect(svgToPitch(9999, -9999)).toEqual({ x: 100, y: 100 });
    });
});
import { describe, expect, it } from 'vitest';

import { AppError } from '../AppError';

describe('AppError', () => {
  describe('fromResponse status mapping', () => {
    it('maps 401 to UNAUTHENTICATED', () => {
      const err = AppError.fromResponse(401, {});
      expect(err.code).toBe('UNAUTHENTICATED');
    });

    it('maps 403 to FORBIDDEN', () => {
      const err = AppError.fromResponse(403, {});
      expect(err.code).toBe('FORBIDDEN');
    });

    it('maps 404 to NOT_FOUND', () => {
      const err = AppError.fromResponse(404, {});
      expect(err.code).toBe('NOT_FOUND');
    });

    it('maps 500 to SERVER_ERROR', () => {
      const err = AppError.fromResponse(500, {});
      expect(err.code).toBe('SERVER_ERROR');
    });

    it('maps 503 to SERVER_ERROR', () => {
      const err = AppError.fromResponse(503, {});
      expect(err.code).toBe('SERVER_ERROR');
    });

    it('maps 400 to UNKNOWN', () => {
      const err = AppError.fromResponse(400, {});
      expect(err.code).toBe('UNKNOWN');
    });

    it('maps 422 to UNKNOWN', () => {
      const err = AppError.fromResponse(422, {});
      expect(err.code).toBe('UNKNOWN');
    });
  });

  describe('detail extraction', () => {
    it('extracts detail from data.detail string', () => {
      const err = AppError.fromResponse(400, { detail: 'Custom detail message' });
      expect(err.detail).toBe('Custom detail message');
    });

    it('extracts detail from data.message string', () => {
      const err = AppError.fromResponse(400, { message: 'Custom message' });
      expect(err.detail).toBe('Custom message');
    });

    it('prefers data.detail over data.message', () => {
      const err = AppError.fromResponse(400, { detail: 'Detail wins', message: 'Message loses' });
      expect(err.detail).toBe('Detail wins');
    });

    it('falls back to HTTP {status} when no detail or message', () => {
      const err = AppError.fromResponse(404, {});
      expect(err.detail).toBe('HTTP 404');
    });

    it('falls back when data is null', () => {
      const err = AppError.fromResponse(500, null);
      expect(err.detail).toBe('HTTP 500');
    });

    it('falls back when data is a string without structure', () => {
      const err = AppError.fromResponse(503, 'raw string');
      expect(err.detail).toBe('raw string');
    });
  });

  describe('class properties', () => {
    it('sets status on the instance', () => {
      const err = AppError.fromResponse(404, {});
      expect(err.status).toBe(404);
    });

    it('sets name to AppError', () => {
      const err = AppError.fromResponse(404, {});
      expect(err.name).toBe('AppError');
    });

    it('extends Error so message equals detail', () => {
      const err = AppError.fromResponse(404, { detail: 'Not found' });
      expect(err.message).toBe('Not found');
    });

    it('is instanceof Error', () => {
      const err = AppError.fromResponse(404, {});
      expect(err).toBeInstanceOf(Error);
    });

    it('is instanceof AppError', () => {
      const err = AppError.fromResponse(404, {});
      expect(err).toBeInstanceOf(AppError);
    });

    it('retains a request ID for support correlation', () => {
      const err = AppError.fromResponse(500, {}, 'edge-request-42');
      expect(err.requestId).toBe('edge-request-42');
    });
  });
});

import { expect, it, vi } from 'vitest';
import apiClient, { changeApiSession } from './client';

it('finishes the previous session refresh before changing cookies and drops its pending retry', async () => {
  let completeRefresh!: (response: Response) => void;
  let signalRefreshStarted!: () => void;
  const refreshStarted = new Promise<void>(resolve => { signalRefreshStarted = resolve; });
  const fetchMock = vi.fn((url: string) => {
    if (url.endsWith('/auth/refresh/')) {
      signalRefreshStarted();
      return new Promise<Response>(resolve => { completeRefresh = resolve; });
    }
    return Promise.resolve(new Response('{}', { status: 401 }));
  });
  vi.stubGlobal('fetch', fetchMock);

  try {
    const previousRequest = apiClient.get('/previous-account/').catch(error => error);
    await refreshStarted;
    const changeCookies = vi.fn(async () => undefined);
    const transition = changeApiSession(changeCookies);
    expect(changeCookies).not.toHaveBeenCalled();

    completeRefresh(new Response('{}', { status: 200 }));
    await transition;
    expect(changeCookies).toHaveBeenCalledOnce();
    expect(await previousRequest).toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  } finally {
    vi.unstubAllGlobals();
  }
});

const base_url = "http://localhost:8000/api";

export const Api_Endpoints = {
  LOGIN: `${base_url}/users/login/`,
  LOGOUT: `${base_url}/users/logout/`,
  REFRESH_TOKEN: `${base_url}/users/api/token/refresh/`,
  CREATE_POST: `${base_url}/community/create/post/`,
  CREATE_COMMENT: (postId: number) => `${base_url}/community/post/${postId}/create/comment/`,
  EXPLORE_POSTS: `${base_url}/community/explore/?order_by=ranked/`,
  POST_ID: (postId: number) => `${base_url}/community/post/${postId}/`,
  DELETE_POST: (postId: number) => `${base_url}/community/my-post/${postId}/`,
  LIKE_POST: (postId: number) => `${base_url}/community/posts/${postId}/like/`,
  LIKE_COMMENT: (postId: number) => `${base_url}/community/comment/${postId}/like/`,
  POST_COMMENTS: (postId: number) => `${base_url}/community/posts/${postId}/comments/`,
};

export const getAccessToken = (): string | null => {
  return localStorage.getItem("access_token");
};

export const getRefreshToken = (): string | null => {
  return localStorage.getItem("refresh_token");
};

export const isAuthenticated = (): boolean => {
  return !!getAccessToken();
};

export const clearTokens = (): void => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
};

export const refreshAccessToken = async (): Promise<string | null> => {
  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    return null;
  }

  try {
    const response = await fetch(Api_Endpoints.REFRESH_TOKEN, {
      method: "POST",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify({
        refresh: refreshToken,
      }),
    });

    if (!response.ok) {
      clearTokens();
      return null;
    }

    const data = await response.json();
    localStorage.setItem("access_token", data.access);
    return data.access;
  } catch (error) {
    clearTokens();
    console.log(error)
    return null;
  }
};

export const authenticatedFetch = async (
    url: string,
    options: RequestInit = {}
): Promise<Response> => {
    const accessToken = getAccessToken();

    if (!accessToken) {
        throw new Error("No access token!");
    }

    const headers = {
        ...options.headers,
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
    };

    let response = await fetch(url, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        const newToken = await refreshAccessToken();

        if (newToken) {
            headers.Authorization = `Bearer ${newToken}`;
            response = await fetch(url, {
                ...options,
                headers,
            });
        } else {
            globalThis.location.href = "/login";
            throw new Error("Session expired");
        }
    }
    return response;
}

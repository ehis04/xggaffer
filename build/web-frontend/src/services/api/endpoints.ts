export const AUTH = {
  LOGIN:                  '/users/auth/login/',
  LOGOUT:                 '/users/auth/logout/',
  REFRESH:                '/users/auth/refresh/',
  ME:                     '/users/auth/me/',
  REGISTER:               '/users/register/',
  SEND_VERIFICATION:      '/users/auth/send-verification/',
  RESEND_VERIFICATION:    '/users/auth/resend-verification/',
  VERIFY_EMAIL:           '/users/auth/verify-email/',
  VERIFICATION_STATUS:    '/users/auth/verification-status/',
} as const;

export const USERS = {
  CREATE_PROFILE:         '/users/profile/create/',
  PROFILE:                '/users/profile/',
  ROLE:                   '/users/profile/role/',
  GET_PROFILE:            (username: string) => `/users/profile/${username}/`,
  FOLLOW:                 (username: string) => `/users/profile/${username}/follow/`,
  FOLLOW_STATUS:          (username: string) => `/users/profile/${username}/follow-status/`,
  FOLLOWERS:              (username: string) => `/users/profile/${username}/followers/`,
  FOLLOWING:              (username: string) => `/users/profile/${username}/following/`,
} as const;

export const COMMUNITY = {
  EXPLORE_POSTS:          '/community/explore/',
  FOLLOWING_POSTS: '/community/following/',
  CREATE_POST:            '/community/create/post/',
  POST:                   (postId: number) => `/community/post/${postId}/`,
  DELETE_POST:            (postId: number) => `/community/my-post/${postId}/`,
  DELETE_COMMENT:         (commentId: number) => `/community/my-comment/${commentId}/`,
  LIKE_POST:              (postId: number) => `/community/posts/${postId}/like/`,
  POST_COMMENTS:          (postId: number) => `/community/posts/${postId}/comments/`,
  CREATE_COMMENT:         (postId: number) => `/community/post/${postId}/create/comment/`,
  LIKE_COMMENT:           (commentId: number) => `/community/comment/${commentId}/like/`,
  TRENDING_HASHTAGS:      '/community/hashtags/trending/',
  GET_USERS_POSTS: (username: string) => `/community/posts/user/${username}/`,
} as const;

export const REFEREE = {
  DASHBOARD:              '/referee/dashboard/',
  COURSES:                '/referee/courses/',
  COURSE:                 (lawNumber: number) => `/referee/law/${lawNumber}/`,
  COURSE_BY_NUMBER:       (lawNumber: number) => `/referee/courses/${lawNumber}/`,
  COURSE_PROGRESS:        (lawNumber: number) => `/referee/law/${lawNumber}/progress/`,
  PROGRESS_COMPLETE:      '/referee/progress/complete/',
  PROGRESS_SCENARIO:      '/referee/progress/scenario/',
  PROGRESS_DRILL:         '/referee/progress/drill/',
  QUIZ:                   (lawNumber: number) => `/referee/law/${lawNumber}/quiz/`,
  QUIZ_BY_ID:             (quizId: number) => `/referee/quizzes/${quizId}/`,
  QUIZ_SUBMIT:            (quizId: number) => `/referee/quiz/${quizId}/submit/`,
} as const;

export const COACHING = {
  SQUAD:                  '/coaching/squad/',
  PLAYER:                 (playerId: number) => `/coaching/player/${playerId}/`,
  SESSIONS:               '/coaching/sessions/',
  SESSION:                (sessionId: number) => `/coaching/session/${sessionId}/`,
  STATS:                  '/coaching/stats/',
} as const;


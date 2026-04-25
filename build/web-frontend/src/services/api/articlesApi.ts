import apiClient from './client';
import type {
    ArticleAuthor,
    ArticleDetail,
    ArticleFeedParams,
    ArticleListItem,
    ArticleRating,
    ArticleSite,
    ArticleTopic,
    UserArticleProfile,
} from '../../types/articles';

export interface PaginatedArticles {
    count: number;
    next: string | null;
    previous: string | null;
    results: ArticleListItem[];
}

const articlesApi = {
    getFeed: (params?: ArticleFeedParams): Promise<PaginatedArticles> => {
        const query: Record<string, string> = {};
        if (params?.page) query.page = String(params.page);
        if (params?.q) query.q = String(params.q);
        if (params?.topic) query.topic = String(params.topic);
        if (params?.site) query.site = String(params.site);
        if (params?.author) query.author = String(params.author);
        if (params?.min_quality) query.min_quality = String(params.min_quality);
        return apiClient.get('/articles/feed/', query);
    },

    getArticle: (id: number): Promise<ArticleDetail> =>
        apiClient.get(`/articles/${id}/`),

    rateArticle: (id: number, rating: number, review?: string): Promise<ArticleRating> =>
        apiClient.post(`/articles/${id}/rate/`, { rating, review }),

    deleteRating: (id: number): Promise<void> =>
        apiClient.delete(`/articles/${id}/rate/`),

    submitFeedback: (params: {
        target_type: 'ARTICLE' | 'AUTHOR' | 'SITE';
        target_id: number;
        feedback_type: 'LIKE' | 'DISLIKE';
        article_id?: number;
    }): Promise<{ status: string }> =>
        apiClient.post('/articles/feedback/', params),

    markRead: (id: number, completed: boolean, timeSpentSeconds?: number): Promise<{ status: string }> =>
        apiClient.post(`/articles/${id}/read/`, {
            completed,
            time_spent_seconds: timeSpentSeconds,
        }),

    getTopics: (): Promise<ArticleTopic[]> =>
        apiClient.get('/articles/topics/'),

    getSites: (): Promise<ArticleSite[]> =>
        apiClient.get('/articles/sites/'),

    getAuthors: (): Promise<ArticleAuthor[]> =>
        apiClient.get('/articles/authors/'),

    getProfile: (): Promise<UserArticleProfile> =>
        apiClient.get('/articles/profile/'),

    updateProfile: (data: Partial<UserArticleProfile>): Promise<UserArticleProfile> =>
        apiClient.patch('/articles/profile/', data),
};

export { articlesApi };
export default articlesApi;

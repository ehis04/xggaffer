// Types matching the articles API serializer output.

export interface ArticleTopic {
    id: number;
    name: string;
    slug: string;
    description: string;
}

export interface ArticleSite {
    id: number;
    name: string;
    domain: string;
    logo_url: string;
    reputation_score: number;
    trust_score: number;
    user_sentiment_score: number;
}

export interface ArticleAuthor {
    id: number;
    name: string;
    bio: string;
    expertise_score: number;
    credibility_score: number;
}

export interface ArticleListItem {
    id: number;
    title: string;
    slug: string;
    url: string;
    summary: string;
    image_url: string;
    site: ArticleSite;
    authors: ArticleAuthor[];
    topics: ArticleTopic[];
    publication_date: string;
    word_count: number;
    read_time_minutes: number;
    quality_score: number;
    average_rating: number;
    total_ratings: number;
    total_likes: number;
    total_dislikes: number;
    view_count: number;
    is_featured: boolean;
    // Per-request user context fields
    user_rating: number | null;
    user_feedback: 'LIKE' | 'DISLIKE' | null;
    is_read: boolean;
}

export interface ArticleDetail extends ArticleListItem {
    content: string;
    scraped_date: string | null;
    external_shares: number;
}

export interface ArticleRating {
    id: number;
    article: number;
    user: number;
    rating: number;
    review: string;
    created_at: string;
}

export interface UserArticleProfile {
    articles_read: number;
    last_active: string | null;
    quality_threshold: number;
    min_read_time: number;
    max_read_time: number;
    preferred_topics: ArticleTopic[];
    preferred_authors: ArticleAuthor[];
    preferred_sites: ArticleSite[];
    daily_recommendation_count: number;
    enable_auto_refresh: boolean;
    last_recommendation_refresh: string | null;
}

export interface ArticleFeedParams {
    page?: number;
    q?: string;
    topic?: string | number;
    site?: number;
    author?: number;
    min_quality?: number;
}

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
    user_feedback: 'like' | 'dislike' | null;
    is_read: boolean;
    is_favorited: boolean;
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
    preferred_quality_threshold: number;
    min_read_time: number;
    max_read_time: number;
    preferred_topics: ArticleTopic[];
    disliked_topics: ArticleTopic[];
    preferred_authors: ArticleAuthor[];
    disliked_authors: ArticleAuthor[];
    preferred_sites: ArticleSite[];
    disliked_sites: ArticleSite[];
    liked_topics: ArticleTopic[];
    inferred_disliked_topics: ArticleTopic[];
    liked_authors: ArticleAuthor[];
    inferred_disliked_authors: ArticleAuthor[];
    liked_sites: ArticleSite[];
    inferred_disliked_sites: ArticleSite[];
    articles_liked: number;
    articles_disliked: number;
    articles_favorited: number;
    daily_recommendation_count: number;
    enable_auto_refresh: boolean;
}

export interface UserArticleProfileUpdatePayload {
    preferred_topic_ids?: number[];
    disliked_topic_ids?: number[];
    preferred_author_ids?: number[];
    disliked_author_ids?: number[];
    preferred_site_ids?: number[];
    disliked_site_ids?: number[];
    preferred_quality_threshold?: number;
    min_read_time?: number;
    max_read_time?: number;
    daily_recommendation_count?: number;
    enable_auto_refresh?: boolean;
}

export type ArticleSortOption = 'relevance' | 'recent' | 'popularity';

export interface ArticleFeedParams {
    page?: number;
    q?: string;
    topic?: string | number;
    site?: number;
    author?: number;
    min_quality?: number;
    sort?: ArticleSortOption;
}

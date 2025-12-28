import './css/FeedTabs.css';
import {useState} from 'react';

interface FeedTabsProps {
  onTabChange?: (tab: 'forYou' | 'following') => void;
  defaultTab?: 'forYou' | 'following';
}

export const FeedTabs: React.FC<FeedTabsProps> = ({
    onTabChange,
    defaultTab = 'forYou',
}) => {
    const [activeTab, setActiveTab] = useState<'forYou' | 'following'>(defaultTab);

    const handleTabClick = (tab: 'forYou' | 'following') => {
        setActiveTab(tab);
        if (onTabChange) {
            onTabChange(tab);
        }
    };

    return (
        <div className='feed-tabs'>
            <div className='feed-tabs-container'>
                <button
                className={`feed-tab ${activeTab === 'forYou' ? 'active' : ''}`}
                onClick={() => handleTabClick('forYou')}
                aria-label='For You'
                >
                    <span className='feed-tab-text'> For You</span>
                    {activeTab === 'forYou' && <div className='feed-tab-indicator'/>}
                </button>

                <button
                className={`feed-tab ${activeTab === 'following' ? 'active' : ''}`}
                onClick={() => handleTabClick('following')}
                aria-label='Following'
                >
                    <span className='feed-tab-text'> Following </span>
                    {activeTab === 'following' && <div className='feed-tab-indicator'/>}
                </button>
            </div>
        </div>
    );
};
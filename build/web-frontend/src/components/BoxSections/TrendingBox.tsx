import "./css/TrendingBox.css";
import { useState } from "react";

interface TrendingItem {
  id: string;
  category: string;
  title: string;
  posts?: number;
  icon?: React.ReactNode;
}

interface TrendingBoxProps {
  title?: string;
  items?: TrendingItem[];
  maxVisible?: number;
  showMoreText?: string;
  onTrendingClick?: (item: TrendingItem) => void;
  onMoreClick?: (item: TrendingItem) => void;
}

export const TrendingBox: React.FC<TrendingBoxProps> = ({
  title = "#Trending",
  items,
  maxVisible = 4,
  showMoreText = "Show more",
  onTrendingClick,
  onMoreClick,
}) => {
  const [expanded, setExpanded] = useState(false);

  const defaultItems: TrendingHashtag[] = [
    {
      id: "1",
      title: "#RealMadrid",
    },
    {
      id: "2",
      title: "#BarcelonaFC",
    },
    {
      id: "3",
      title: "#Chelsea",
    },
    {
      id: "4",
      title: "#Arsenal",
    },
  ];

  const trendingItems = items || defaultItems;
  const displayItems = expanded
    ? trendingItems
    : trendingItems.slice(0, maxVisible);

  const handleItemClick = (item: TrendingItem) => {
    e.stopPropagation();
    if (onMoreClick) {
      onMoreClick(item);
    }
  };

  return (
    <div className="trending-box">
      <h2 className="trending-box-title">{title}</h2>

      <div className="trending-list">
        {displayItems.map((item) => (
          <div
            key={item.id}
            className="trending-item"
            onClick={() => handleItemClick(item)}
          >
            <div className="trending-title">
              <a href="">{item.title}</a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

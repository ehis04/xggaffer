import "./css/SearchBar.css";
import { useState, useRef } from "react";

interface SearchBarProps {
  placeholder?: string;
  onSearch?: (query: string) => void;
  onChange?: (query: string) => void;
  className?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  placeholder = "Search",
  onSearch,
  onChange,
}) => {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch) {
      onSearch(query);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    if (onChange) {
      onChange(value);
    }
  };

  const handleClear = () => {
    setQuery("");
    if (onChange) {
      onChange("");
    }
    inputRef.current?.focus();
  };

  const handelLabelClick = () => {
    inputRef.current?.focus();
  };

  return (
    <form className="searchbar-comp" onSubmit={handleSubmit}>
      <div className="search-icon" onClick={handelLabelClick}>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          fill="currentColor"
          className="bi bi-search"
          viewBox="0 0 16 16"
        >
          <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0" />
        </svg>
      </div>

      <input
        ref={inputRef}
        placeholder={placeholder}
        id="search-input"
        className="input"
        type="text"
        value={query}
        onChange={handleChange}
        aria-label="Search"
      />

      {query && (
        <button
          type="button"
          className="clear-button"
          onClick={handleClear}
          aria-label="Clear search"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            fill="currentColor"
            className="bi bi-x-circle"
            viewBox="0 0 16 16"
          >
            <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16" />
            <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708" />
          </svg>
        </button>
      )}
    </form>
  );
};

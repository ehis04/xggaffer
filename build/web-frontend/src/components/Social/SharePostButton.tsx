import { useState } from "react";
import type React from "react";
import communityApi from "../../services/api/communityApi";
import "./css/SharePostButton.css";

interface SharePostButtonProps {
  textBody: string;
  className?: string;
  children?: React.ReactNode;
  title?: string;
  onShared?: () => void;
}

export const SharePostButton = ({
  textBody,
  className = "",
  children = "Share",
  title = "Share to community",
  onShared,
}: SharePostButtonProps) => {
  const [status, setStatus] = useState<"idle" | "sharing" | "shared" | "error">(
    "idle",
  );

  const handleShare = async (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    if (status === "sharing") return;

    try {
      setStatus("sharing");
      await communityApi.createPost({ text_body: textBody, visibility: "PB" });
      setStatus("shared");
      onShared?.();
      window.setTimeout(() => setStatus("idle"), 2200);
    } catch (error) {
      console.error("Couldn't share post:", error);
      setStatus("error");
      window.setTimeout(() => setStatus("idle"), 2600);
    }
  };

  const label =
    status === "sharing"
      ? "Sharing..."
      : status === "shared"
        ? "Shared"
        : status === "error"
          ? "Try again"
          : children;

  return (
    <button
      type="button"
      className={`share-post-button ${className}`}
      onClick={handleShare}
      disabled={status === "sharing"}
      title={title}
    >
      {label}
    </button>
  );
};

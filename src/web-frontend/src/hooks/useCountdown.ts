import { useState, useEffect } from "react";

export function useCountdown(from: number, onComplete?: () => void): number {
  const [count, setCount] = useState(from);

  useEffect(() => {
    if (count <= 0) {
      onComplete?.();
      return;
    }
    const id = setInterval(() => {
      setCount((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(id);
  }, [count, onComplete]);

  return count;
}
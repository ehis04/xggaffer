import React from "react";
import styles from "./css/StatusBlock.module.css";

export type StatusVariant = "not-found" | "forbidden" | "unauthenticated" | "error" | "empty";

interface StatusBlockProps {
  variant: StatusVariant;
  title?: string;
  message?: string;
  actions?: React.ReactNode;
}

const VARIANT_DEFAULTS: Record<StatusVariant, { title: string; message: string }> = {
  "not-found":       { title: "Not Found",           message: "The resource you're looking for doesn't exist." },
  "forbidden":       { title: "Access Denied",        message: "You don't have permission to view this." },
  "unauthenticated": { title: "Sign In Required",     message: "Please sign in to continue." },
  "error":           { title: "Something went wrong", message: "An unexpected error occurred. Please try again." },
  "empty":           { title: "Nothing here yet",     message: "There's nothing to display here yet." },
};

const VARIANT_CLASS: Record<StatusVariant, string> = {
  "not-found":       styles.notFound,
  "forbidden":       styles.forbidden,
  "unauthenticated": styles.unauthenticated,
  "error":           styles.error,
  "empty":           styles.empty,
};

const ICON_CLASS: Record<StatusVariant, string> = {
  "not-found":       styles.iconMuted,
  "forbidden":       styles.iconAccent,
  "unauthenticated": styles.iconMuted,
  "error":           styles.iconAccent,
  "empty":           styles.iconMuted,
};

const VARIANT_ICONS: Record<StatusVariant, React.ReactNode> = {
  "not-found": (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <circle cx="12" cy="12" r="10" />
      <path strokeLinecap="round" d="M12 8v4m0 4h.01" />
    </svg>
  ),
  "forbidden": (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 2l8 18H4L12 2z" />
      <path strokeLinecap="round" d="M12 9v4m0 3h.01" />
    </svg>
  ),
  "unauthenticated": (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path strokeLinecap="round" d="M8 11V7a4 4 0 018 0v4" />
    </svg>
  ),
  "error": (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
    </svg>
  ),
  "empty": (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 7h18M3 12h18M3 17h18" />
      <rect x="2" y="4" width="20" height="16" rx="2" />
    </svg>
  ),
};

export function StatusBlock({ variant, title, message, actions }: StatusBlockProps) {
  const defaults = VARIANT_DEFAULTS[variant];
  return (
    <div className={`${styles.container} ${VARIANT_CLASS[variant]}`}>
      <div className={`${styles.icon} ${ICON_CLASS[variant]}`} aria-hidden="true">
        {VARIANT_ICONS[variant]}
      </div>
      <h2 className={styles.title}>{title ?? defaults.title}</h2>
      <p className={styles.message}>{message ?? defaults.message}</p>
      {actions && <div className={styles.actions}>{actions}</div>}
    </div>
  );
}
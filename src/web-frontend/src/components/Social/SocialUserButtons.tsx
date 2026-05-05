import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/useAuth";
import "./css/SocialUserButtons.css";
import { useEffect, useMemo, useRef, useState } from "react";
import communityApi from "../../services/api/communityApi";
import type { NotificationItem } from "../../services/api/communityApi";
import usersApi from "../../services/api/usersApi";

const MAX_NOTIFICATIONS_TO_SHOW = 8;

export const SocialUserButtons = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
      navigate("/", { replace: true });
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoadingNotifications, setIsLoadingNotifications] = useState(false);
  const [notificationsError, setNotificationsError] = useState<string | null>(null);
  const [notificationActionError, setNotificationActionError] = useState<string | null>(null);
  const [reviewingRequestId, setReviewingRequestId] = useState<number | null>(null);
  const [hasFetchedNotifications, setHasFetchedNotifications] = useState(false);
  const notificationsRef = useRef<HTMLDivElement | null>(null);

  const unreadCount = useMemo(
    () => notifications.filter((notification) => !notification.is_read).length,
    [notifications]
  );

  const orderedNotifications = useMemo(() => {
    const sorted = [...notifications].sort((a, b) => {
      if (a.is_read !== b.is_read) {
        return a.is_read ? 1 : -1;
      }
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
    return sorted.slice(0, MAX_NOTIFICATIONS_TO_SHOW);
  }, [notifications]);

  useEffect(() => {
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (
        notificationsRef.current &&
        event.target instanceof Node &&
        !notificationsRef.current.contains(event.target)
      ) {
        setIsNotificationsOpen(false);
      }
    };

    if (isNotificationsOpen) {
      document.addEventListener("mousedown", closeOnOutsideClick);
    }

    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
    };
  }, [isNotificationsOpen]);

  useEffect(() => {
    if (!isNotificationsOpen || hasFetchedNotifications) return;

    const fetchNotifications = async () => {
      setIsLoadingNotifications(true);
      setNotificationsError(null);
      try {
        const response = await communityApi.getNotifications({ pageSize: 25 });
        setNotifications(response.results ?? []);
        setHasFetchedNotifications(true);
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "Unable to load notifications right now.";
        setNotificationsError(message);
      } finally {
        setIsLoadingNotifications(false);
      }
    };

    void fetchNotifications();
  }, [hasFetchedNotifications, isNotificationsOpen]);

  const getNotificationMessage = (notification: NotificationItem) => {
    const actor = notification.triggered_by?.username ?? "Someone";
    switch (notification.notification_type) {
      case "L":
        return `@${actor} liked your post`;
      case "C":
        return `@${actor} commented on your post`;
      case "RY":
        return `@${actor} replied to your comment`;
      case "M":
        return `@${actor} mentioned you`;
      case "NF":
        return `@${actor} followed you`;
      case "FR":
        return `@${actor} sent you a follow request`;
      case "FA":
        return `@${actor} accepted your follow request`;
      case "R":
        return `@${actor} reposted your content`;
      default:
        return `@${actor} sent you a notification`;
    }
  };

  const handleNotificationClick = async (notificationId: number) => {
    const targetNotification = notifications.find((item) => item.id === notificationId);
    if (!targetNotification || targetNotification.is_read) {
      return;
    }

    setNotifications((current) =>
      current.map((item) =>
        item.id === notificationId ? { ...item, is_read: true } : item
      )
    );

    try {
      await communityApi.markNotificationAsRead(notificationId);
    } catch {
      setNotifications((current) =>
        current.map((item) =>
          item.id === notificationId ? { ...item, is_read: false } : item
        )
      );
    }
  };

  const handleFollowRequestReview = async (
    notification: NotificationItem,
    action: "accept" | "decline"
  ) => {
    if (!notification.target_id) return;

    setReviewingRequestId(notification.target_id);
    setNotificationActionError(null);

    try {
      if (action === "accept") {
        await usersApi.acceptFollowRequest(notification.target_id);
      } else {
        await usersApi.declineFollowRequest(notification.target_id);
      }

      setNotifications((current) =>
        current.map((item) =>
          item.id === notification.id
            ? {
                ...item,
                is_read: true,
                follow_request_status: action === "accept" ? "A" : "D",
              }
            : item
        )
      );
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : `Unable to ${action} this follow request.`;
      setNotificationActionError(message);
    } finally {
      setReviewingRequestId(null);
    }
  };

  return (
    <div className="socialuserbuttons">
      <div className="notifications-button" ref={notificationsRef}>
        <button
          type="button"
          className="social-action-button"
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            setIsNotificationsOpen((current) => !current);
          }}
          aria-expanded={isNotificationsOpen}
          aria-label="Toggle notifications"
        >
          <svg
            className="social-button-icon"
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            fill="currentColor"
            viewBox="0 0 16 16"
          >
            <path d="M8 16a2 2 0 0 0 2-2H6a2 2 0 0 0 2 2M8 1.918l-.797.161A4 4 0 0 0 4 6c0 .628-.134 2.197-.459 3.742-.16.767-.376 1.566-.663 2.258h10.244c-.287-.692-.502-1.49-.663-2.258C12.134 8.197 12 6.628 12 6a4 4 0 0 0-3.203-3.92zM14.22 12c.223.447.481.801.78 1H1c.299-.199.557-.553.78-1C2.68 10.2 3 6.88 3 6c0-2.42 1.72-4.44 4.005-4.901a1 1 0 1 1 1.99 0A5 5 0 0 1 13 6c0 .88.32 4.2 1.22 6" />
          </svg>
          {unreadCount > 0 && (
            <span className="notifications-badge" aria-label={`${unreadCount} unread notifications`}>
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </button>
        {isNotificationsOpen && (
          <div className="notifications-dropdown" role="menu" aria-label="Notifications">
            <div className="notifications-dropdown-header">Notifications</div>
            {isLoadingNotifications && (
              <div className="notifications-dropdown-state">Loading notifications...</div>
            )}
            {!isLoadingNotifications && notificationsError && (
              <div className="notifications-dropdown-state notifications-dropdown-error">
                {notificationsError}
              </div>
            )}
            {!isLoadingNotifications && notificationActionError && (
              <div className="notifications-dropdown-state notifications-dropdown-error">
                {notificationActionError}
              </div>
            )}
            {!isLoadingNotifications &&
              !notificationsError &&
              notifications.length === 0 && (
                <div className="notifications-dropdown-state">No notifications yet.</div>
              )}
            {!isLoadingNotifications && !notificationsError && orderedNotifications.length > 0 && (
              <ul className="notifications-list">
                {orderedNotifications.map((notification) => (
                  <li
                    key={notification.id}
                    className={`notifications-list-item ${notification.is_read ? "" : "is-unread"}`}
                    onClick={() => void handleNotificationClick(notification.id)}
                  >
                    <p className="notifications-list-item-title">
                      {getNotificationMessage(notification)}
                    </p>
                    <span className="notifications-list-item-time">
                      {new Date(notification.created_at).toLocaleString()}
                    </span>
                    {notification.notification_type === "FR" &&
                      notification.follow_request_status === "P" &&
                      notification.target_id && (
                        <div
                          className="notifications-follow-actions"
                          onClick={(event) => event.stopPropagation()}
                        >
                          <button
                            type="button"
                            className="notifications-follow-action secondary"
                            disabled={reviewingRequestId === notification.target_id}
                            onClick={() =>
                              void handleFollowRequestReview(notification, "decline")
                            }
                          >
                            Decline
                          </button>
                          <button
                            type="button"
                            className="notifications-follow-action primary"
                            disabled={reviewingRequestId === notification.target_id}
                            onClick={() =>
                              void handleFollowRequestReview(notification, "accept")
                            }
                          >
                            Accept
                          </button>
                        </div>
                      )}
                    {notification.notification_type === "FR" &&
                      notification.follow_request_status &&
                      notification.follow_request_status !== "P" && (
                        <span className="notifications-follow-reviewed">
                          {notification.follow_request_status === "A" ? "Accepted" : "Declined"}
                        </span>
                      )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
      <div className="chat-button">
        <button style={{ background: "none", border: "none", cursor: "pointer" }}>
          <svg
            className="social-button-icon"
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            fill="currentColor"
            viewBox="0 0 16 16"
          >
            <path d="M2.678 11.894a1 1 0 0 1 .287.801 11 11 0 0 1-.398 2c1.395-.323 2.247-.697 2.634-.893a1 1 0 0 1 .71-.074A8 8 0 0 0 8 14c3.996 0 7-2.807 7-6s-3.004-6-7-6-7 2.808-7 6c0 1.468.617 2.83 1.678 3.894m-.493 3.905a22 22 0 0 1-.713.129c-.2.032-.352-.176-.273-.362a10 10 0 0 0 .244-.637l.003-.01c.248-.72.45-1.548.524-2.319C.743 11.37 0 9.76 0 8c0-3.866 3.582-7 8-7s8 3.134 8 7-3.582 7-8 7a9 9 0 0 1-2.347-.306c-.52.263-1.639.742-3.468 1.105" />
          </svg>
        </button>
      </div>
      <div className="logout-button">
        <button onClick={handleLogout} style={{ background: "none", border: "none", cursor: "pointer" }}>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            fill="currentColor"
            className="social-button-icon"
            viewBox="0 0 16 16"
          >
            <path d="M7.5 1v7h1V1z" />
            <path d="M3 8.812a5 5 0 0 1 2.578-4.375l-.485-.874A6 6 0 1 0 11 3.616l-.501.865A5 5 0 1 1 3 8.812" />
          </svg>
        </button>
      </div>
    </div>
  );
};

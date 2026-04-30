import { useState, useEffect, useRef } from "react";
import type { ProfileData } from "./types/ProfileTypes";
import "./css/EditProfile.css";
import { ProfileButton } from "../Buttons/ProfileButton";

type Visibility = "PB" | "PR";

interface EditProfileForm {
  display_name: string;
  bio: string;
  gender: string;
  date_of_birth: string;
  visibility: Visibility;
  profile_picture?: File | null;
}

interface EditProfileProps {
  isOpen: boolean;
  userData: ProfileData | null;
  onClose: () => void;
  onSave: (form: EditProfileForm) => Promise<void> | void;
}

const VISIBILITY_OPTIONS: {
  value: Visibility;
  label: string;
  desc: string;
}[] = [
  {
    value: "PB",
    label: "Public",
    desc: "Anyone can see your profile",
  },
  {
    value: "PR",
    label: "Private",
    desc: "Only you can see your profile",
  },
];

export const EditProfile = ({
  isOpen,
  userData,
  onClose,
  onSave,
}: EditProfileProps) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [form, setForm] = useState<EditProfileForm>({
    display_name: "",
    bio: "",
    gender: "NS",
    date_of_birth: "",
    visibility: "PB",
    profile_picture: null,
  });
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileError, setFileError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (userData) {
      setForm({
        display_name: userData.display_name ?? "",
        bio: userData.bio ?? "",
        gender: userData.gender || "NS",
        date_of_birth: userData.date_of_birth ?? "",
        visibility: userData.visibility === "PR" || userData.visibility === "PRIVATE" ? "PR" : "PB",
        profile_picture: null,
      });
      setPreviewUrl(null);
      setFileError("");
    }
  }, [userData]);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
      setFileError("Please choose a JPEG, PNG, or WebP image.");
      e.target.value = "";
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setFileError("Profile photos must be 5MB or smaller.");
      e.target.value = "";
      return;
    }

    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setForm((f) => ({ ...f, profile_picture: file }));
    setPreviewUrl(URL.createObjectURL(file));
    setFileError("");
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave(form);
    } finally {
      setIsSaving(false);
    }
  };

  const profileImage = previewUrl || userData?.profile_image || undefined;

  return (
    <div
      className={`epm-backdrop${isOpen ? " epm-backdrop--open" : ""}`}
      onClick={handleBackdropClick}
    >
      <div
        className="epm-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="epm-title"
      >
        <div className="epm-header">
          <span className="epm-title" id="epm-title">
            Edit Profile
          </span>
          <div className="epm-header-actions">
            <button className="epm-close" onClick={onClose}>
              X
            </button>
            <button className="epm-save" onClick={handleSave} disabled={isSaving}>
              {isSaving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>

        <div className="epm-body">
          <div className="epm-avatar-section">
            <ProfileButton
              username={userData?.username ?? ""}
              profileImage={profileImage}
              size="large"
              onClick={() => undefined}
            />
            <div className="epm-avatar-info">
              <div className="epm-avatar-name">
                {userData?.display_name || userData?.username}
              </div>
              <div className="epm-avatar-hint">Profile photo</div>
              <input
                ref={fileInputRef}
                className="epm-file-input"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
              />
              <button
                className="epm-btn-photo"
                type="button"
                onClick={() => fileInputRef.current?.click()}
              >
                Change photo
              </button>
              {form.profile_picture && (
                <div className="epm-photo-file">{form.profile_picture.name}</div>
              )}
              {fileError && <div className="epm-file-error">{fileError}</div>}
            </div>
          </div>

          <div className="epm-field">
            <label className="epm-label" htmlFor="epm-display-name">
              Display name
            </label>
            <input
              className="epm-input"
              id="epm-display-name"
              type="text"
              value={form.display_name}
              maxLength={60}
              placeholder="Your display name"
              onChange={(e) =>
                setForm((f) => ({ ...f, display_name: e.target.value }))
              }
            />
            <div className="epm-char-count">{form.display_name.length}/60</div>
          </div>

          <div className="epm-field">
            <label className="epm-label" htmlFor="epm-bio">
              Bio
            </label>
            <textarea
              className="epm-textarea"
              id="epm-bio"
              value={form.bio}
              maxLength={200}
              placeholder="Tell people about yourself..."
              onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))}
            />
            <div className="epm-char-count">{form.bio.length}/200</div>
          </div>


          <div className="epm-field">
            <label className="epm-label" htmlFor="epm-gender">
              Gender
            </label>
            <select
              className="epm-select"
              id="epm-gender"
              value={form.gender}
              onChange={(e) =>
                setForm((f) => ({ ...f, gender: e.target.value }))
              }
            >
              <option value="NS">Prefer not to say</option>
              <option value="M">Male</option>
              <option value="F">Female</option>
              <option value="O">Other</option>
            </select>
          </div>

          <div className="epm-field">
            <label className="epm-label" htmlFor="epm-dob">
              Date of birth
            </label>
            <input
              className="epm-input"
              id="epm-dob"
              type="date"
              value={form.date_of_birth}
              onChange={(e) =>
                setForm((f) => ({ ...f, date_of_birth: e.target.value }))
              }
            />
            <div className="epm-hint">
              Not shown publicly — used for age verification only.
            </div>
          </div>

          <div className="epm-field">
            <span className="epm-label">Profile visibility</span>
            <div className="epm-visibility-options">
              {VISIBILITY_OPTIONS.map((opt) => (
                <div
                  key={opt.value}
                  className={`epm-vis-option${form.visibility === opt.value ? " epm-vis-option--selected" : ""}`}
                  onClick={() =>
                    setForm((f) => ({ ...f, visibility: opt.value }))
                  }
                >
                  <div
                    className={`epm-vis-label${form.visibility === opt.value ? " epm-vis-label--selected" : ""}`}
                  >
                    {opt.label}
                  </div>
                  <div className="epm-vis-desc">{opt.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

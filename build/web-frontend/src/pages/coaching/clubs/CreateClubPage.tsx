import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../../services/api/client';
import { clubsApi } from '../../../services/api';
import type {
  ClubType,
  CreateClubPayload,
  DirectoryVisibility,
  FictionalBasis,
} from '../../../types/club';
import styles from './css/CreateClubPage.module.css';

const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email.trim());
};

const COUNTRIES = [
  { code: '', label: 'Select a country' },
  { code: 'IE', label: 'Ireland' },
  { code: 'GB', label: 'United Kingdom' },
  { code: 'US', label: 'United States' },
  { code: 'ES', label: 'Spain' },
  { code: 'DE', label: 'Germany' },
  { code: 'FR', label: 'France' },
  { code: 'IT', label: 'Italy' },
  { code: 'PT', label: 'Portugal' },
  { code: 'NL', label: 'Netherlands' },
  { code: 'BE', label: 'Belgium' },
  { code: 'BR', label: 'Brazil' },
  { code: 'AR', label: 'Argentina' },
  { code: 'MX', label: 'Mexico' },
  { code: 'JP', label: 'Japan' },
  { code: 'KR', label: 'South Korea' },
  { code: 'AU', label: 'Australia' },
  { code: 'CA', label: 'Canada' },
  { code: 'SE', label: 'Sweden' },
  { code: 'NO', label: 'Norway' },
  { code: 'DK', label: 'Denmark' },
  { code: 'PL', label: 'Poland' },
  { code: 'AT', label: 'Austria' },
  { code: 'CH', label: 'Switzerland' },
  { code: 'TR', label: 'Turkey' },
  { code: 'NG', label: 'Nigeria' },
  { code: 'GH', label: 'Ghana' },
  { code: 'ZA', label: 'South Africa' },
  { code: 'EG', label: 'Egypt' },
  { code: 'MA', label: 'Morocco' },
  { code: 'CN', label: 'China' },
  { code: 'IN', label: 'India' },
  { code: 'SA', label: 'Saudi Arabia' },
  { code: 'AE', label: 'United Arab Emirates' },
  { code: 'QA', label: 'Qatar' },
];

type RoleCapability = boolean | null;

interface ClubCreateFormState {
  name: string;
  description: string;
  city: string;
  country: string;
  stadium: string;
  division: string;
  achievements: string;
  visibility: 'public' | 'private';
  club_type: ClubType;
  fictional_basis: FictionalBasis;
  source_real_club_name: string;
  directory_visibility: DirectoryVisibility;
  verification_contact_name: string;
  verification_contact_role: string;
  verification_contact_email: string;
  verification_evidence_text: string;
  verification_evidence_url: string;
}

const collectRoleValues = (value: unknown): string[] => {
  if (typeof value === 'string') {
    return [value];
  }

  if (Array.isArray(value)) {
    return value.flatMap(collectRoleValues);
  }

  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    return [
      ...collectRoleValues(record.role),
      ...collectRoleValues(record.roles),
      ...collectRoleValues(record.results),
      ...collectRoleValues(record.data),
      ...collectRoleValues(record.code),
      ...collectRoleValues(record.name),
    ];
  }

  return [];
};

const isCoachCapablePayload = (payload: unknown): boolean => {
  return collectRoleValues(payload).some((value) => {
    const normalised = value.trim().toLowerCase();
    return normalised === 'c' || normalised === 'coach';
  });
};

const initialForm: ClubCreateFormState = {
  name: '',
  description: '',
  city: '',
  country: '',
  stadium: '',
  division: '',
  achievements: '',
  visibility: 'private',
  club_type: 'user_fictional',
  fictional_basis: 'original',
  source_real_club_name: '',
  directory_visibility: 'listed',
  verification_contact_name: '',
  verification_contact_role: '',
  verification_contact_email: '',
  verification_evidence_text: '',
  verification_evidence_url: '',
};

const normaliseError = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === 'string') {
    return error;
  }

  if (error && typeof error === 'object') {
    const values = Object.values(error as Record<string, unknown>).flatMap((value) => {
      if (Array.isArray(value)) {
        return value.map(String);
      }
      return [String(value)];
    });

    if (values.length > 0) {
      return values.join(' ');
    }
  }

  return 'Failed to create club.';
};

const CreateClubPage: React.FC = () => {
  const navigate = useNavigate();

  const [form, setForm] = useState<ClubCreateFormState>(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [roleCapability, setRoleCapability] = useState<RoleCapability>(null);
  const [roleCheckError, setRoleCheckError] = useState<string | null>(null);
  const [emailTouched, setEmailTouched] = useState(false);

  useEffect(() => {
    const loadRoleCapability = async () => {
      try {
        const payload = await apiClient.get<unknown>('/users/profile/role/');
        setRoleCapability(isCoachCapablePayload(payload));
        setRoleCheckError(null);
      } catch {
        setRoleCapability(null);
        setRoleCheckError('Role capability could not be confirmed on this page. Backend rules still apply.');
      }
    };

    void loadRoleCapability();
  }, []);

  const isFictional = form.club_type === 'user_fictional';
  const isRealNonPro = form.club_type === 'user_real_non_pro';
  const isRealClubCopy = isFictional && form.fictional_basis === 'real_club_copy';

  const creationBlocked = roleCapability === false;

  const handleChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = event.target;

    // Track email field touches for validation feedback
    if (name === 'verification_contact_email') {
      setEmailTouched(true);
    }

    setForm((prev) => {
      const next = { ...prev, [name]: value };

      if (name === 'club_type' && value === 'user_real_non_pro') {
        next.fictional_basis = 'original';
      }

      if (name === 'club_type' && value !== 'user_real_non_pro') {
        next.verification_contact_name = prev.verification_contact_name;
        next.verification_contact_role = prev.verification_contact_role;
        next.verification_contact_email = prev.verification_contact_email;
        next.verification_evidence_text = prev.verification_evidence_text;
        next.verification_evidence_url = prev.verification_evidence_url;
        // Reset email validation feedback when changing away from real non-pro
        setEmailTouched(false);
      }

      return next;
    });
  };

  const canSubmit = useMemo(() => {
    if (!form.name.trim()) {
      return false;
    }

    if (creationBlocked) {
      return false;
    }

    if (isRealClubCopy && !form.source_real_club_name.trim()) {
      return false;
    }

    if (isRealNonPro) {
      return Boolean(
        form.verification_contact_name.trim() &&
        form.verification_contact_role.trim() &&
        form.verification_contact_email.trim() &&
        isValidEmail(form.verification_contact_email) &&
        (form.verification_evidence_text.trim() || form.verification_evidence_url.trim())
      );
    }

    return true;
  }, [creationBlocked, form, isRealClubCopy, isRealNonPro]);

  const buildPayload = (): CreateClubPayload => {
    const payload: CreateClubPayload = {
      name: form.name.trim(),
      description: form.description.trim(),
      city: form.city.trim(),
      country: form.country,
      stadium: form.stadium.trim(),
      division: form.division.trim(),
      achievements: form.achievements.trim(),
      visibility: form.visibility,
      club_type: form.club_type,
      directory_visibility: form.directory_visibility,
    };

    if (isFictional) {
      payload.fictional_basis = form.fictional_basis;
      if (isRealClubCopy) {
        payload.source_real_club_name = form.source_real_club_name.trim();
      }
    }

    if (isRealNonPro) {
      payload.verification_contact_name = form.verification_contact_name.trim();
      payload.verification_contact_role = form.verification_contact_role.trim();
      payload.verification_contact_email = form.verification_contact_email.trim();
      payload.verification_evidence_text = form.verification_evidence_text.trim();
      payload.verification_evidence_url = form.verification_evidence_url.trim();
      if (form.source_real_club_name.trim()) {
        payload.source_real_club_name = form.source_real_club_name.trim();
      }
    }

    return Object.fromEntries(
      Object.entries(payload).filter(([, value]) => value !== '')
    ) as CreateClubPayload;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!canSubmit) {
      setError('Please complete the required fields for the selected club type.');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const club = await clubsApi.create(buildPayload());
      navigate(`/clubs/${club.id}/`);
    } catch (err) {
      setError(normaliseError(err));
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.container}>
      <section className={styles.header}>
        <div>
          <h1 className={styles.title}>Create Club</h1>
          <p className={styles.subtitle}>
            Create a fictional club or a verified real non-pro club representation. System professional clubs remain platform-managed.
          </p>
        </div>

        <button className={styles.backButton} onClick={() => navigate('/clubs')}>
          Back to Clubs
        </button>
      </section>

      {error && <div className={styles.error}>{error}</div>}
      {roleCheckError && <div className={styles.notice}>{roleCheckError}</div>}
      {creationBlocked && (
        <div className={styles.notice}>
          Club creation is reserved for coach-capable users. Your current account roles do not include coach capability.
        </div>
      )}

      <form className={styles.form} onSubmit={handleSubmit}>
        <section className={styles.panel}>
          <h2 className={styles.sectionTitle}>Identity</h2>

          <div className={styles.field}>
            <label className={styles.label}>Club Name *</label>
            <input
              className={styles.input}
              name="name"
              value={form.name}
              onChange={handleChange}
              placeholder="e.g. Ranelagh Athletic"
              required
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Description</label>
            <textarea
              className={styles.textarea}
              name="description"
              value={form.description}
              onChange={handleChange}
              placeholder="A short description of your club"
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Club Type *</label>
            <select
              className={styles.input}
              name="club_type"
              value={form.club_type}
              onChange={handleChange}
            >
              <option value="user_fictional">Fictional club</option>
              <option value="user_real_non_pro">Real non-pro club</option>
            </select>
          </div>

          {isFictional && (
            <>
              <div className={styles.field}>
                <label className={styles.label}>Fictional Basis *</label>
                <select
                  className={styles.input}
                  name="fictional_basis"
                  value={form.fictional_basis}
                  onChange={handleChange}
                >
                  <option value="original">Original fictional club</option>
                  <option value="real_club_copy">Unofficial copy of a real club</option>
                </select>
              </div>

              {isRealClubCopy && (
                <div className={styles.field}>
                  <label className={styles.label}>Reference Real Club Name *</label>
                  <input
                    className={styles.input}
                    name="source_real_club_name"
                    value={form.source_real_club_name}
                    onChange={handleChange}
                    placeholder="e.g. Shamrock Rovers"
                    required
                  />
                </div>
              )}
            </>
          )}

          {isRealNonPro && (
            <>
              <div className={styles.field}>
                <label className={styles.label}>Real Club Name</label>
                <input
                  className={styles.input}
                  name="source_real_club_name"
                  value={form.source_real_club_name}
                  onChange={handleChange}
                  placeholder="e.g. Local Town AFC"
                />
              </div>

              <div className={styles.noticeBlock}>
                Creating a real non-pro club representation requires lightweight verification details and will default to pending verification.
              </div>
            </>
          )}
        </section>

        <section className={styles.panel}>
          <h2 className={styles.sectionTitle}>Discovery and Access</h2>

          <div className={styles.row}>
            <div className={styles.field}>
              <label className={styles.label}>Profile Visibility</label>
              <select
                className={styles.input}
                name="visibility"
                value={form.visibility}
                onChange={handleChange}
              >
                <option value="private">Private</option>
                <option value="public">Public</option>
              </select>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Directory Visibility</label>
              <select
                className={styles.input}
                name="directory_visibility"
                value={form.directory_visibility}
                onChange={handleChange}
              >
                <option value="listed">Listed in browse</option>
                <option value="hidden_code_only">Hidden, code lookup only</option>
              </select>
            </div>
          </div>

          <div className={styles.noticeBlock}>
            User-created clubs default to approval-required join policy. Hidden clubs receive a generated join code after creation.
          </div>
        </section>

        <section className={styles.panel}>
          <h2 className={styles.sectionTitle}>Location and Competition</h2>

          <div className={styles.row}>
            <div className={styles.field}>
              <label className={styles.label}>City</label>
              <input
                className={styles.input}
                name="city"
                value={form.city}
                onChange={handleChange}
                placeholder="e.g. Dublin"
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Country</label>
              <select
                className={styles.input}
                name="country"
                value={form.country}
                onChange={handleChange}
              >
                {COUNTRIES.map((country) => (
                  <option key={country.code} value={country.code}>
                    {country.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className={styles.row}>
            <div className={styles.field}>
              <label className={styles.label}>Stadium</label>
              <input
                className={styles.input}
                name="stadium"
                value={form.stadium}
                onChange={handleChange}
                placeholder="e.g. Tolka Park"
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Division</label>
              <input
                className={styles.input}
                name="division"
                value={form.division}
                onChange={handleChange}
                placeholder="e.g. Leinster Senior League"
              />
            </div>
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Achievements</label>
            <textarea
              className={styles.textarea}
              name="achievements"
              value={form.achievements}
              onChange={handleChange}
              placeholder="Trophies, honours, or notable milestones"
            />
          </div>
        </section>

        {isRealNonPro && (
          <section className={styles.panel}>
            <h2 className={styles.sectionTitle}>Verification Details</h2>

            <div className={styles.row}>
              <div className={styles.field}>
                <label className={styles.label}>Contact Name *</label>
                <input
                  className={styles.input}
                  name="verification_contact_name"
                  value={form.verification_contact_name}
                  onChange={handleChange}
                  placeholder="e.g. Alex Byrne"
                  required={isRealNonPro}
                />
              </div>

              <div className={styles.field}>
                <label className={styles.label}>Contact Role *</label>
                <input
                  className={styles.input}
                  name="verification_contact_role"
                  value={form.verification_contact_role}
                  onChange={handleChange}
                  placeholder="e.g. Manager"
                  required={isRealNonPro}
                />
              </div>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Contact Email *</label>
              <input
                className={styles.input}
                type="email"
                name="verification_contact_email"
                value={form.verification_contact_email}
                onChange={handleChange}
                placeholder="e.g. manager@club.ie"
                required={isRealNonPro}
              />
              {emailTouched && form.verification_contact_email.trim() && !isValidEmail(form.verification_contact_email) && (
                <div style={{ color: '#fca5a5', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                  Please enter a valid email address (e.g. manager@club.ie)
                </div>
              )}
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Evidence Summary *</label>
              <textarea
                className={styles.textarea}
                name="verification_evidence_text"
                value={form.verification_evidence_text}
                onChange={handleChange}
                placeholder="Explain the evidence supporting your right to manage this club representation."
                required={isRealNonPro}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Evidence URL</label>
              <input
                className={styles.input}
                type="url"
                name="verification_evidence_url"
                value={form.verification_evidence_url}
                onChange={handleChange}
                placeholder="Optional supporting webpage"
              />
            </div>
          </section>
        )}

        <div className={styles.formActions}>
          <button
            className={styles.submitButton}
            type="submit"
            disabled={submitting || !canSubmit}
          >
            {submitting ? 'Creating...' : 'Create Club'}
          </button>

          <button
            className={styles.secondaryButton}
            type="button"
            onClick={() => navigate('/clubs')}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default CreateClubPage;
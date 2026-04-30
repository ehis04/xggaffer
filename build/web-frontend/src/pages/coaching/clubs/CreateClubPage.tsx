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
import { Sidebar } from '../../../components/Navigation/SideBar';
import { SocialUserButtons } from '../../../components/Social/SocialUserButtons';

const isValidEmail = (email: string): boolean =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());

const REGIONS = [
  'London', 'Manchester', 'Dublin', 'Birmingham', 'Glasgow',
  'Liverpool', 'Leeds', 'Edinburgh', 'Cardiff', 'Belfast',
  'Cork', 'Galway', 'Madrid', 'Barcelona', 'Berlin',
  'Paris', 'Rome', 'Amsterdam', 'Lisbon', 'Brussels',
];

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
];

const MATCH_FORMATS = ['5v5', '7v7', '9v9', '11v11', 'Futsal'] as const;
const AGE_GROUPS = ['U7', 'U9', 'U11', 'U13', 'U15', 'U16', 'U18', 'U21', 'Adult', 'Veteran'] as const;
const SEASON_STARTS = ['Jan 2025', 'Mar 2025', 'Jun 2025', 'Sep 2025', 'Jan 2026', 'Sep 2026'];

type MatchFormat = (typeof MATCH_FORMATS)[number];

interface ClubCreateFormState {
  name: string;
  short_handle: string;
  description: string;
  city: string;
  country: string;
  stadium: string;
  division: string;
  season_start: string;
  achievements: string;
  match_format: MatchFormat | '';
  age_group: string;
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

const initialForm: ClubCreateFormState = {
  name: '',
  short_handle: '',
  description: '',
  city: '',
  country: '',
  stadium: '',
  division: '',
  season_start: 'Sep 2025',
  achievements: '',
  match_format: '11v11',
  age_group: 'U16',
  visibility: 'public',
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

const collectRoleValues = (value: unknown): string[] => {
  if (typeof value === 'string') return [value];
  if (Array.isArray(value)) return value.flatMap(collectRoleValues);
  if (value && typeof value === 'object') {
    const r = value as Record<string, unknown>;
    return [
      ...collectRoleValues(r.role), ...collectRoleValues(r.roles),
      ...collectRoleValues(r.results), ...collectRoleValues(r.data),
      ...collectRoleValues(r.code), ...collectRoleValues(r.name),
    ];
  }
  return [];
};

const isCoachCapablePayload = (payload: unknown): boolean =>
  collectRoleValues(payload).some((v) => {
    const n = v.trim().toLowerCase();
    return n === 'c' || n === 'coach';
  });

const normaliseError = (error: unknown): string => {
  if (error instanceof Error) return error.message;
  if (typeof error === 'string') return error;
  if (error && typeof error === 'object') {
    const values = Object.values(error as Record<string, unknown>).flatMap((v) =>
      Array.isArray(v) ? v.map(String) : [String(v)]
    );
    if (values.length > 0) return values.join(' ');
  }
  return 'Failed to create club.';
};

const generatePreviewCode = (name: string): string => {
  if (!name.trim()) return '— — — — — —';
  const initials = name
    .split(' ')
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');
  const rand = Math.random().toString(36).slice(2, 6).toUpperCase();
  return `${initials} · ${rand}`;
};

const CreateClubPage: React.FC = () => {
  const navigate = useNavigate();

  const [form, setForm] = useState<ClubCreateFormState>(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [roleCapability, setRoleCapability] = useState<boolean | null>(null);
  const [roleCheckError, setRoleCheckError] = useState<string | null>(null);
  const [emailTouched, setEmailTouched] = useState(false);
  const [codeCopied, setCodeCopied] = useState(false);

  const previewCode = useMemo(() => generatePreviewCode(form.name), [form.name]);

  useEffect(() => {
    const load = async () => {
      try {
        const payload = await apiClient.get<unknown>('/users/profile/role/');
        setRoleCapability(isCoachCapablePayload(payload));
      } catch {
        setRoleCapability(null);
        setRoleCheckError('Role capability could not be confirmed. Backend rules still apply.');
      }
    };
    void load();
  }, []);

  const isFictional = form.club_type === 'user_fictional';
  const isRealNonPro = form.club_type === 'user_real_non_pro';
  const isRealClubCopy = isFictional && form.fictional_basis === 'real_club_copy';
  const creationBlocked = roleCapability === false;

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    if (name === 'verification_contact_email') setEmailTouched(true);
    setForm((prev) => {
      const next = { ...prev, [name]: value };
      if (name === 'name') {
        next.short_handle = value
          .toLowerCase()
          .replace(/[^a-z0-9\s-]/g, '')
          .trim()
          .replace(/\s+/g, '-');
      }
      if (name === 'club_type' && value === 'user_real_non_pro') {
        next.fictional_basis = 'original';
      }
      if (name === 'club_type' && value !== 'user_real_non_pro') {
        setEmailTouched(false);
      }
      return next;
    });
  };

  const canSubmit = useMemo(() => {
    if (!form.name.trim()) return false;
    if (creationBlocked) return false;
    if (isRealClubCopy && !form.source_real_club_name.trim()) return false;
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
      if (isRealClubCopy) payload.source_real_club_name = form.source_real_club_name.trim();
    }
    if (isRealNonPro) {
      payload.verification_contact_name = form.verification_contact_name.trim();
      payload.verification_contact_role = form.verification_contact_role.trim();
      payload.verification_contact_email = form.verification_contact_email.trim();
      payload.verification_evidence_text = form.verification_evidence_text.trim();
      payload.verification_evidence_url = form.verification_evidence_url.trim();
      if (form.source_real_club_name.trim()) payload.source_real_club_name = form.source_real_club_name.trim();
    }
    return Object.fromEntries(
      Object.entries(payload).filter(([, v]) => v !== '')
    ) as CreateClubPayload;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) { setError('Please complete the required fields.'); return; }
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

  const handleCopyCode = () => {
    void navigator.clipboard.writeText(previewCode);
    setCodeCopied(true);
    setTimeout(() => setCodeCopied(false), 2000);
  };

  const previewInitials = form.name
    ? form.name.split(' ').map((w) => w[0]?.toUpperCase() ?? '').slice(0, 2).join('')
    : '?';

  const previewTags = [
    form.match_format,
    form.age_group,
    form.city,
  ].filter(Boolean);

  const visibilityLabel = form.directory_visibility === 'listed' ? 'Public' : 'Private';
  const divisionLabel = form.division || '';

  return (
    <div className={styles.createClubShell}>
      <div className="sidebar-section">
        <Sidebar />
      </div>

      <div className={styles.createClubMain}>

        <header className={styles.createClubHeader}>
          <div className={styles.createClubHeaderLeft}>
            <span className={styles.createClubHeaderLabel}>Coaching</span>
            <span className={styles.createClubHeaderSep}>·</span>
            <span className={styles.createClubHeaderTitle}>Clubs</span>
          </div>
          <div className={styles.createClubHeaderMiddle}>
          </div>
          <div className={styles.createClubHeaderRight}>
            <SocialUserButtons />
          </div>
        </header>

        <div className={styles.createClubContent}>

          <section className={styles.createClubHero}>
            <div className={styles.createClubHeroBreadcrumb}>CREATE</div>
            <h1 className={styles.createClubHeroTitle}>Start a new club.</h1>
            <p className={styles.createClubHeroSub}>
              A club brings your squad together rosters, sessions, fixtures, and messaging under one crest.
            </p>
          </section>

          {error && <div className={styles.createClubError}>{error}</div>}
          {roleCheckError && <div className={styles.createClubNotice}>{roleCheckError}</div>}
          {creationBlocked && (
            <div className={styles.createClubNotice}>
              Club creation is reserved for coach-capable users. Your current account roles do not include coach capability.
            </div>
          )}

          <form className={styles.createClubForm} onSubmit={handleSubmit}>

            <div className={styles.createClubPanel}>
              <div className={styles.createClubPanelHead}>
                <h2 className={styles.createClubPanelTitle}>Club details</h2>
                <span className={styles.createClubPanelRequired}>REQUIRED</span>
              </div>

              <div className={styles.createClubField}>
                <label className={styles.createClubLabel}>CLUB NAME</label>
                <input
                  className={styles.createClubInput}
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  placeholder="Riverside FC U16"
                  required
                />
              </div>

              <div className={styles.createClubRow}>
                <div className={styles.createClubField}>
                  <label className={styles.createClubLabel}>SHORT HANDLE</label>
                  <input
                    className={styles.createClubInput}
                    name="short_handle"
                    value={form.short_handle}
                    onChange={handleChange}
                    placeholder="riverside-u16"
                  />
                </div>
                <div className={styles.createClubField}>
                  <label className={styles.createClubLabel}>REGION</label>
                  <select
                    className={styles.createClubSelect}
                    name="city"
                    value={form.city}
                    onChange={handleChange}
                  >
                    <option value="">Select a region</option>
                    {REGIONS.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className={styles.createClubField}>
                <label className={styles.createClubLabel}>BIO</label>
                <textarea
                  className={styles.createClubTextarea}
                  name="description"
                  value={form.description}
                  onChange={handleChange}
                  placeholder="Competitive youth programme focused on tactical development and league play."
                  rows={4}
                />
              </div>

              <div className={styles.createClubRow}>
                <div className={styles.createClubField}>
                  <label className={styles.createClubLabel}>CLUB TYPE</label>
                  <select
                    className={styles.createClubSelect}
                    name="club_type"
                    value={form.club_type}
                    onChange={handleChange}
                  >
                    <option value="user_fictional">Fictional club</option>
                    <option value="user_real_non_pro">Real non-pro club</option>
                  </select>
                </div>

                {isFictional && (
                  <div className={styles.createClubField}>
                    <label className={styles.createClubLabel}>FICTIONAL BASIS</label>
                    <select
                      className={styles.createClubSelect}
                      name="fictional_basis"
                      value={form.fictional_basis}
                      onChange={handleChange}
                    >
                      <option value="original">Original fictional club</option>
                      <option value="real_club_copy">Unofficial copy of a real club</option>
                    </select>
                  </div>
                )}
              </div>

              {isRealClubCopy && (
                <div className={styles.createClubField}>
                  <label className={styles.createClubLabel}>REFERENCE REAL CLUB NAME *</label>
                  <input
                    className={styles.createClubInput}
                    name="source_real_club_name"
                    value={form.source_real_club_name}
                    onChange={handleChange}
                    placeholder="e.g. Shamrock Rovers"
                    required
                  />
                </div>
              )}

              {isRealNonPro && (
                <div className={styles.createClubField}>
                  <label className={styles.createClubLabel}>REAL CLUB NAME</label>
                  <input
                    className={styles.createClubInput}
                    name="source_real_club_name"
                    value={form.source_real_club_name}
                    onChange={handleChange}
                    placeholder="e.g. Local Town AFC"
                  />
                </div>
              )}
            </div>

            <div className={styles.createClubPanel}>
              <div className={styles.createClubPanelHead}>
                <h2 className={styles.createClubPanelTitle}>Format &amp; age</h2>
              </div>

              <div className={styles.createClubField}>
                <label className={styles.createClubLabel}>MATCH FORMAT</label>
                <div className={styles.createClubFormatPills}>
                  {MATCH_FORMATS.map((f) => (
                    <button
                      key={f}
                      type="button"
                      className={`${styles.createClubFormatPill} ${form.match_format === f ? styles.createClubFormatPillActive : ''}`}
                      onClick={() => setForm((prev) => ({ ...prev, match_format: f }))}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>

              <div className={styles.createClubRow}>
                <div className={styles.createClubField}>
                  <label className={styles.createClubLabel}>AGE GROUP</label>
                  <select
                    className={styles.createClubSelect}
                    name="age_group"
                    value={form.age_group}
                    onChange={handleChange}
                  >
                    {AGE_GROUPS.map((a) => (
                      <option key={a} value={a}>{a}</option>
                    ))}
                  </select>
                </div>

                <div className={styles.createClubField}>
                  <label className={styles.createClubLabel}>DIVISION</label>
                  <input
                    className={styles.createClubInput}
                    name="division"
                    value={form.division}
                    onChange={handleChange}
                    placeholder="County League North"
                  />
                </div>

                <div className={styles.createClubField}>
                  <label className={styles.createClubLabel}>SEASON START</label>
                  <select
                    className={styles.createClubSelect}
                    name="season_start"
                    value={form.season_start}
                    onChange={handleChange}
                  >
                    {SEASON_STARTS.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className={styles.createClubPanel}>
              <div className={styles.createClubPanelHead}>
                <h2 className={styles.createClubPanelTitle}>Visibility</h2>
              </div>

              <div className={styles.createClubVisibilityRow}>
                <button
                  type="button"
                  className={`${styles.createClubVisibilityCard} ${form.directory_visibility === 'listed' ? styles.createClubVisibilityCardActive : ''}`}
                  onClick={() => setForm((prev) => ({ ...prev, directory_visibility: 'listed', visibility: 'public' }))}
                >
                  <div className={styles.createClubVisibilityTitle}>Public</div>
                  <div className={styles.createClubVisibilitySub}>Anyone can discover and request to join.</div>
                </button>

                <button
                  type="button"
                  className={`${styles.createClubVisibilityCard} ${form.directory_visibility === 'hidden_code_only' ? styles.createClubVisibilityCardActive : ''}`}
                  onClick={() => setForm((prev) => ({ ...prev, directory_visibility: 'hidden_code_only', visibility: 'private' }))}
                >
                  <div className={styles.createClubVisibilityTitle}>Private</div>
                  <div className={styles.createClubVisibilitySub}>Invite-only. Never appears in Browse.</div>
                </button>
              </div>
            </div>

            <div className={styles.createClubPanel}>
              <div className={styles.createClubPanelHead}>
                <h2 className={styles.createClubPanelTitle}>Location</h2>
                <span className={styles.createClubPanelOptional}>OPTIONAL</span>
              </div>

              <div className={styles.createClubRow}>
                <div className={styles.createClubField}>
                  <label className={styles.createClubLabel}>COUNTRY</label>
                  <select
                    className={styles.createClubSelect}
                    name="country"
                    value={form.country}
                    onChange={handleChange}
                  >
                    {COUNTRIES.map((c) => (
                      <option key={c.code} value={c.code}>{c.label}</option>
                    ))}
                  </select>
                </div>

                <div className={styles.createClubField}>
                  <label className={styles.createClubLabel}>STADIUM</label>
                  <input
                    className={styles.createClubInput}
                    name="stadium"
                    value={form.stadium}
                    onChange={handleChange}
                    placeholder="e.g. Tolka Park"
                  />
                </div>
              </div>
            </div>

            {isRealNonPro && (
              <div className={styles.createClubPanel}>
                <div className={styles.createClubPanelHead}>
                  <h2 className={styles.createClubPanelTitle}>Verification details</h2>
                  <span className={styles.createClubPanelRequired}>REQUIRED</span>
                </div>

                <div className={styles.createClubNotice} style={{ marginBottom: '1rem' }}>
                  Creating a real non-pro club requires verification details and defaults to pending status.
                </div>

                <div className={styles.createClubRow}>
                  <div className={styles.createClubField}>
                    <label className={styles.createClubLabel}>CONTACT NAME *</label>
                    <input className={styles.createClubInput} name="verification_contact_name" value={form.verification_contact_name} onChange={handleChange} placeholder="e.g. Alex Byrne" required />
                  </div>
                  <div className={styles.createClubField}>
                    <label className={styles.createClubLabel}>CONTACT ROLE *</label>
                    <input className={styles.createClubInput} name="verification_contact_role" value={form.verification_contact_role} onChange={handleChange} placeholder="e.g. Manager" required />
                  </div>
                </div>

                <div className={styles.createClubField}>
                  <label className={styles.createClubLabel}>CONTACT EMAIL *</label>
                  <input
                    className={styles.createClubInput}
                    type="email"
                    name="verification_contact_email"
                    value={form.verification_contact_email}
                    onChange={handleChange}
                    placeholder="e.g. manager@club.ie"
                    required
                  />
                  {emailTouched && form.verification_contact_email.trim() && !isValidEmail(form.verification_contact_email) && (
                    <p className={styles.createClubInputError}>Please enter a valid email address.</p>
                  )}
                </div>

                <div className={styles.createClubField}>
                  <label className={styles.createClubLabel}>EVIDENCE SUMMARY *</label>
                  <textarea className={styles.createClubTextarea} name="verification_evidence_text" value={form.verification_evidence_text} onChange={handleChange} placeholder="Explain the evidence supporting your right to manage this club." rows={3} required />
                </div>

                <div className={styles.createClubField}>
                  <label className={styles.createClubLabel}>EVIDENCE URL</label>
                  <input className={styles.createClubInput} type="url" name="verification_evidence_url" value={form.verification_evidence_url} onChange={handleChange} placeholder="Optional supporting webpage" />
                </div>
              </div>
            )}

            <div className={styles.createClubActions}>
              <button type="button" className={styles.createClubCancelBtn} onClick={() => navigate('/clubs')}>
                Cancel
              </button>
              <div className={styles.createClubActionsRight}>
                <button type="button" className={styles.createClubDraftBtn} disabled={!form.name.trim()}>
                  Save as draft
                </button>
                <button type="submit" className={styles.createClubSubmitBtn} disabled={submitting || !canSubmit}>
                  {submitting ? 'Creating…' : 'Continue →'}
                </button>
              </div>
            </div>
          </form>

          <div className={styles.createClubPanel}>
            <div className={styles.createClubPanelHead}>
              <h2 className={styles.createClubPanelTitle}>Crest &amp; preview</h2>
              <button type="button" className={styles.createClubUploadBtn}>Upload image</button>
            </div>

            <div className={styles.createClubPreviewRow}>
              <div className={styles.createClubPreviewBadge}>
                <span className={styles.createClubPreviewInitials}>{previewInitials}</span>
              </div>
              <div className={styles.createClubPreviewInfo}>
                <div className={styles.createClubPreviewName}>{form.name || 'Club Name'}</div>
                <div className={styles.createClubPreviewMeta}>
                  {previewTags.join(' · ')}
                </div>
                <div className={styles.createClubPreviewTags}>
                  {visibilityLabel && (
                    <span className={styles.createClubPreviewTag}>{visibilityLabel}</span>
                  )}
                  {divisionLabel && (
                    <span className={styles.createClubPreviewTag}>{divisionLabel}</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className={styles.createClubPanel}>
            <div className={styles.createClubPanelHead}>
              <h2 className={styles.createClubPanelTitle}>Invite code</h2>
              <span className={styles.createClubAutoGenBadge}>Auto-generated</span>
            </div>

            <div className={styles.createClubCodeWrap}>
              <div className={styles.createClubCodeInner}>
                <div className={styles.createClubCodeLabel}>JOIN CODE</div>
                <div className={styles.createClubCodeValue}>
                  {previewCode.split('').map((char, i) => (
                    <span key={i} className={char === ' ' || char === '·' ? styles.createClubCodeSep : styles.createClubCodeChar}>
                      {char}
                    </span>
                  ))}
                </div>
              </div>
              <button type="button" className={styles.createClubCopyBtn} onClick={handleCopyCode}>
                {codeCopied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <p className={styles.createClubCodeHint}>
              Share this code with players and assistant coaches — they'll be added on approval.
            </p>
          </div>

        </div>
      </div>
    </div>
  );
};

export default CreateClubPage;
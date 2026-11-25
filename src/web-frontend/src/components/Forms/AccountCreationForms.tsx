import "./css/AccountCreationForms.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../../services/api/client";
import { useAuth } from "../../context/useAuth";

type RoleKey = "Player" | "Coach" | "Referee" | "Fan";

interface RoleConfig {
  value: string;
  label: RoleKey;
  desc: string;
  fields: FieldConfig[];
}

interface FieldConfig {
  id: string;
  label: string;
  type: "text" | "email" | "number" | "select" | "password";
  placeholder?: string;
  options?: string[];
  min?: number;
  max?: number;
  required?: boolean;
}

const PLAYER_POSITIONS = [
  "GK", "RB", "RWB", "CB", "RCB", "CCB", "LCB", "LB", "LWB", "RDM", "CDM", "LDM",
  "CM", "RM", "LM", "RAM", "CAM", "LAM", "RW", "LW", "CF", "ST",
];

const FORMATIONS = [
  "N/A", "3-1-4-2", "3-4-1-2", "3-4-2-1", "3-4-3", "3-5-1-1", "4-1-2-1-2",
  "4-1-2-3", "4-1-3-2", "4-1-4-1", "4-2-1-3", "4-2-2-2", "4-2-3-1",
  "4-2-4", "4-3-1-2", "4-3-2-1", "4-3-3", "4-4-1-1", "4-4-2", "4-5-1",
  "5-2-1-2", "5-2-2-1", "5-2-3", "5-3-2", "5-4-1",
];

const ROLES: RoleConfig[] = [
  {
    value: "P",
    label: "Player",
    desc: "Register as a football player",
    fields: [
      { id: "primary_position", label: "Primary Position", type: "select", options: PLAYER_POSITIONS, required: true },
      { id: "secondary_position", label: "Secondary Position", type: "select", options: ["None", ...PLAYER_POSITIONS] },
      { id: "preferred_foot", label: "Preferred Foot", type: "select", options: ["Left", "Right", "Both"], required: true },
      { id: "height_cm", label: "Height (cm)", type: "number", placeholder: "e.g. 178", min: 100, max: 230 },
      { id: "weight_kg", label: "Weight (kg)", type: "number", placeholder: "e.g. 75", min: 40, max: 150 },
    ],
  },
  {
    value: "C",
    label: "Coach",
    desc: "Register as a team coach",
    fields: [
      { id: "experience_level", label: "Experience Level", type: "select", options: ["Beginner", "Intermediate", "Professional"], required: true },
      { id: "formation_preferences", label: "Preferred Formation", type: "select", options: FORMATIONS },
      { id: "years_experience", label: "Years of Experience", type: "number", placeholder: "e.g. 5", min: 0, max: 50 },
      { id: "club_name", label: "Club Name", type: "text", placeholder: "e.g. FC Barcelona" },
    ],
  },
  {
    value: "R",
    label: "Referee",
    desc: "Register as a match referee",
    fields: [
      { id: "experience_level", label: "Experience Level", type: "select", options: ["Beginner", "Intermediate", "Experienced", "Professional"], required: true },
      { id: "certification_level", label: "Certification Level", type: "select", options: ["No Certification", "Entry Level", "Regional", "National", "FIFA Listed"], required: true },
      { id: "years_experience", label: "Years of Experience", type: "number", placeholder: "e.g. 3", min: 0, max: 50 },
      { id: "total_matches_officiated", label: "Total Matches Officiated", type: "number", placeholder: "e.g. 120", min: 0, max: 9999 },
      { id: "matches_this_season", label: "Matches This Season", type: "number", placeholder: "e.g. 14", min: 0, max: 999 },
      { id: "primary_position", label: "Primary Position", type: "select", options: ["Referee", "Assistant", "Fourth", "VAR"] },
      { id: "preferred_learning_time", label: "Preferred Learning Time", type: "select", options: ["Morning", "Afternoon", "Evening", "Night"] },
      { id: "certification_goal", label: "Certification Goal", type: "select", options: ["No Certification", "Entry Level", "Regional", "National", "FIFA Listed"] },
    ],
  },
  {
    value: "F",
    label: "Fan",
    desc: "Follow the game you love",
    fields: [],
  },
];

const STEPS = ["Choose role", "Set up profile"];

interface StepDotsProps {
  current: number;
}

const StepDots = ({ current }: StepDotsProps) => (
  <div className="ac-step-dots">
    {STEPS.map((label, i) => (
      <div key={label} className={`ac-step-dot ${i === current ? "ac-step-dot--active" : i < current ? "ac-step-dot--done" : ""}`} title={label} />
    ))}
  </div>
);

interface ChooseRoleStepProps {
  selected: RoleKey | null;
  onSelect: (role: RoleKey) => void;
  onNext: () => void;
  error: string;
}

const ChooseRoleStep = ({ selected, onSelect, onNext, error }: ChooseRoleStepProps) => (
  <div className="ac-form-card">
    <h2 className="ac-form-title">Choose a Role</h2>

    {error && <div className="ac-error-message">{error}</div>}

    <div className="ac-role-list">
      {ROLES.map(({ label, desc }) => (
        <button
          key={label}
          type="button"
          aria-pressed={selected === label}
          className={`ac-role-option ${selected === label ? "ac-role-option--selected" : ""}`}
          onClick={() => onSelect(label)}
        >
          <span className="ac-role-label">{label}</span>{' '}
          <span className="ac-role-desc">{desc}</span>
        </button>
      ))}
    </div>

    <button className="ac-submit-button" type="button" onClick={onNext}>
      Continue
    </button>

    <StepDots current={0} />
  </div>
);

interface CreateProfileStepProps {
  role: RoleConfig;
  values: Record<string, string>;
  onChange: (id: string, value: string) => void;
  onNext: () => void;
  onBack: () => void;
  isLoading: boolean;
  error: string;
}

const CreateProfileStep = ({ role, values, onChange, onNext, onBack, isLoading, error }: CreateProfileStepProps) => (
  <div className="ac-form-card">
    <button type="button" className="ac-back-button" onClick={onBack}>
      Back
    </button>
    <h2 className="ac-form-title">Create Profile</h2>
    <p className="ac-form-subtitle">
      {role.fields.length > 0 ? `${role.label} details` : "No extra details are needed for this role."}
    </p>

    {error && <div className="ac-error-message">{error}</div>}

    {role.fields.length > 0 && (
      <div className="ac-fields-grid">
        {role.fields.map((field) => (
          <div key={field.id} className="ac-field-wrapper">
            <label className="ac-field-label" htmlFor={field.id}>
              {field.label}
              {field.required && <span className="ac-required">*</span>}
            </label>
            {field.type === "select" ? (
              <div className="ac-inputForm">
                <select
                  id={field.id}
                  className="ac-input ac-select"
                  value={values[field.id] ?? ""}
                  onChange={(e) => onChange(field.id, e.target.value)}
                  required={field.required}
                >
                  <option value="" disabled>
                    Select...
                  </option>
                  {field.options?.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <div className="ac-inputForm">
                <input
                  id={field.id}
                  type={field.type}
                  className="ac-input"
                  placeholder={field.placeholder}
                  value={values[field.id] ?? ""}
                  onChange={(e) => onChange(field.id, e.target.value)}
                  min={field.min}
                  max={field.max}
                  required={field.required}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    )}

    <button className="ac-submit-button" type="button" onClick={onNext} disabled={isLoading}>
      {isLoading ? "Saving..." : "Continue"}
    </button>

    <StepDots current={1} />
  </div>
);


const numberOrZero = (value: string | undefined) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

export const AccountCreationForms = () => {
  const [step, setStep] = useState(0);
  const [selectedRole, setSelectedRole] = useState<RoleKey | null>(null);
  const [profileValues, setProfileValues] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { isEmailVerified } = useAuth();

  const roleConfig = ROLES.find((r) => r.label === selectedRole);

  const handleRoleNext = () => {
    if (!selectedRole) {
      setError("Please select a role to continue.");
      return;
    }
    setError("");
    setStep(1);
  };

  const requiredFieldsComplete = (role: RoleConfig) =>
    role.fields
      .filter((field) => field.required)
      .every((field) => (profileValues[field.id] ?? "").trim().length > 0);

  const saveRoleDetails = async (role: RoleConfig) => {
    if (role.value === "P") {
      await apiClient.post("/players/profile/create/", {
        primary_position: profileValues.primary_position,
        secondary_position: profileValues.secondary_position === "None" ? "" : profileValues.secondary_position || "",
        preferred_foot: { Left: "l", Right: "r", Both: "b" }[profileValues.preferred_foot] ?? "r",
        height_cm: numberOrZero(profileValues.height_cm),
        weight_kg: numberOrZero(profileValues.weight_kg),
      });
      return;
    }

    if (role.value === "C") {
      await apiClient.post("/coaching/profile/create/", {
        experience_level: { Beginner: "B", Intermediate: "I", Professional: "P" }[profileValues.experience_level] ?? "B",
        formation_preferences: profileValues.formation_preferences === "N/A" ? "n/a" : profileValues.formation_preferences || "n/a",
        years_experience: numberOrZero(profileValues.years_experience),
        club_name: profileValues.club_name || "",
      });
      return;
    }

    if (role.value === "R") {
      await apiClient.post("/referee/profile/create/", {
        experience_level: { Beginner: "B", Intermediate: "I", Experienced: "E", Professional: "P" }[profileValues.experience_level] ?? "B",
        certification_level: {
          "No Certification": "NON",
          "Entry Level": "EL",
          Regional: "REG",
          National: "NAT",
          "FIFA Listed": "FIFA",
        }[profileValues.certification_level] ?? "NON",
        years_experience: numberOrZero(profileValues.years_experience),
        total_matches_officiates: numberOrZero(profileValues.total_matches_officiated),
        matches_this_season: numberOrZero(profileValues.matches_this_season),
        primary_position: { Referee: "R", Assistant: "A", Fourth: "F", VAR: "V" }[profileValues.primary_position] ?? "R",
        preferred_learning_time: { Morning: "M", Afternoon: "A", Evening: "E", Night: "N" }[profileValues.preferred_learning_time] ?? "",
        certification_goal: {
          "No Certification": "NON",
          "Entry Level": "EL",
          Regional: "REG",
          National: "NAT",
          "FIFA Listed": "FIFA",
        }[profileValues.certification_goal] ?? "",
      });
    }
  };

  const handleProfileNext = async () => {
    if (!roleConfig) return;
    if (!requiredFieldsComplete(roleConfig)) {
      setError("Please complete the required fields before continuing.");
      return;
    }

    setError("");
    setIsLoading(true);
    try {
      await apiClient.post("/users/profile/role/", { role: roleConfig.value });
      await saveRoleDetails(roleConfig);
      navigate(isEmailVerified ? "/home" : "/verify-email", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };


  const handleFieldChange = (id: string, value: string) => {
    setProfileValues((prev) => ({ ...prev, [id]: value }));
  };

  return (
    <div className="ac-container">
      {step === 0 && (
        <ChooseRoleStep
          selected={selectedRole}
          onSelect={(r) => {
            setSelectedRole(r);
            setProfileValues({});
            setError("");
          }}
          onNext={handleRoleNext}
          error={error}
        />
      )}

      {step === 1 && roleConfig && (
        <CreateProfileStep
          role={roleConfig}
          values={profileValues}
          onChange={handleFieldChange}
          onNext={handleProfileNext}
          onBack={() => {
            setStep(0);
            setError("");
          }}
          isLoading={isLoading}
          error={error}
        />
      )}

    </div>
  );
};

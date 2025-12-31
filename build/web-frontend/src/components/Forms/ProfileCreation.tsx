import "./css/ProfileCreation.css";
import { useState } from "react";
import type { FormEvent } from "react";
import {
  Api_Endpoints,
  authenticatedFetch,
} from "../../services/api/AuthenticateUserApi";

interface ProfileData {
  display_name: string;
  gender: string;
  date_of_birth: string;
  bio: string;
}

export const ProfileCreation = () => {
  const [formData, setFormData] = useState<ProfileData>({
    display_name: "",
    gender: "NS",
    date_of_birth: "",
    bio: "",
  });

  const [error, setError] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { id, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [id]: value,
    }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const response = await authenticatedFetch(Api_Endpoints.PROFILE_CREATE, {
        method: "POST",
        body: JSON.stringify({
          display_name: formData.display_name,
          gender: formData.gender,
          date_of_birth: formData.date_of_birth || null,
          bio: formData.bio || "",
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Profile created failed");
      }

      const data = await response.json();

      console.log("Profile creation successful: ", data);
      globalThis.location.href = "http://localhost:5173/create/profile/role";
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "An error occured during profile creation"
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="profile-creation-container">
      <h2> Create Your Profile </h2>

      <div className="profile-creation-form-group">
        <label htmlFor="display_name">Display Name</label>
        <input
          type="text"
          id="display_name"
          value={formData.display_name}
          onChange={handleInputChange}
          placeholder="Enter your desired display name"
        />
      </div>
      <div className="mid-section">
        <div className="profile-creation-form-group">
          <label htmlFor="gender">Gender</label>
          <select
            id="gender"
            value={formData.gender}
            onChange={handleInputChange}
          >
            <option value="F">Female</option>
            <option value="M">Male</option>
            <option value="O">Other</option>
            <option value="NS">Not Specified</option>
          </select>
        </div>

        <div className="profile-creation-form-group">
          <label htmlFor="date_of_birth">Date of Birth</label>
          <input
            type="date"
            id="date_of_birth"
            value={formData.date_of_birth}
            onChange={handleInputChange}
            className="profile-dob"
          />
        </div>
      </div>

      <div className="profile-creation-form-group">
        <label htmlFor="bio">Bio</label>
        <textarea
          className="bio-input"
          id="bio"
          value={formData.bio}
          placeholder="Tell us a little about yourself..."
          onChange={handleInputChange}
        ></textarea>
      </div>

      <button type="submit" className="button-submit" disabled={isLoading}>
        {isLoading ? "Creating Profile..." : "Create Profile"}
      </button>
    </form>
  );
};

import "./css/RoleAssignForm.css";
import { useState } from "react";
import type { FormEvent } from "react";
import {
  Api_Endpoints,
  authenticatedFetch,
} from "../../services/api/AuthenticateUserApi";

interface RoleData {
  role: string;
}

export const RoleAssignForm = () => {
  const [formData, setFormData] = useState<RoleData>({
    role: "P",
  });
  const [error, setError] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
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
      const response = await authenticatedFetch(Api_Endpoints.ASSIGN_ROLE, {
        method: "POST",
        body: JSON.stringify({
          role: formData.role,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Couldn't assign role to user");
      }

      const data = await response.json();

      console.log("Successfully assigned role to user: ", data);
      globalThis.location.href = "http://localhost:5173/create/profile/role/details";
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "An error occured while assigning your role"
      );
    } finally {
      setIsLoading(false);
    }
  };
  return (
    <form className="role-assign-form-container"  onSubmit={handleSubmit}>
      <h2> Choose a Role </h2>

      <div className="role-assign-form-group">
        <label htmlFor="role">Role</label>
        <select id="role" value={formData.role} onChange={handleInputChange}>
          <option value="C">Coach</option>
          <option value="P">Player</option>
          <option value="R">Referee</option>
          <option value="F">Not Specified</option>
        </select>
      </div>

      <button type="submit" className="button-submit" disabled={isLoading}>
        {isLoading ? "Creating Profile..." : "Create Profile"}
      </button>
    </form>
  );
};

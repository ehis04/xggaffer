import type { Teamsheet } from '../../types/teamsheet';

const API_BASE_URL = 'http://localhost:8000/api/teamsheets';

export const teamsheetApi = {
    getAllTeamsheets: async (): Promise<Teamsheet[]> => {
        const response = await fetch(`${API_BASE_URL}/teamsheets/`);
        const data = await response.json();
        // DRF may return a paginated response { results: [...] }
        if (Array.isArray(data)) return data as Teamsheet[];
        if (data && Array.isArray((data as any).results)) return (data as any).results as Teamsheet[];
        // Fallback: return empty array
        return [];
    },


    getTeamsheet: async (id: number): Promise<Teamsheet> => {
        const response = await fetch(`${API_BASE_URL}/teamsheets/${id}/`)
        return response.json();
    },

    createTeamsheet: async (data: Omit<Teamsheet, 'id' | 'created_at' | 'updated_at'>): Promise<Teamsheet> => {
        const response = await fetch(`${API_BASE_URL}/teamsheets/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    updateTeamsheet: async (id: number, data: Partial<Teamsheet>): Promise<Teamsheet> => {
        const response = await fetch(`${API_BASE_URL}/teamsheets/${id}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    deleteTeamsheet: async (id: number): Promise<void> => {
        await fetch(`${API_BASE_URL}/teamsheets/${id}/`, {
            method: 'DELETE'
        });
    }
};

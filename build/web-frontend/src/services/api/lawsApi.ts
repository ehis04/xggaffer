import axios from 'axios';
import type { LawEdition, Law, LawListItem, LawChange } from '../../types/laws';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const lawsApi = {
  // Editions
  async getEditions(): Promise<LawEdition[]> {
    const response = await axios.get(`${API_BASE}/laws/editions/`);
    return response.data.results || response.data;
  },

  async getCurrentEdition(): Promise<LawEdition> {
    const response = await axios.get(`${API_BASE}/laws/editions/current/`);
    return response.data;
  },

  // Laws
  async getLaws(editionId?: number): Promise<LawListItem[]> {
    const params = editionId ? { edition: editionId } : {};
    const response = await axios.get(`${API_BASE}/laws/laws/`, { params });
    return response.data.results || response.data;
  },

  async getLawById(id: number): Promise<Law> {
    const response = await axios.get(`${API_BASE}/laws/laws/${id}/`);
    return response.data;
  },

  async getLawByNumber(lawNumber: number, editionId?: number): Promise<Law> {
    const params: any = { number: lawNumber };
    if (editionId) params.edition = editionId;
    const response = await axios.get(`${API_BASE}/laws/laws/by_number/`, { params });
    return response.data;
  },

  // Changes
  async getChanges(editionId?: number, lawNumber?: number): Promise<LawChange[]> {
    const params: any = {};
    if (editionId) params.edition = editionId;
    if (lawNumber) params.law_number = lawNumber;
    const response = await axios.get(`${API_BASE}/laws/changes/`, { params });
    return response.data.results || response.data;
  },
};
import apiClient from './client';
import type { LawEdition, Law, LawListItem, LawChange } from '../../types/laws';

export const lawsApi = {
  getEditions: () =>
    apiClient.get<LawEdition[]>('/laws/editions/'),

  getCurrentEdition: () =>
    apiClient.get<LawEdition>('/laws/editions/current/'),

  getLaws: (editionId?: number) => {
    const params = editionId ? { edition: String(editionId) } : undefined;
    return apiClient.get<LawListItem[]>('/laws/laws/', params);
  },

  getLawById: (id: number) =>
    apiClient.get<Law>(`/laws/laws/${id}/`),

  getLawByNumber: (lawNumber: number, editionId?: number) => {
    const params: Record<string, string> = { number: String(lawNumber) };
    if (editionId) params.edition = String(editionId);
    return apiClient.get<Law>('/laws/laws/by_number/', params);
  },

  getChanges: (editionId?: number, lawNumber?: number) => {
    const params: Record<string, string> = {};
    if (editionId) params.edition = String(editionId);
    if (lawNumber) params.law_number = String(lawNumber);
    return apiClient.get<LawChange[]>('/laws/changes/', params);
  },
};

export default lawsApi;
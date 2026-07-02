import axios from 'axios';
import { ChatRequest, ChatResponse, SessionSummary } from '@/types';

// Uses Next.js rewrite proxy → eliminates CORS entirely
const api = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      'Request failed';

    console.error('[API Error]', msg, err.config?.url);
    return Promise.reject(new Error(msg));
  }
);

export const chatApi = {
  sendMessage: (data: ChatRequest): Promise<ChatResponse> =>
    api.post<ChatResponse>('/api/chat', data).then((r) => r.data),

  getHistory: (sessionId: string, limit = 50) =>
    api
      .get(`/api/chat/${sessionId}/history`, { params: { limit } })
      .then((r) => r.data),

  getContext: (sessionId: string) =>
    api.get(`/api/chat/${sessionId}/context`).then((r) => r.data),

  clearContext: (sessionId: string) =>
    api.delete(`/api/chat/${sessionId}/context`).then((r) => r.data),
};

export const sessionsApi = {
  list: (limit = 20): Promise<SessionSummary[]> =>
    api
      .get<SessionSummary[]>('/api/sessions', { params: { limit } })
      .then((r) => r.data),

  // Preserved from old version
  get: (sessionId: string) =>
    api.get(`/api/sessions/${sessionId}`).then((r) => r.data),

  delete: (sessionId: string) =>
    api.delete(`/api/sessions/${sessionId}`).then((r) => r.data),
};

// Added from new version
export const companyApi = {
  list: () =>
    api.get('/api/company').then((r) => r.data),

  create: (data: object) =>
    api.post('/api/company', data).then((r) => r.data),

  updateServices: (companyId: string, services: string[]) =>
    api
      .put(`/api/company/${companyId}/services`, services)
      .then((r) => r.data),
};

// Preserved from old version
export const travelApi = {
  getSearches: (sessionId: string, limit = 10) =>
    api
      .get(`/api/travel/${sessionId}/searches`, {
        params: { limit },
      })
      .then((r) => r.data),

  applyFilters: (data: {
    session_id: string;
    filters: Record<string, unknown>;
    search_type: string;
  }) =>
    api.post('/api/travel/filter', data).then((r) => r.data),
};

export default api;
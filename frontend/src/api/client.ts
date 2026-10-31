import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import type {
  User,
  Token,
  AuthURLResponse,
  CallbackRequest,
  ReviewDetailResponse,
  ReviewCreate,
  ReviewUpdate,
  ReviewSearchParams,
  PaginatedReviews,
  ReviewExportRequest,
  ReviewExportResponse,
  ReviewImportRequest,
  ReviewImportResponse,
  Finding,
  FindingCreate,
  FindingUpdate,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

class ApiClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        if (this.accessToken && config.headers) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        if (error.response?.status === 401 && !originalRequest._retry && this.refreshToken) {
          originalRequest._retry = true;
          try {
            await this.refreshAccessToken();
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${this.accessToken}`;
            }
            return this.client(originalRequest);
          } catch {
            this.clearTokens();
            window.location.href = '/login';
            return Promise.reject(error);
          }
        }

        if (error.response?.status === 401) {
          this.clearTokens();
          window.location.href = '/login';
        }

        return Promise.reject(error);
      }
    );
  }

  setTokens(accessToken: string, refreshToken: string) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
  }

  async refreshAccessToken(): Promise<void> {
    const response = await this.client.post<Token>('/auth/refresh', {}, {
      headers: { 'X-CSRF-Token': this.getCsrfToken() },
    });
    this.setTokens(response.data.access_token, response.data.refresh_token);
  }

  private getCsrfToken(): string {
    const cookies = document.cookie.split('; ');
    const csrfCookie = cookies.find(c => c.startsWith('csrf_token='));
    return csrfCookie ? csrfCookie.split('=')[1] : '';
  }

  // Auth
  async getAuthUrl(): Promise<AuthURLResponse> {
    const response = await this.client.get<AuthURLResponse>('/auth/login');
    return response.data;
  }

  async callback(data: CallbackRequest): Promise<Token> {
    const response = await this.client.post<Token>('/auth/callback', data);
    this.setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout');
    this.clearTokens();
  }

  async getMe(): Promise<User> {
    const response = await this.client.get<User>('/auth/me');
    return response.data;
  }

  // Reviews
  async listReviews(params: ReviewSearchParams): Promise<PaginatedReviews> {
    const response = await this.client.get<PaginatedReviews>('/reviews', { params });
    return response.data;
  }

  async getReview(id: number): Promise<ReviewDetailResponse> {
    const response = await this.client.get<ReviewDetailResponse>(`/reviews/${id}`);
    return response.data;
  }

  async createReview(data: ReviewCreate): Promise<ReviewDetailResponse> {
    const response = await this.client.post<ReviewDetailResponse>('/reviews', data, {
      headers: { 'X-CSRF-Token': this.getCsrfToken() },
    });
    return response.data;
  }

  async updateReview(id: number, data: ReviewUpdate): Promise<ReviewDetailResponse> {
    const response = await this.client.patch<ReviewDetailResponse>(`/reviews/${id}`, data, {
      headers: { 'X-CSRF-Token': this.getCsrfToken() },
    });
    return response.data;
  }

  async deleteReview(id: number): Promise<void> {
    await this.client.delete(`/reviews/${id}`, {
      headers: { 'X-CSRF-Token': this.getCsrfToken() },
    });
  }

  async exportReview(data: ReviewExportRequest): Promise<ReviewExportResponse> {
    const response = await this.client.post<ReviewExportResponse>(`/reviews/${data.review_id}/export`, data, {
      headers: { 'X-CSRF-Token': this.getCsrfToken() },
    });
    return response.data;
  }

  // Import
  async importReview(data: ReviewImportRequest): Promise<ReviewImportResponse> {
    const response = await this.client.post<ReviewImportResponse>('/reviews/import', data, {
      headers: { 'X-CSRF-Token': this.getCsrfToken() },
    });
    return response.data;
  }


  // Findings
  async createFinding(reviewId: number, data: FindingCreate): Promise<Finding> {
    const response = await this.client.post<Finding>(`/reviews/${reviewId}/findings`, data, {
      headers: { 'X-CSRF-Token': this.getCsrfToken() },
    });
    return response.data;
  }

  async updateFinding(reviewId: number, findingId: number, data: FindingUpdate): Promise<Finding> {
    const response = await this.client.patch<Finding>(`/reviews/${reviewId}/findings/${findingId}`, data, {
      headers: { 'X-CSRF-Token': this.getCsrfToken() },
    });
    return response.data;
  }

  // Users
  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/users/me');
    return response.data;
  }
}

export const api = new ApiClient();
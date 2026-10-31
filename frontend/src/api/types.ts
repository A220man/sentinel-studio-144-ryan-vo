export interface User {
  id: number;
  keycloak_sub: string;
  email: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  role: 'viewer' | 'operator' | 'admin';
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthURLResponse {
  auth_url: string;
  state: string;
  code_verifier: string;
}

export interface CallbackRequest {
  code: string;
  state: string;
  code_verifier: string;
}

export type ReviewStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

export type FindingSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type FindingCategory = 'bug' | 'security' | 'performance' | 'style' | 'documentation' | 'testing' | 'maintainability';

export interface Finding {
  id: number;
  review_id: number;
  file_path: string;
  start_line: number;
  end_line: number;
  severity: FindingSeverity;
  category: FindingCategory;
  title: string;
  description: string;
  suggestion: string | null;
  rule_id: string | null;
  is_llm_generated: boolean;
  llm_explanation: string | null;
  created_at: string;
}

export interface ReviewBase {
  title: string;
  description?: string;
  repository_url?: string;
  base_branch: string;
  head_branch: string;
  diff_content?: string;
}

export interface ReviewCreate extends ReviewBase {}

export interface ReviewUpdate {
  title?: string;
  description?: string;
  repository_url?: string;
  base_branch?: string;
  head_branch?: string;
  diff_content?: string;
  status?: ReviewStatus;
}

export interface ReviewListResponse {
  id: number;
  author_id: number;
  title: string;
  description: string | null;
  repository_url: string | null;
  base_branch: string;
  head_branch: string;
  status: ReviewStatus;
  findings_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewDetailResponse extends ReviewListResponse {
  findings: Finding[];
}

export interface ReviewSearchParams {
  status?: ReviewStatus;
  author_id?: number;
  repository_url?: string;
  date_from?: string;
  date_to?: string;
  page: number;
  page_size: number;
}

export interface PaginatedReviews {
  items: ReviewListResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ReviewExportRequest {
  review_id: number;
  format: 'json' | 'sarif' | 'markdown';
}

export interface ReviewExportResponse {
  content: string;
  filename: string;
  media_type: string;
}

export interface FindingCreate {
  file_path: string;
  start_line: number;
  end_line: number;
  severity: FindingSeverity;
  category: FindingCategory;
  title: string;
  description: string;
  suggestion?: string;
  rule_id?: string;
  is_llm_generated?: boolean;
  llm_explanation?: string;
}

export interface FindingUpdate {
  severity?: FindingSeverity;
  category?: FindingCategory;
  title?: string;
  description?: string;
  suggestion?: string;
  rule_id?: string;
  is_llm_generated?: boolean;
  llm_explanation?: string;
}

export interface ReviewImportRequest {
  content: string;
  format: 'json';
}

export interface ReviewImportResponse extends ReviewDetailResponse {}
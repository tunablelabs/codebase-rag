import {
  CreateSessionResponse,
  UploadResponse,
  RepositoryUploadRequest,
  QueryRequest,
  QueryResponse,
} from '@/types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      error.message || `HTTP error! status: ${response.status}`
    );
  }
  return response.json();
}

export const api = {
  async createSession(): Promise<CreateSessionResponse> {
    const response = await fetch(`${BASE_URL}/codex/create/chat`, {
      method: 'GET',
    });
    return handleResponse<CreateSessionResponse>(response);
  },

  async uploadRepository(request: RepositoryUploadRequest): Promise<UploadResponse> {
    const response = await fetch(`${BASE_URL}/codex/uploadproject`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_id: request.file_id,
        local_dir: request.local_dir,
        repo: request.repo,
        files: request.files
      }),
    });
    return handleResponse<UploadResponse>(response);
  },

  async storeRepository(fileId: string): Promise<UploadResponse> {
    const response = await fetch(`${BASE_URL}/code/storage`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_id: fileId
      }),
    });
    return handleResponse<UploadResponse>(response);
  },

  async queryRepository(request: QueryRequest): Promise<QueryResponse> {
    const response = await fetch(`${BASE_URL}/codex/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_id: request.file_id,
        use_llm: String(request.use_llm),
        ast_flag: String(request.ast_flag),
        query: request.query,
        limit: request.limit
      }),
    });
    return handleResponse<QueryResponse>(response);
  },
};

export default api;
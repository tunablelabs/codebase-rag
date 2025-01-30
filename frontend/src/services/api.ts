import {
  CreateSessionResponse,
  UploadResponse,
  RepositoryUploadRequest,
  QueryRequest,
  QueryResponse,
  UploadStats
} from '@/types';

//const BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';
const BASE_URL = 'http://localhost:8000'
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
    console.log('create/chat')
    const response = await fetch(`${BASE_URL}/codex/create/chat`, {
      method: 'GET',
    });
    console.log(response)
    return handleResponse<CreateSessionResponse>(response);
  },

  async uploadRepository(request: RepositoryUploadRequest): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file_id", request.file_id);
    formData.append("local_dir", request.local_dir);
    if(request.repo){
      formData.append("repo", request.repo);
    }
    if(request.files){
      Array.from(request.files).forEach((file) => {
        formData.append("files", file);
      });
    }
    

    const response = await fetch(`${BASE_URL}/codex/uploadproject`, {
      method: 'POST',
      body: formData,
    });
    //console.log('response from upload repository',response.json())
    return handleResponse<UploadResponse>(response);
  },

  async storeRepository(fileId: string): Promise<UploadResponse> {
    console.log(fileId)
    const response = await fetch(`${BASE_URL}/codex/storage`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_id: fileId
      }),
    });
    //console.log('response from storeage',response)
    return handleResponse<UploadResponse>(response);
  },

  async getStats(fileId: string): Promise<UploadStats> {
    console.log(fileId)
    const response = await fetch(`${BASE_URL}/codex/stats`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_id: fileId
      }),
    });
    return handleResponse<UploadStats>(response);
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
import {
  CreateSessionResponse,
  UploadResponse,
  RepositoryUploadRequest,
  QueryRequest,
  QueryResponse,
  UploadStats,
  ListChatSession,
  StoreResponse,
  Message,
  NListChatSession
} from '@/types';

const BASE_URL = ' https://codebase-rag-production.up.railway.app/api'

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
  async createSession(email: string): Promise<CreateSessionResponse> {
    console.log('create/chat',email)
    const response = await fetch(`${BASE_URL}/codex/create/user`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: email
      }),
    });
    console.log('response',response)
    return handleResponse<CreateSessionResponse>(response);
  },

 // Add logging to the listAllSessions method
  async listAllSessions(fileId: string): Promise<NListChatSession[]> {
    console.log("[API] Fetching sessions...");
    const response = await fetch(`${BASE_URL}/codex/session/list?user_id=${encodeURIComponent(fileId)}`, {
      method: 'GET',
      headers: {
        'Cache-Control': 'no-cache'
      },
    });
    const data = await handleResponse<NListChatSession[]>(response);
    console.log("[API] Received sessions:", data);
    const sessionsWithMessages = await Promise.all(
      data.map(async (session): Promise<NListChatSession> => {
        const messagesResponse = await fetch(`${BASE_URL}/codex/session/data?user_id=${encodeURIComponent(fileId)}&session_id=${encodeURIComponent(session.session_id)}`, {
          method: 'GET',
          headers: {
            'Cache-Control': 'no-cache'
          }
        });
  
        const messages = await handleResponse<Message[]>(messagesResponse);
        console.log(messages);
        return {
          ...session,
          messages // Attach messages to the session
        };
      })
    );
    console.log("[API] Sessions with messages:", sessionsWithMessages);
    return sessionsWithMessages;
  
    //return data;
  },

  async uploadRepository(request: RepositoryUploadRequest): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("user_id", request.user_id);
    formData.append("local_dir", request.local_dir);
    if(request.repo){
      formData.append("repo", request.repo);
    }
    if(request.files){
      Array.from(request.files).forEach((file) => {
        formData.append("files", file);
      });
    }
    

    const response = await fetch(`${BASE_URL}/codex/create/session/uploadproject`, {
      method: 'POST',
      body: formData,
    });
    //console.log('response from upload repository',response.json())
    return handleResponse<UploadResponse>(response);
  },

  async storeRepository(sessionId: string, userId:string ): Promise<StoreResponse> {
    const response = await fetch(`${BASE_URL}/codex/storage`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        user_id: userId
      }),
    });
    console.log('response from storeage',response)
    return handleResponse<StoreResponse>(response);
  },

  async getStats(sessionId: string, userId: string): Promise<UploadStats> {
    console.log(sessionId, userId)
    const response = await fetch(`${BASE_URL}/codex/stats`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        session_id: sessionId
      }),
    });
    console.log('response',response);
    return handleResponse<UploadStats>(response);
  },

  async queryRepository(request: QueryRequest): Promise<QueryResponse> {
    const response = await fetch(`${BASE_URL}/codex/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: String(request.user_id),
        session_id: String(request.session_id),
        use_llm: String(request.use_llm),
        ast_flag: String(request.ast_flag),
	      sys_prompt: String(request.sys_prompt),
        query: request.query,
        limit: request.limit
      }),
    });
    return handleResponse<QueryResponse>(response);
  },

  renameSession: async ({ session_id, new_name, email }: { session_id: string; new_name: string; email: string }) => {
    try {
      const response = await fetch(`${BASE_URL}/codex/session/rename`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: session_id,
          updated_name: new_name,
          user_id: email
        }),
      });
  
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to rename session');
      }
  
      return await response.json();
    } catch (error) {
      console.error('Error in renameSession:', error);
      throw error;
    }
  },
  
  // For deleting sessions
  deleteSession: async ({ session_id, email }: { session_id: string; email: string }) => {
    try {
      const response = await fetch(`${BASE_URL}/codex/session/delete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: session_id,
          user_id: email
        }),
      });
  
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to delete session');
      }
  
      return await response.json();
    } catch (error) {
      console.error('Error in deleteSession:', error);
      throw error;
    }
  }
  
};

export default api;


export interface BaseApiResponse {
  success: boolean;
}

// session and chat related types
export interface Message {
  user?: string;
  bot?: string;
  type: 'user' | 'bot';
  text: string;
  timestamp: string;
}

export interface Session {
  id: string;
  name: string;
  messages: Message[];
  createdAt: string;
  lastActive: string;
  githubUrl?: string;
}

// chat configuration options
export interface ChatOptions {
  githubUrl: string;
  systemPrompt: string;
  astFlag: boolean;
  forceReindex: boolean;
  sessionId?: string;
  llmEvaluator?: boolean;
}

// API Response types
export interface CreateSessionResponse extends BaseApiResponse {
  file_id: string;
}

// New type created for Listing Chat Sessions
export interface ListChatSession extends BaseApiResponse {
  file_id: string;
  last_message_preview: string;
  repo_name: string;
  messages: Message[];
}

export interface UploadResponse extends BaseApiResponse {
  message?: string;
}

export interface UploadStats extends BaseApiResponse {
  stats: {
    total_code_files: number;
    language_distribution: {
    [language: string]: string; // For example: {"Python": "100%"}
  };
  }
}

// repository and file handling types
export interface RepositoryUploadRequest {
  file_id: string;
  local_dir: string;
  repo?: string;
  files?: File[];
}

export interface UploadedFile {
  name: string;
  size: number;
  type: string;
  uploadedAt: string;
  id?: string;
}

export interface FileUploadOptions {
  maxSize?: number;
  allowedTypes?: string[];
  multiple?: boolean;
}

// query related types
export interface QueryRequest {
  file_id: string;
  use_llm: string;
  ast_flag: string;
  query: string;
  sys_prompt: string;
  limit: number;
}

export interface MetricScore {
  score: number;
  reason: string;
}

export interface QueryMetrics {
  "Answer Relevancy": MetricScore;
  "Faithfulness": MetricScore;
  "Contextual Relevancy": MetricScore;
  "context_query_match": MetricScore;
  "information_density": MetricScore;
  "answer_coverage": MetricScore;
  "response_consistency": MetricScore;
  "source_diversity": MetricScore;
}

export interface QueryResponse {
  query: string;
  response: string;
  metric: QueryMetrics;
}
import { useState, useCallback } from 'react';
import api from '@/services/api';

interface GithubUploadHookReturn {
  isUploading: boolean;
  stats: Stats | null;
  uploadUrl: (githubUrl: string, email: string) => Promise<Stats | undefined>;
  sessionId: string | null;
}

interface Stats {
  stats: {
    total_code_files: number;
    language_distribution: {
      [language: string]: string; // Example: {"Python": "100%"}
    };
  };
}

export function useGithubUrl(): GithubUploadHookReturn {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const isValidGithubUrl = (url: string) => {
    const regex =
      /^(https?:\/\/)?([a-zA-Z0-9-_]+)?(?::([a-zA-Z0-9-_]+))?@?github\.com\/([\w\-]+)\/([\w\-]+)/;
    return regex.test(url);
  };

  const uploadUrl = useCallback(async (githubUrl: string, email: string): Promise<Stats | undefined> => {
    console.log('Received GitHub URL:', githubUrl);
    setIsUploading(true);
    setUploadError(null);

    try {
      if (!isValidGithubUrl(githubUrl)) {
        alert("Please provide a valid GitHub repository URL.");
        return;
      }

      const sessionResponse = await api.createSession(email);
      console.log('Session Created:', sessionResponse);
      
      const uploadResponse = await api.uploadRepository({
        user_id: email,
        local_dir: 'False',
        repo: githubUrl, 
      });
      setSessionId(String(uploadResponse.session_id)); 
      console.log('storage processing')

      await api.storeRepository(uploadResponse.session_id, email);
      const stats = await api.getStats(uploadResponse.session_id, email);
      console.log('stats',stats)
      //setStats(stats); 
      return stats;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      //setUploadError(errorMessage);
      throw err;
    } finally {
      setIsUploading(false);
    }
  }, []);

  return {
    stats,
    isUploading,
    uploadUrl,
    sessionId
  };
}

import { useState, useEffect, useCallback } from 'react';
import api from '@/services/api';

interface UseStatsReturn {
  stats: any | null;
  isLoading: boolean;
  error: string | null;
  fetchStats: (fileId: string) => Promise<void>;
}

export function useStats(): UseStatsReturn {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.getStats(id);
      console.log(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch stats');
    } finally {
      setIsLoading(false);
    }
  }, []);
  return { isLoading, error, fetchStats };
}

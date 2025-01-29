import { useState, useCallback } from 'react';
import { FileUploadOptions, UploadedFile } from '@/types';
import api from '@/services/api';

interface FileUploadHookReturn {
  files: UploadedFile[];
  isUploading: boolean;
  uploadError: string | null;
  uploadFiles: (fileList: FileList) => Promise<UploadedFile[] | undefined>;
  clearFiles: () => void;
  sessionIdf: string | null;
}

interface Stats {
  stats: {
  total_code_files: number;
  language_distribution: {
    [language: string]: string; // For example: {"Python": "100%"}
  };
}
}

export function useFileUpload(options: FileUploadOptions = {}): FileUploadHookReturn {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [sessionIdf, setsessionIdf] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);

  const validateFile = useCallback((file: File): boolean => {
    if (options.maxSize && file.size > options.maxSize) {
      setUploadError(`File size exceeds ${options.maxSize / 1024 / 1024}MB limit`);
      return false;
    }

    if (options.allowedTypes && !options.allowedTypes.includes(file.type)) {
      setUploadError(`File type ${file.type} not supported`);
      return false;
    }

    return true;
  }, [options.maxSize, options.allowedTypes]);

  const uploadFiles = useCallback(async (fileList: FileList): Promise<Stats | undefined> => {
    console.log('recieve')
    setIsUploading(true);
    setUploadError(null);

    try {
      const sessionResponse = await api.createSession();
      console.log(sessionResponse)
      setsessionIdf(sessionResponse.file_id); 
      const fileArray = Array.from(fileList);
      
      if (!fileArray.every(validateFile)) {
        return;
      }
      console.log(fileArray)
      await api.uploadRepository({
        file_id: sessionResponse.file_id,
        local_dir: 'True',
        files: fileArray
      });
      console.log('storing_repo',sessionResponse.file_id)
      await api.storeRepository(sessionResponse.file_id);

      const stats = await api.getStats(sessionResponse.file_id);
      console.log('stats',stats)
      setStats(stats); 

      /*const uploadedFiles: UploadedFile[] = fileArray.map(file => ({
        name: file.name,
        size: file.size,
        type: file.type,
        uploadedAt: new Date().toISOString(),
        id: sessionResponse.file_id
      })); */

      //setFiles(prev => [...prev, ...uploadedFiles]);*/
      return stats;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      setUploadError(errorMessage);
      setIsUploading(false);
      throw err;
    } finally {
      setIsUploading(false);
    }
  }, [validateFile]);

  const clearFiles = useCallback(() => {
    setFiles([]);
    setUploadError(null);
  }, []);

  return {
    files,
    isUploading,
    uploadError,
    uploadFiles,
    clearFiles,
    sessionIdf
  };
}

import { useState, useCallback } from 'react';
import { FileUploadOptions, UploadedFile } from '@/types';
import api from '@/services/api';

interface FileUploadHookReturn {
  files: UploadedFile[];
  isUploading: boolean;
  uploadError: string | null;
  uploadFiles: (fileList: FileList, email: string) => Promise<Stats | undefined>;
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

  const uploadFiles = useCallback(async (fileList: FileList, email: string): Promise<Stats | undefined> => {
    console.log('recieve')
    setIsUploading(true);
    setUploadError(null);

    try {
      const sessionResponse = await api.createSession(email);
      const fileArray = Array.from(fileList);
      
      if (!fileArray.every(validateFile)) {
        return;
      }
      console.log(fileArray)
      const uploadResponse = await api.uploadRepository({
        user_id: email,
        local_dir: 'True',
        files: fileArray
      });
      setsessionIdf(String(uploadResponse.session_id)); 
      console.log('storing_repo',uploadResponse.session_id)
      await api.storeRepository(uploadResponse.session_id, email);

      const stats = await api.getStats(uploadResponse.session_id, email);
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

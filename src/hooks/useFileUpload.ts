import { useState, useCallback } from 'react';
import { FileUploadOptions, UploadedFile } from '@/types';
import api from '@/services/api';

interface FileUploadHookReturn {
  files: UploadedFile[];
  isUploading: boolean;
  uploadError: string | null;
  uploadFiles: (fileList: FileList) => Promise<UploadedFile[] | undefined>;
  clearFiles: () => void;
}

export function useFileUpload(options: FileUploadOptions = {}): FileUploadHookReturn {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

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

  const uploadFiles = useCallback(async (fileList: FileList): Promise<UploadedFile[] | undefined> => {
    setIsUploading(true);
    setUploadError(null);

    try {
      const sessionResponse = await api.createSession();
      const fileArray = Array.from(fileList);
      
      if (!fileArray.every(validateFile)) {
        return;
      }

      await api.uploadRepository({
        file_id: sessionResponse.file_id,
        local_dir: 'false',
        files: fileArray
      });

      await api.storeRepository(sessionResponse.file_id);

      const uploadedFiles: UploadedFile[] = fileArray.map(file => ({
        name: file.name,
        size: file.size,
        type: file.type,
        uploadedAt: new Date().toISOString(),
        id: sessionResponse.file_id
      }));

      setFiles(prev => [...prev, ...uploadedFiles]);
      return uploadedFiles;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      setUploadError(errorMessage);
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
    clearFiles
  };
}
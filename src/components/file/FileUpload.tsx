import React, { useRef, useState, DragEvent } from 'react';
import { Upload, FolderUp, Check, AlertCircle } from 'lucide-react';

interface FileUploadProps {
  onFileSelect: (files: FileList) => void;
  accept?: string;
  multiple?: boolean;
  className?: string;
}

export default function FileUpload({ 
  onFileSelect, 
  accept = '', 
  multiple = false,
  className = ''
}: FileUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [isHovered, setIsHovered] = useState(false);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFiles(files);
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      handleFiles(files);
    }
  };

  const handleFiles = (files: FileList) => {
    try {
      onFileSelect(files);
      setUploadStatus('success');
      setTimeout(() => setUploadStatus('idle'), 3000);
      

      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      setUploadStatus('error');
      setTimeout(() => setUploadStatus('idle'), 3000);
    }
  };

  return (
    <div className={`${className} relative`}>
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept={accept}
        multiple={multiple}
        webkitdirectory={multiple ? "true" : undefined}
        className="hidden"
        id="file-upload"
      />
      
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative group
          border-2 border-dashed rounded-xl
          transition-all duration-300 ease-in-out
          ${isDragging ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 
            'border-slate-300 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500'}
          ${uploadStatus === 'success' ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : ''}
          ${uploadStatus === 'error' ? 'border-red-500 bg-red-50 dark:bg-red-900/20' : ''}
        `}
      >
        <label
          htmlFor="file-upload"
          className="flex flex-col items-center justify-center px-6 py-8 cursor-pointer"
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
    
          <div className={`
            w-12 h-12 mb-4 rounded-full
            flex items-center justify-center
            transition-all duration-300
            ${uploadStatus === 'success' ? 'bg-green-100 dark:bg-green-900/30' :
              uploadStatus === 'error' ? 'bg-red-100 dark:bg-red-900/30' :
              'bg-slate-100 dark:bg-slate-800'}
          `}>
            {uploadStatus === 'success' ? (
              <Check className="w-6 h-6 text-green-600 dark:text-green-400" />
            ) : uploadStatus === 'error' ? (
              <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
            ) : multiple ? (
              <FolderUp className={`w-6 h-6 ${isDragging || isHovered ? 'text-blue-600 dark:text-blue-400' : 'text-slate-600 dark:text-slate-400'}`} />
            ) : (
              <Upload className={`w-6 h-6 ${isDragging || isHovered ? 'text-blue-600 dark:text-blue-400' : 'text-slate-600 dark:text-slate-400'}`} />
            )}
          </div>

    
          <div className="space-y-1 text-center">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
              {multiple ? 'Upload Repository' : 'Upload File'}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {isDragging ? 'Drop your files here' : 
                `Drag and drop your ${multiple ? 'folder' : 'file'} here, or click to browse`}
            </p>
          </div>

  
          <div className={`
            mt-2 text-sm font-medium
            transition-all duration-300
            ${uploadStatus === 'success' ? 'text-green-600 dark:text-green-400' :
              uploadStatus === 'error' ? 'text-red-600 dark:text-red-400' : 'text-transparent'}
          `}>
            {uploadStatus === 'success' ? 'Upload successful!' :
             uploadStatus === 'error' ? 'Upload failed. Please try again.' : ''}
          </div>
        </label>


        <div className={`
          absolute inset-0 rounded-xl
          bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500
          opacity-0 transition-opacity duration-300
          ${isDragging || isHovered ? 'opacity-10' : ''}
        `} />
      </div>
    </div>
  );
}
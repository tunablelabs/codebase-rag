import React from "react";

interface FileListProps {
  isFilesVisible: boolean;
  files: string[]; // Assuming files is an array of strings. Adjust type if needed.
}

const FileList: React.FC<FileListProps> = ({ isFilesVisible, files }) => {
  if (!isFilesVisible) return null; // Prevent rendering if not visible

  return (
    <div className="space-y-2 bg-white/70 p-4 rounded-lg shadow-lg backdrop-blur-sm dark:bg-slate-900/70">
      <h3 className="font-semibold text-slate-800 dark:text-slate-200">
        Few Files from your repository
      </h3>
      <ul className="list-disc pl-5 text-slate-700 dark:text-slate-300">
        {files.map((file, index) => (
          <li key={index}>{file}</li>
        ))}
      </ul>
    </div>
  );
};

export default FileList;

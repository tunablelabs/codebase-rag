interface FileListProps {
  visible: boolean;
  files: string[];
}
//  {stats && <pre>{JSON.stringify(stats, null, 2)}</pre>}

export function FileListComponent({ visible, files }: FileListProps) {
  if (!visible || files.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2 bg-white/70 p-4 rounded-lg shadow-lg backdrop-blur-sm dark:bg-slate-900/70">
    
      <h3 className="font-semibold text-slate-800 dark:text-slate-200 mb-3">
        Repository Folders
      </h3>
      <ul className="space-y-2">
        {files.map((file, index) => (
          <li 
            key={index}
            className="flex items-center gap-2 text-slate-700 dark:text-slate-300"
          >
            <svg
              className="w-4 h-4 text-slate-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <span>{file}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default FileListComponent;
import React from "react";

interface Stats {
  total_code_files: number;
  language_distribution: Record<string, string>;
}


const ShowStats: React.FC<Stats> = ({ stats }: Stats) => {
  console.log(stats)
  console.log('inside stats',stats.language_distribution)
  return(
    <div className="space-y-2 bg-white/70 p-4 rounded-lg shadow-lg backdrop-blur-sm dark:bg-slate-900/70">
      <h3 className="font-semibold text-slate-800 dark:text-slate-200 mb-3">
        Repository Statistics
      </h3>
      <p className="mt-2 text-base-content/80">Total Code Files: {stats.total_code_files}</p>

      {stats.language_distribution && Object.keys(stats.language_distribution).length > 0 ? (
        <>
          <h4 className="text-lg font-medium text-base-content">Language Distribution:</h4>
          <ul className="space-y-2">
            {Object.entries(stats.language_distribution).map(([language, percentage]) => (
              <li key={language}>
                <strong>{language}:</strong> {percentage}
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="text-gray-500">No language data available</p>
      )}
    </div>
  )
};

export default ShowStats;

import React from "react";

interface Stats {
  total_code_files: number;
  language_distribution: Record<string, string>;
}

interface StatsProps {
  stats: Stats;
}

const ShowStats: React.FC<StatsProps> = ({ stats }) => {
  return (
    <div className="space-y-4 bg-base-100 dark:bg-base-200/10 p-4 rounded-lg 
      shadow-lg backdrop-blur-sm border border-base-200/50 dark:border-base-600 mt-10">
      <div>
        <h3 className="font-medium text-base-content">
          Repository Statistics
        </h3>
        <p className="text-sm text-base-content/70 mt-1">
          Total Code Files: {stats.total_code_files}
        </p>
      </div>

      {stats.language_distribution && Object.keys(stats.language_distribution).length > 0 ? (
        <div className="space-y-3">
          <h4 className="font-medium text-base-content">
            Language Distribution
          </h4>
          <div className="space-y-2">
            {Object.entries(stats.language_distribution).map(([language, percentage]) => (
              <div 
                key={language}
                className="flex items-center justify-between p-2 rounded-md
                  bg-base-200/50 dark:bg-base-300/30"
              >
                <span className="text-sm text-base-content">
                  {language}
                </span>
                <span className="text-sm text-base-content/80 font-mono">
                  {String(percentage)}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="text-sm text-base-content/60">
          No language distribution data available
        </p>
      )}
    </div>
  );
};

export default ShowStats;
import React from 'react';

interface EnhancedTextResponseProps {
  text: string;
  isUser?: boolean;
}

const EnhancedTextResponse: React.FC<EnhancedTextResponseProps> = ({ text, isUser = false }) => {
  // Split text into paragraphs
  const paragraphs = text.split('\n\n').filter((p: string) => p.trim());
  
  const formatParagraph = (paragraph: string) => {
    // Special handling for section headers (if they end with a colon)
    if (paragraph.trim().endsWith(':')) {
      return (
        <h3 className={`text-base font-semibold mb-2 mt-4 
          ${isUser ? 'text-primary-content' : 'text-base-content/90'}`}
        >
          {paragraph}
        </h3>
      );
    }

    // Handle emphasis using asterisks or underscores
    const formattedText = paragraph.split(/(\*\*.*?\*\*|\*.*?\*|_.*?_)/).map((part: string, index: number) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        // Strong emphasis
        return (
          <strong key={index} className={`font-semibold 
            ${isUser ? 'text-primary-content' : 'text-base-content'}`}
          >
            {part.slice(2, -2)}
          </strong>
        );
      } else if ((part.startsWith('*') && part.endsWith('*')) || 
                 (part.startsWith('_') && part.endsWith('_'))) {
        // Regular emphasis
        return (
          <em key={index} className={`italic 
            ${isUser ? 'text-primary-content/90' : 'text-base-content/90'}`}
          >
            {part.slice(1, -1)}
          </em>
        );
      }
      return part;
    });

    return (
      <p className={`leading-relaxed mb-3 last:mb-0
        ${isUser ? 'text-primary-content' : 'text-base-content/80'}`}
      >
        {formattedText}
      </p>
    );
  };

  return (
    <div className={`prose max-w-none ${isUser ? 'prose-invert' : 'dark:prose-invert'}`}>
      <div className="space-y-1">
        {paragraphs.map((paragraph: string, index: number) => (
          <div 
            key={index}
            className="transition-colors duration-200"
          >
            {formatParagraph(paragraph)}
          </div>
        ))}
      </div>
    </div>
  );
};

export default EnhancedTextResponse;
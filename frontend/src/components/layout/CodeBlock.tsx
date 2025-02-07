import React, { useState, useEffect } from 'react';
import { Check, Copy } from 'lucide-react';

interface CodeBlockProps {
  code: string;
  language?: string;
  maxWidth?: string;
}

interface CodeSpan {
  index: number;
  length: number;
  className: string;
}

const tokenColors = {
  keyword: 'text-[#FF7B72]',
  string: 'text-[#79C0FF]',
  function: 'text-[#D2A8FF]',
  number: 'text-[#79C0FF]',
  comment: 'text-[#8B949E] italic',
  punctuation: 'text-[#C9D1D9]',
  operator: 'text-[#FF7B72]',
  property: 'text-[#79C0FF]',
  variable: 'text-[#FFA657]',
  className: 'text-[#D2A8FF]',
};

const formatCode = (code: string): string => {
  // Improve code formatting by normalizing indentation
  const lines = code.split('\n');
  const minIndent = lines
    .filter(line => line.trim().length > 0)
    .reduce((min, line) => {
      const indent = line.match(/^\s*/)?.[0].length || 0;
      return Math.min(min, indent);
    }, Infinity);

  return lines
    .map(line => line.slice(minIndent))
    .join('\n');
};

const highlightCode = (code: string, language?: string) => {
  if (!language) return code;

  const rules = {
    keywords: {
      pattern: /\b(class|func|let|var|if|else|for|while|return|guard|switch|case|break|continue|import|struct|enum|protocol)\b/g,
      className: tokenColors.keyword
    },
    strings: {
      pattern: /"[^"\\]*(?:\\.[^"\\]*)*"/g,
      className: tokenColors.string
    },
    comments: {
      pattern: /\/\/.*|\/\*[\s\S]*?\*\//g,
      className: tokenColors.comment
    },
    functions: {
      pattern: /\b\w+(?=\s*[({])/g,
      className: tokenColors.function
    },
    numbers: {
      pattern: /\b\d+\.?\d*\b/g,
      className: tokenColors.number
    },
    classNames: {
      pattern: /\b[A-Z][a-zA-Z0-9]*\b/g,
      className: tokenColors.className
    },
    operators: {
      pattern: /[+\-*/%=<>!&|^~?:]+/g,
      className: tokenColors.operator
    },
    properties: {
      pattern: /\.\w+\b/g,
      className: tokenColors.property
    },
    punctuation: {
      pattern: /[{}[\](),;.]/g,
      className: tokenColors.punctuation
    }
  };

  let highlightedCode = code;
  const spans: CodeSpan[] = [];

  Object.entries(rules).forEach(([_, rule]) => {
    let match;
    while ((match = rule.pattern.exec(code)) !== null) {
      spans.push({
        index: match.index,
        length: match[0].length,
        className: rule.className
      });
    }
  });

  spans.sort((a, b) => b.index - a.index);

  spans.forEach(span => {
    const before = highlightedCode.slice(0, span.index);
    const content = highlightedCode.slice(span.index, span.index + span.length);
    const after = highlightedCode.slice(span.index + span.length);
    highlightedCode = `${before}<span class="${span.className}">${content}</span>${after}`;
  });

  return highlightedCode;
};

const CodeBlock: React.FC<CodeBlockProps> = ({ code, language, maxWidth = '90ch' }) => {
  const [isCopied, setIsCopied] = useState(false);
  const [highlightedCode, setHighlightedCode] = useState('');
  const [isOverflowing, setIsOverflowing] = useState(false);

  useEffect(() => {
    const formattedCode = formatCode(code);
    setHighlightedCode(highlightCode(formattedCode, language));
  }, [code, language]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  return (
    <div className="relative mt-2 rounded-lg bg-[#0D1117] text-[#C9D1D9] group">
      <div className="flex items-center justify-between px-4 py-2 bg-[#161B22] rounded-t-lg border-b border-[#30363D]">
        {language && (
          <div className="text-xs text-[#8B949E] font-medium">
            {language}
          </div>
        )}
        
        <button
          onClick={handleCopy}
          className="flex items-center gap-2 px-2 py-1 rounded
            hover:bg-[#30363D] text-[#8B949E] hover:text-[#C9D1D9]
            transition-all duration-200"
          aria-label={isCopied ? 'Copied!' : 'Copy code'}
        >
          {isCopied ? (
            <>
              <Check className="w-4 h-4" />
              <span className="text-xs">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              <span className="text-xs">Copy</span>
            </>
          )}
        </button>
      </div>

      <div className="relative">
        <div className="overflow-x-auto scrollbar-thin 
          scrollbar-track-[#161B22] scrollbar-thumb-[#30363D]
          hover:scrollbar-thumb-[#3B4048]">
          <pre 
            className="p-4 text-xs font-mono"
            style={{ 
              maxWidth: maxWidth,
              margin: '0 auto'
            }}
          >
            <code 
              className="block break-normal"
              dangerouslySetInnerHTML={{ __html: highlightedCode }}
            />
          </pre>
        </div>
      </div>
    </div>
  );
};

export default CodeBlock;
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
interface FormattedMarkdownProps {
  content: string;
}

const preprocessMarkdown = (content: string) => {
  return content
    .replace(/\r\n/g, "\n") // Normalize newlines
    .replace(/\n{3,}/g, "\n\n") // Replace 3+ newlines with exactly 2
    .trim() // Remove leading/trailing whitespace
    .replace(/(\S)\n(\S)/g, "$1 $2") // Replace single newlines with spaces
    .replace(/---\n+/g, "---\n") // Fix spacing after horizontal rules
    .replace(/\n+---/g, "\n---") // Fix spacing before horizontal rules
    .replace(/\n{2,}(#{1,6}\s.*)/g, "\n\n$1") // Fix spacing around headings
    .replace(/\n{2,}(\*\*[^*]+\*\*):?/g, "\n\n$1:"); // Fix spacing around bold text
};

const FormattedMarkdown: React.FC<FormattedMarkdownProps> = ({ content }) => {
  const processedContent = preprocessMarkdown(content);
  //console.log(processedContent, 'processedContent');
  
  return (
    <div className="markdown-content">
      <style jsx>{`
        .markdown-content :global(p),
        .markdown-content :global(ul) {
          margin-bottom: 1em;
        }
        .markdown-content :global(h1),
        .markdown-content :global(h2),
        .markdown-content :global(h3),
        .markdown-content :global(h4) {
          margin-top: 1em;
          margin-bottom: 0.5em;
        }
        .markdown-content :global(li) {
          margin-bottom: 0.3em;
        }
        .markdown-content :global(pre) {
          margin: 1em 0;
        }
        .markdown-content :global(code) {
          background-color: rgba(0, 0, 0, 0.05);
          padding: 0.2em;
        }
        .markdown-content {
          white-space: pre-wrap; /* Preserve newlines and spaces */
          word-wrap: break-word; /* Prevent overflow */
        }
      `}</style>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{processedContent}</ReactMarkdown>
    </div>
  );
};

export default FormattedMarkdown;

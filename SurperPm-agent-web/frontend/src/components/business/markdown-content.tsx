import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'

export function MarkdownContent({ content, className = '' }: { content: string; className?: string }) {
  return (
    <div className={className}>
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        h1: ({ children }) => <h1 className="aui-md-h1">{children}</h1>,
        h2: ({ children }) => <h2 className="aui-md-h2">{children}</h2>,
        h3: ({ children }) => <h3 className="aui-md-h3">{children}</h3>,
        h4: ({ children }) => <h4 className="aui-md-h4">{children}</h4>,
        h5: ({ children }) => <h5 className="aui-md-h5">{children}</h5>,
        h6: ({ children }) => <h6 className="aui-md-h6">{children}</h6>,
        p: ({ children }) => <p className="aui-md-p">{children}</p>,
        a: ({ href, children }) => <a href={href} className="aui-md-a" target="_blank" rel="noreferrer">{children}</a>,
        strong: ({ children }) => <strong className="aui-md-strong">{children}</strong>,
        blockquote: ({ children }) => <blockquote className="aui-md-blockquote">{children}</blockquote>,
        pre: ({ children }) => <pre className="aui-md-pre">{children}</pre>,
        code: ({ className: cn, children, ...props }) => {
          const isBlock = cn?.startsWith('hljs') || cn?.startsWith('language-')
          if (isBlock) return <code className={cn} {...props}>{children}</code>
          return <code className="aui-md-inline-code" {...props}>{children}</code>
        },
        table: ({ children }) => <table className="aui-md-table">{children}</table>,
        th: ({ children }) => <th className="aui-md-th">{children}</th>,
        td: ({ children }) => <td className="aui-md-td">{children}</td>,
        tr: ({ children }) => <tr className="aui-md-tr">{children}</tr>,
        ul: ({ children }) => <ul className="aui-md-ul">{children}</ul>,
        ol: ({ children }) => <ol className="aui-md-ol">{children}</ol>,
        hr: () => <hr className="aui-md-hr" />,
      }}
    >
      {content}
    </ReactMarkdown>
    </div>
  )
}

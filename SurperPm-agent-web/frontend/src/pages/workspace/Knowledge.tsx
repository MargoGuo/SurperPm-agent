import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Text } from "@/components/retroui/Text";
import { MarkdownContent } from "@/components/business/markdown-content";
import { BookOpen, FileText, Folder, FolderOpen } from "lucide-react";

interface TreeNode {
  name: string;
  path: string;
  children?: TreeNode[];
}

function isDir(node: TreeNode): boolean {
  return Array.isArray(node.children);
}

export default function KnowledgePage() {
  const { slug } = useParams<{ slug: string }>();
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  if (!slug) return null;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b-2 border-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 border-2 border-border bg-primary flex items-center justify-center shadow-[3px_3px_0_0_#000]">
            <BookOpen size={20} />
          </div>
          <div>
            <Text as="h2" className="text-xl">Knowledge Base</Text>
            <p className="text-sm text-muted-foreground">
              项目知识库 — 文档、规范与决策记录
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex flex-1 min-h-0">
        {/* Sidebar tree */}
        <aside className="w-72 border-r-2 border-border overflow-y-auto p-4 bg-card">
          <p className="text-xs font-head font-bold uppercase tracking-wider text-muted-foreground mb-3">
            文件目录
          </p>
          <KnowledgeTree selectedPath={selectedPath} onSelect={setSelectedPath} />
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-auto p-6">
          {selectedPath ? (
            <FileContent path={selectedPath} />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-3">
              <div className="w-16 h-16 border-2 border-border bg-muted/30 flex items-center justify-center">
                <FileText size={32} className="text-muted-foreground/50" />
              </div>
              <p className="font-head text-sm">选择文件查看内容</p>
              <p className="text-xs text-center max-w-xs">
                从左侧目录树选择一个文件，内容将在此处显示。
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

function KnowledgeTree({
  selectedPath,
  onSelect,
}: {
  selectedPath: string | null;
  onSelect: (path: string) => void;
}) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["knowledge-tree"],
    queryFn: () => api.get<TreeNode>("/knowledge/tree"),
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-foreground border-t-transparent" />
        加载中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-xs text-destructive border-2 border-destructive/30 p-2 bg-destructive/5">
        加载失败: {(error as Error).message}
      </div>
    );
  }

  if (!data || !data.children || data.children.length === 0) {
    return (
      <div className="text-xs text-muted-foreground border-2 border-border p-3 bg-muted/20">
        <p className="font-head font-bold mb-1">暂无知识文件</p>
        <p>将文件推送到知识库仓库即可开始使用。</p>
      </div>
    );
  }

  return (
    <TreeNodeList
      nodes={data.children}
      depth={0}
      selectedPath={selectedPath}
      onSelect={onSelect}
    />
  );
}

function TreeNodeList({
  nodes,
  depth,
  selectedPath,
  onSelect,
}: {
  nodes: TreeNode[];
  depth: number;
  selectedPath: string | null;
  onSelect: (path: string) => void;
}) {
  return (
    <ul className="space-y-0.5">
      {nodes.map((node) => (
        <TreeItem
          key={node.path}
          node={node}
          depth={depth}
          selectedPath={selectedPath}
          onSelect={onSelect}
        />
      ))}
    </ul>
  );
}

function TreeItem({
  node,
  depth,
  selectedPath,
  onSelect,
}: {
  node: TreeNode;
  depth: number;
  selectedPath: string | null;
  onSelect: (path: string) => void;
}) {
  const [expanded, setExpanded] = useState(depth < 1);
  const isSelected = selectedPath === node.path;
  const nodeIsDir = isDir(node);

  const handleClick = () => {
    if (nodeIsDir) {
      setExpanded(!expanded);
    } else {
      onSelect(node.path);
    }
  };

  return (
    <li>
      <button
        onClick={handleClick}
        className={`w-full text-left text-sm px-2 py-1.5 flex items-center gap-1.5 transition-all ${
          isSelected
            ? "bg-primary/20 border-l-2 border-l-primary font-medium"
            : "hover:bg-muted border-l-2 border-l-transparent"
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {nodeIsDir ? (
          expanded ? <FolderOpen size={14} className="text-primary shrink-0" /> : <Folder size={14} className="text-muted-foreground shrink-0" />
        ) : (
          <FileText size={14} className="text-muted-foreground shrink-0" />
        )}
        <span className="truncate">{node.name}</span>
      </button>
      {nodeIsDir && expanded && node.children && node.children.length > 0 && (
        <TreeNodeList
          nodes={node.children}
          depth={depth + 1}
          selectedPath={selectedPath}
          onSelect={onSelect}
        />
      )}
    </li>
  );
}

function FileContent({ path }: { path: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["knowledge-content", path],
    queryFn: () =>
      api.get<{ content: string; path: string }>(
        `/knowledge/file?path=${encodeURIComponent(path)}`
      ),
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-foreground border-t-transparent" />
        加载文件中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="border-2 border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
        加载失败: {(error as Error).message}
      </div>
    );
  }

  const isMarkdown = path.endsWith('.md') || path.endsWith('.mdx');
  const content = data?.content ?? "";

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 border-b-2 border-border pb-2">
        <FileText size={16} className="text-muted-foreground" />
        <span className="font-mono text-xs text-muted-foreground">{path}</span>
      </div>
      {isMarkdown ? (
        <div className="border-2 border-border bg-white p-6 overflow-auto max-h-[calc(100vh-280px)] shadow-[2px_2px_0_0_rgba(0,0,0,0.1)]">
          <MarkdownContent content={content} />
        </div>
      ) : (
        <pre className="aui-md-pre overflow-auto max-h-[calc(100vh-280px)]">
          <code>{content}</code>
        </pre>
      )}
    </div>
  );
}

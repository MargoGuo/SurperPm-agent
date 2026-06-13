import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card } from "@/components/retroui/Card";
import { Badge } from "@/components/retroui/Badge";

interface Learning {
  id: string;
  goal_id: number;
  goal_title: string;
  status: string;
  summary: string;
  pr_url: string | null;
  token_used: number | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

function statusVariant(status: string): "default" | "outline" | "solid" | "surface" {
  if (status === "success") return "solid";
  if (status === "failed" || status === "timeout") return "outline";
  return "surface";
}

export function LearningRecords() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["learnings"],
    queryFn: () => api.get<Learning[]>("/learnings"),
  });

  return (
    <div className="flex flex-col">
      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-foreground border-t-transparent" />
          加载中...
        </div>
      )}

      {error && (
        <Card className="max-w-lg">
          <Card.Content>
            <p className="text-sm text-destructive py-4">
              加载失败: {(error as Error).message}
            </p>
          </Card.Content>
        </Card>
      )}

      {data && data.length === 0 && (
        <Card className="max-w-lg">
          <Card.Content>
            <p className="text-sm text-muted-foreground py-4">
              暂无执行记录。完成一次 Goal 执行后这里会出现蒸馏小结。
            </p>
          </Card.Content>
        </Card>
      )}

      {data && data.length > 0 && (
        <div className="grid gap-4 max-w-3xl">
          {data.map((item) => (
            <Card key={item.id}>
              <Card.Header>
                <div className="flex items-center justify-between gap-3">
                  <Card.Title className="text-base">{item.goal_title}</Card.Title>
                  <Badge variant={statusVariant(item.status)}>{item.status}</Badge>
                </div>
              </Card.Header>
              <Card.Content>
                <p className="text-sm whitespace-pre-wrap mb-3">{item.summary}</p>
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                  <span>Goal #{item.goal_id}</span>
                  {item.token_used != null && <span>Tokens: {item.token_used}</span>}
                  {item.finished_at && (
                    <span>完成: {new Date(item.finished_at).toLocaleString()}</span>
                  )}
                  {item.pr_url && (
                    <a
                      href={item.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-foreground underline underline-offset-2 hover:text-muted-foreground"
                    >
                      查看 PR
                    </a>
                  )}
                </div>
              </Card.Content>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

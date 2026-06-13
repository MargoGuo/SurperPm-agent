import { useParams } from "react-router-dom";
import { Text } from "@/components/retroui/Text";
import { KanbanBoard } from "../../components/goals/kanban-board";
import { CreateGoalDialog } from "../../components/goals/create-goal-dialog";

export default function GoalsPage() {
  const { slug } = useParams<{ slug: string }>();

  if (!slug) return null;

  return (
    <div className="flex flex-col h-full p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <Text as="h2" className="text-2xl">Goals</Text>
          <p className="text-sm text-muted-foreground mt-1">管理和跟踪项目目标</p>
        </div>
        <CreateGoalDialog workspaceId={slug} />
      </div>
      <div className="flex-1 min-h-0">
        <KanbanBoard workspaceId={slug} />
      </div>
    </div>
  );
}

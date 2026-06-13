import { GoalProvider, useGoalState, useGoalDispatch } from './goal/useGoalStore'
import BoardView from './goal/BoardView'
import ListView from './goal/ListView'
import SubmitDrawer from './goal/SubmitDrawer'
import RunDetailDrawer from './goal/RunDetailDrawer'
import { Button } from '@/components/retroui/Button'

function GoalContent() {
  const { viewMode, isSubmitOpen, selectedRunId, runs } = useGoalState()
  const dispatch = useGoalDispatch()
  const selectedRun = runs.find((r) => r.id === selectedRunId) ?? null

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-6 py-4 border-b-2">
        <h1 className="text-xl font-bold">Goal 控制台</h1>
        <div className="flex items-center gap-3">
          <div className="flex border-2 border-border">
            <button
              onClick={() => dispatch({ type: 'SET_VIEW_MODE', mode: 'board' })}
              className={`px-4 py-1.5 text-sm font-medium cursor-pointer transition-colors ${
                viewMode === 'board'
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-accent'
              }`}
            >
              看板
            </button>
            <button
              onClick={() => dispatch({ type: 'SET_VIEW_MODE', mode: 'list' })}
              className={`px-4 py-1.5 text-sm font-medium cursor-pointer transition-colors border-l-2 border-border ${
                viewMode === 'list'
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-accent'
              }`}
            >
              列表
            </button>
          </div>
          <Button onClick={() => dispatch({ type: 'TOGGLE_SUBMIT' })}>
            + 新建执行
          </Button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-auto">
        {viewMode === 'board' ? <BoardView /> : <ListView />}
      </div>

      {isSubmitOpen && <SubmitDrawer />}
      {selectedRun && <RunDetailDrawer run={selectedRun} />}
    </div>
  )
}

export default function Goal() {
  return (
    <GoalProvider>
      <GoalContent />
    </GoalProvider>
  )
}

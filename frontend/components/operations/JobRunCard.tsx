import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { getJobStatusColor, getJobStatusLabel } from '@/lib/operations/taskStateUtils'
import type { JobRun } from '@/lib/operations/types'
import { MOMENT_FORMAT } from '@/lib/time'

interface JobRunCardProps {
  run: JobRun
}

function formatTimestamp(value: string | null): string {
  if (value === null) return '—'
  return MOMENT_FORMAT.format(new Date(value))
}

/**
 * One extraction run, as returned by `GET /api/v1/operations/jobs`.
 *
 * A failed run keeps its reason on screen rather than only in the worker's
 * logs: whoever looks at the job history tomorrow will not have that stdout.
 */
export function JobRunCard({ run }: JobRunCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{run.task_name}</CardTitle>
          <span className={`font-bold ${getJobStatusColor(run.status)}`}>
            {getJobStatusLabel(run.status)}
          </span>
        </div>
        <CardDescription>
          Inicio {formatTimestamp(run.started_at)} · Fin {formatTimestamp(run.finished_at)}
          {run.attempts > 1 && ` · ${run.attempts} intentos`}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {run.status === 'SUCCEEDED' && run.result != null && (
          <div className="p-3 bg-ok-surface rounded border border-ok-border">
            <p className="text-sm font-medium text-ok mb-2">Resultado:</p>
            <pre className="text-xs overflow-auto text-ok">
              {JSON.stringify(run.result, null, 2)}
            </pre>
          </div>
        )}

        {run.status === 'FAILED' && run.error !== null && (
          <div className="p-3 bg-danger-surface rounded border border-danger-border">
            <p className="text-sm font-medium text-danger mb-2">Error:</p>
            <p className="text-xs text-danger">{run.error}</p>
          </div>
        )}

        <details className="cursor-pointer">
          <summary className="text-xs text-muted-foreground hover:text-foreground">
            Ver detalles completos
          </summary>
          <pre className="text-xs overflow-auto mt-2 p-2 bg-muted rounded">
            {JSON.stringify(run, null, 2)}
          </pre>
        </details>
      </CardContent>
    </Card>
  )
}

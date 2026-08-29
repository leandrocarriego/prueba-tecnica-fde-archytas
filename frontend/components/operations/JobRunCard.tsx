import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { getJobStatusColor, getJobStatusLabel } from '@/lib/operations/taskStateUtils'
import type { JobRun } from '@/lib/operations/types'

interface JobRunCardProps {
  run: JobRun
}

function formatTimestamp(value: string | null): string {
  if (value === null) return '—'
  return new Date(value).toLocaleString('es-AR')
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
          <div className="p-3 bg-emerald-50 rounded border border-emerald-200">
            <p className="text-sm font-medium text-emerald-800 mb-2">Resultado:</p>
            <pre className="text-xs overflow-auto text-emerald-700">
              {JSON.stringify(run.result, null, 2)}
            </pre>
          </div>
        )}

        {run.status === 'FAILED' && run.error !== null && (
          <div className="p-3 bg-red-50 rounded border border-red-200">
            <p className="text-sm font-medium text-red-800 mb-2">Error:</p>
            <p className="text-xs text-red-700">{run.error}</p>
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

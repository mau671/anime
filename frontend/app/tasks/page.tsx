"use client"

import * as React from "react"

import { PageShell } from "@/components/page-shell"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  runExportQbittorrentJob,
  runInitDbJob,
  runScanNyaaJob,
  runSyncAnilistJob,
  useJobHistory,
  useJobStatistics,
  useRunningJobs,
} from "@/lib/api-hooks"
import type { JobExecutionResponse, JobHistoryEntry } from "@/lib/api-types"
import { cn } from "@/lib/utils"

type JobActionKey =
  | "Sincronización Anilist"
  | "Escaneo Nyaa"
  | "Inicializar base de datos"
  | "Exportar a qBittorrent"

const actionHandlers: Record<JobActionKey, () => Promise<JobExecutionResponse>> = {
  "Sincronización Anilist": () => runSyncAnilistJob(),
  "Escaneo Nyaa": () => runScanNyaaJob(),
  "Inicializar base de datos": () => runInitDbJob(),
  "Exportar a qBittorrent": () => runExportQbittorrentJob({}),
}

type ActionsCardProps = {
  onJobTriggered?: (jobType: JobActionKey, response: JobExecutionResponse) => void
}

function ActionsCard({ onJobTriggered }: ActionsCardProps) {
  const [workingKey, setWorkingKey] = React.useState<JobActionKey | null>(null)

  const runAction = async (key: JobActionKey) => {
    const action = actionHandlers[key]
    if (!action) return

    try {
      setWorkingKey(key)
      const result = await action()
      onJobTriggered?.(key, result)
    } catch (error) {
      console.error(error)
      onJobTriggered?.(key, {
        status: "failed",
        detail: "La solicitud falló",
        task_id: "",
        result: null,
      })
    } finally {
      setWorkingKey(null)
    }
  }

  const buttons: JobActionKey[] = [
    "Sincronización Anilist",
    "Escaneo Nyaa",
    "Inicializar base de datos",
    "Exportar a qBittorrent",
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Acciones rápidas</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {buttons.map((key) => (
          <Button
            key={key}
            variant={key === "Inicializar base de datos" ? "destructive" : "outline"}
            onClick={() => runAction(key)}
            disabled={workingKey !== null}
          >
            {workingKey === key ? `${key}...` : key}
          </Button>
        ))}
      </CardContent>
    </Card>
  )
}

function StatusBadge({ status }: { status?: string | null }) {
  if (!status) return null
  const variant =
    status === "completed" || status === "ok"
      ? "success"
      : status === "queued"
        ? "secondary"
        : status === "running"
          ? "outline"
          : "destructive"

  return (
    <Badge
      variant={variant === "success" ? "default" : variant}
      className={cn(
        "capitalize",
        variant === "success" && "bg-emerald-600 text-white",
        variant === "destructive" && "bg-destructive text-destructive-foreground"
      )}
    >
      {status}
    </Badge>
  )
}

function formatDate(value?: string | null) {
  if (!value) return "-"
  try {
    return new Intl.DateTimeFormat("es", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(value))
  } catch (error) {
    console.error("Error parsing date", error)
    return value
  }
}

function RunningJobsCard() {
  const { data, isLoading } = useRunningJobs()

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Trabajos en ejecución</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : !data || data.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No hay trabajos ejecutándose en este momento.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {data.map((job) => (
              <div
                key={job.id ?? job.task_id ?? `${job.task_type}-${job.started_at}`}
                className="border-border/50 flex flex-col gap-1 rounded-md border p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium capitalize">
                    {job.task_type.replace(/_/g, " ")}
                  </span>
                  <StatusBadge status={job.status ?? "running"} />
                </div>
                {job.error ? (
                  <span className="text-sm text-destructive">{job.error}</span>
                ) : null}
                <span className="text-xs text-muted-foreground">
                  Inició: {formatDate(job.started_at)}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function renderJobDetail(job: JobHistoryEntry) {
  if (job.error) return job.error
  if (job.result && Object.keys(job.result).length > 0) {
    return JSON.stringify(job.result)
  }
  if (job.parameters && Object.keys(job.parameters).length > 0) {
    return JSON.stringify(job.parameters)
  }
  return "-"
}

function JobHistoryTable({
  entries,
  isLoading,
}: {
  entries?: JobHistoryEntry[]
  isLoading: boolean
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Historial reciente</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-48 w-full" />
        ) : (
        <Table>
          <TableHeader>
            <TableRow>
                <TableHead>Trabajo</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Detalles</TableHead>
                <TableHead>Inicio</TableHead>
                <TableHead>Fin</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
              {!entries || entries.length === 0 ? (
              <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    Aún no hay trabajos registrados.
                </TableCell>
              </TableRow>
            ) : (
                entries.map((job) => (
                  <TableRow key={job.id ?? job.task_id ?? `${job.task_type}-${job.created_at}`}>
                    <TableCell className="max-w-[280px]">
                      <div className="flex flex-col gap-1">
                        <span className="font-medium capitalize">
                          {job.task_type.replace(/_/g, " ")}
                        </span>
                        {typeof job.anilist_id === "number" ? (
                          <span className="text-xs text-muted-foreground">
                            Anilist ID: {job.anilist_id}
                          </span>
                        ) : null}
                      </div>
                  </TableCell>
                  <TableCell>
                      <StatusBadge status={job.status} />
                    </TableCell>
                    <TableCell className="max-w-[360px] text-sm">
                      {renderJobDetail(job)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(job.started_at ?? job.created_at)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(job.completed_at ?? job.updated_at)}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        )}
      </CardContent>
    </Card>
  )
}

function JobSummaryCard() {
  const { data: stats, isLoading } = useJobStatistics({ period: "24h" })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Resumen 24h</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 text-sm">
        {isLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : !stats || stats.statistics.length === 0 ? (
          <p className="text-muted-foreground">No hay estadísticas disponibles.</p>
        ) : (
          stats.statistics.map((item) => (
            <div key={item.status} className="flex items-center justify-between rounded-md border px-3 py-2">
              <span className="capitalize">{item.status.replace(/_/g, " ")}</span>
              <span className="font-semibold">{item.count}</span>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  )
}

export default function TasksPage() {
  const {
    data: historyData,
    isLoading: historyLoading,
  } = useJobHistory({ limit: 25 })

  const handleJobTriggered = React.useCallback(
    async () => {
      // Las mutaciones relevantes se disparan desde runJob
    },
    []
  )

  return (
    <PageShell
      title="Trabajos"
      description="Ejecuta acciones manuales y revisa el historial del sistema."
    >
      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <div className="flex flex-col gap-6">
          <ActionsCard onJobTriggered={handleJobTriggered} />
          <JobSummaryCard />
          <RunningJobsCard />
        </div>
        <div className="flex flex-col gap-6">
          <JobHistoryTable entries={historyData?.tasks} isLoading={historyLoading} />
        </div>
      </div>
    </PageShell>
  )
}



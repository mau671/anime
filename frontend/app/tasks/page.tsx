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
  initDatabase,
  reloadScheduler,
  syncAnilist,
  triggerScan,
  useRunningTasks,
  useTaskHistory,
  useTaskStatistics,
  useTaskTypes,
} from "@/lib/api-hooks"
import type { TaskHistoryEntry, TaskStatusResponse } from "@/lib/api-types"
import { cn } from "@/lib/utils"

type TaskActionKey =
  | "Sincronización Anilist"
  | "Escaneo Nyaa"
  | "Recargar planificador"
  | "Inicializar base de datos"

type HistoryEntry = {
  task: TaskActionKey
  status: TaskStatusResponse["status"]
  detail: string
  timestamp: string
}

const actionHandlers: Record<TaskActionKey, () => Promise<TaskStatusResponse>> = {
  "Sincronización Anilist": () =>
    syncAnilist({ season: null, season_year: null }),
  "Escaneo Nyaa": () => triggerScan(),
  "Recargar planificador": () => reloadScheduler(),
  "Inicializar base de datos": () => initDatabase(),
}

type ActionsCardProps = {
  onTaskTriggered?: (taskType: string, response: TaskStatusResponse) => void
}

function ActionsCard({ onTaskTriggered }: ActionsCardProps) {
  const [workingKey, setWorkingKey] = React.useState<TaskActionKey | null>(null)

  const runAction = async (key: TaskActionKey) => {
    const action = actionHandlers[key]
    if (!action) return

    try {
      setWorkingKey(key)
      const result = await action()
      onTaskTriggered?.(key, result)
    } catch (error) {
      console.error(error)
      onTaskTriggered?.(key, {
        status: "failed",
        detail: "La solicitud falló",
      })
    } finally {
      setWorkingKey(null)
    }
  }

  const buttons: TaskActionKey[] = [
    "Sincronización Anilist",
    "Escaneo Nyaa",
    "Recargar planificador",
    "Inicializar base de datos",
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

function RunningTasksCard() {
  const { data, isLoading } = useRunningTasks()

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Tareas en ejecución</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : !data || data.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No hay tareas ejecutándose en este momento.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {data.map((task) => (
              <div
                key={task.id ?? task.task_id ?? `${task.task_type}-${task.started_at}`}
                className="border-border/50 flex flex-col gap-1 rounded-md border p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">
                    {task.task_type ?? "Tarea desconocida"}
                  </span>
                  <StatusBadge status={task.status ?? "running"} />
                </div>
                {task.detail ? (
                  <span className="text-sm text-muted-foreground">{task.detail}</span>
                ) : null}
                <span className="text-xs text-muted-foreground">
                  Inició: {formatDate(task.started_at)}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function TaskHistoryTable({
  entries,
  isLoading,
}: {
  entries?: TaskHistoryEntry[]
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
                <TableHead>Tarea</TableHead>
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
                    Aún no hay tareas registradas.
                  </TableCell>
                </TableRow>
              ) : (
                entries.map((item) => (
                  <TableRow key={item.id ?? item.task_id ?? `${item.task_type}-${item.created_at}`}>
                    <TableCell className="max-w-[280px]">
                      <div className="flex flex-col gap-1">
                        <span className="font-medium capitalize">
                          {item.task_type ?? "Desconocido"}
                        </span>
                        {typeof item.anilist_id === "number" ? (
                          <span className="text-xs text-muted-foreground">
                            Anilist ID: {item.anilist_id}
                          </span>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={item.status} />
                    </TableCell>
                    <TableCell className="max-w-[360px] text-sm">
                      {item.detail ?? "-"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(item.started_at ?? item.created_at)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(item.finished_at ?? item.updated_at)}
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

function TaskSummaryCard() {
  const { data: stats, isLoading } = useTaskStatistics({ period: "24h" })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Resumen 24h</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 text-sm">
        {isLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : !stats || Object.keys(stats).length === 0 ? (
          <p className="text-muted-foreground">
            No hay estadísticas disponibles.
          </p>
        ) : (
          Object.entries(stats).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between rounded-md border px-3 py-2">
              <span className="capitalize">{key.replace(/_/g, " ")}</span>
              <span className="font-semibold">
                {typeof value === "number" || typeof value === "string"
                  ? value
                  : JSON.stringify(value)}
              </span>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  )
}

export default function TasksPage() {
  const { data: historyData, isLoading: historyLoading, mutate: refreshHistory } =
    useTaskHistory({ limit: 25 })
  const { data: taskTypes } = useTaskTypes()

  const handleTaskTriggered = React.useCallback(
    async (_taskType: string, _response: TaskStatusResponse) => {
      await Promise.all([refreshHistory()])
    },
    [refreshHistory]
  )

  return (
    <PageShell
      title="Tareas"
      description="Ejecuta acciones manuales y revisa el historial."
    >
      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <div className="flex flex-col gap-6">
          <ActionsCard onTaskTriggered={handleTaskTriggered} />
          <TaskSummaryCard />
          <RunningTasksCard />
        </div>
        <div className="flex flex-col gap-6">
          <TaskHistoryTable entries={historyData?.items} isLoading={historyLoading} />
        </div>
      </div>
    </PageShell>
  )
}



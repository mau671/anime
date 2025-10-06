"use client"

import * as React from "react"

import { PageShell } from "@/components/page-shell"
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
} from "@/lib/api-hooks"
import type { TaskStatusResponse } from "@/lib/api-types"

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

const historyPlaceholder: HistoryEntry[] = []

function useTaskHistory() {
  const [history, setHistory] = React.useState<HistoryEntry[]>(historyPlaceholder)

  const addEntry = React.useCallback((entry: Omit<HistoryEntry, "timestamp">) => {
    setHistory((prev) => [
      { ...entry, timestamp: new Date().toISOString() },
      ...prev,
    ])
  }, [])

  return { history, addEntry }
}

const actionHandlers: Record<
  TaskActionKey,
  () => Promise<TaskStatusResponse>
> = {
  "Sincronización Anilist": () =>
    syncAnilist({ season: null, season_year: null }),
  "Escaneo Nyaa": () => triggerScan(),
  "Recargar planificador": () => reloadScheduler(),
  "Inicializar base de datos": () => initDatabase(),
}

function ActionsCard({ onMutate }: { onMutate: (entry: HistoryEntry) => void }) {
  const [workingKey, setWorkingKey] = React.useState<TaskActionKey | null>(null)

  const runAction = async (key: TaskActionKey) => {
    const action = actionHandlers[key]
    if (!action) return

    try {
      setWorkingKey(key)
      const result = await action()
      onMutate({
        task: key,
        status: result.status,
        detail: result.detail ?? key,
        timestamp: new Date().toISOString(),
      })
    } catch (error) {
      console.error(error)
      onMutate({
        task: key,
        status: "failed",
        detail: "La solicitud falló",
        timestamp: new Date().toISOString(),
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

function HistoryTable({ history }: { history: HistoryEntry[] }) {
  if (!history) {
    return <Skeleton className="h-48 w-full" />
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Historial reciente</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tarea</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Detalles</TableHead>
              <TableHead>Fecha</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {history.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground">
                  Aún no hay tareas registradas.
                </TableCell>
              </TableRow>
            ) : (
              history.map((item, index) => (
                <TableRow key={`${item.task}-${index}`}>
                  <TableCell>{item.task}</TableCell>
                  <TableCell className="uppercase text-xs font-semibold">
                    {item.status}
                  </TableCell>
                  <TableCell>{item.detail}</TableCell>
                  <TableCell>
                    {new Intl.DateTimeFormat("es", {
                      dateStyle: "short",
                      timeStyle: "short",
                    }).format(new Date(item.timestamp))}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

export default function TasksPage() {
  const { history, addEntry } = useTaskHistory()

  return (
    <PageShell
      title="Tareas"
      description="Ejecuta acciones manuales y revisa el historial."
    >
      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <ActionsCard
          onMutate={(entry) =>
            addEntry({ task: entry.task, status: entry.status, detail: entry.detail })
          }
        />
        <HistoryTable history={history} />
      </div>
    </PageShell>
  )
}



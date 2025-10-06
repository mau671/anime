"use client"

import * as React from "react"

import { PageShell } from "@/components/page-shell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useHealth } from "@/lib/api-hooks"

function HealthStatus() {
  const { data, isLoading, error } = useHealth()

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Estado del sistema</CardTitle>
        </CardHeader>
        <CardContent className="text-destructive">
          No se pudo obtener el estado del servidor.
        </CardContent>
      </Card>
    )
  }

  if (isLoading || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Estado del sistema</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-48" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Estado del sistema</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Estado</span>
          <span className="text-sm uppercase font-semibold text-emerald-600">
            {data.status}
          </span>
        </div>
        {data.detail ? (
          <p className="text-muted-foreground text-sm">{data.detail}</p>
        ) : null}
      </CardContent>
    </Card>
  )
}

export default function HealthPage() {
  return (
    <PageShell
      title="Salud"
      description="Verifica que los servicios esenciales estén en funcionamiento."
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <HealthStatus />
      </div>
    </PageShell>
  )
}



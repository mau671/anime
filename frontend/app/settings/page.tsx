"use client"

import * as React from "react"

import { PageShell } from "@/components/page-shell"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import {
  useSettings,
  useGlobalSettings,
  useAppConfig,
  updateGlobalSettings,
  updateAppConfig,
  testQbittorrentConnection,
  GLOBAL_SETTINGS_ID,
} from "@/lib/api-hooks"
import type { AppConfig, SettingsEnvelope } from "@/lib/api-types"
import { AVAILABLE_VARIABLES, TEMPLATE_EXAMPLES } from "@/lib/path-template"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"

type SettingsCardProps = {
  settings?: SettingsEnvelope[]
  onOpenAppConfig: () => void
}

function SettingsCard({ settings, onOpenAppConfig }: SettingsCardProps) {
  // Use anilist_id = 0 for global settings
  const globalSettings = settings?.find(
    (s) => s.settings.anilist_id === GLOBAL_SETTINGS_ID
  )
  const defaults = globalSettings?.settings
  const { data: latestGlobalSettings } = useGlobalSettings()
  
  const [showVariables, setShowVariables] = React.useState(false)
  const [template, setTemplate] = React.useState("")
  const [resolution, setResolution] = React.useState("")
  const [subgroup, setSubgroup] = React.useState("")
  const [isSaving, setIsSaving] = React.useState(false)
  const [lastSavedAt, setLastSavedAt] = React.useState<string | undefined>(
    defaults?.updated_at ?? defaults?.created_at ?? undefined
  )

  React.useEffect(() => {
    const source = latestGlobalSettings?.settings ?? defaults
    if (!source) return

    setTemplate(source.save_path_template ?? "")
    setResolution(source.preferred_resolution ?? "")
    setSubgroup(source.preferred_subgroup ?? "")
    setLastSavedAt(source.updated_at ?? source.created_at ?? undefined)
  }, [defaults, latestGlobalSettings])

  const handleSave = async () => {
    try {
      setIsSaving(true)
      await updateGlobalSettings({
        save_path_template: template || null,
        preferred_resolution: resolution || null,
        preferred_subgroup: subgroup || null,
      })
      const now = new Date().toISOString()
      setLastSavedAt(now)
      toast.success("Ajustes guardados correctamente")
    } catch (error) {
      console.error(error)
      toast.error("No se pudieron guardar los ajustes")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Valores por defecto</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div>
              <h3 className="text-sm font-medium leading-none">Template de ruta</h3>
              <p className="text-muted-foreground text-sm">
                Define un template con variables para generar rutas automáticamente.{" "}
                <Button
                  type="button"
                  variant="link"
                  className="h-auto p-0 text-sm"
                  onClick={() => setShowVariables(true)}
                >
                  Ver variables disponibles
                </Button>
              </p>
            </div>
            <Textarea
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              placeholder={TEMPLATE_EXAMPLES[0]}
              rows={3}
              className="font-mono text-xs"
            />
            <div className="flex flex-wrap gap-2">
              {TEMPLATE_EXAMPLES.slice(0, 3).map((example, i) => (
                <Button
                  key={i}
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setTemplate(example)}
                  className="text-xs"
                >
                  Ejemplo {i + 1}
                </Button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <div>
              <h3 className="text-sm font-medium leading-none">Resolución por defecto</h3>
              <p className="text-muted-foreground text-sm">
                Aplica cuando no se configure una resolución específica para un anime.
              </p>
            </div>
            <Input
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              placeholder="1080p"
            />
          </div>

          <div className="flex flex-col gap-2">
            <div>
              <h3 className="text-sm font-medium leading-none">Fansub por defecto</h3>
              <p className="text-muted-foreground text-sm">
                Se utilizará como preferencia inicial para los nuevos animes.
              </p>
            </div>
            <Input
              value={subgroup}
              onChange={(e) => setSubgroup(e.target.value)}
              placeholder="Fansub"
            />
          </div>

          <div className="flex flex-col gap-2 border-t pt-4">
            {lastSavedAt ? (
              <span className="text-xs text-muted-foreground">
                Última actualización: {new Intl.DateTimeFormat("es", {
                  dateStyle: "short",
                  timeStyle: "short",
                }).format(new Date(lastSavedAt))}
              </span>
            ) : null}
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving && <Loader2 className="size-4 animate-spin" />}
              Guardar cambios
            </Button>
          </div>
        </CardContent>
      </Card>

      <Button
        type="button"
        variant="outline"
        className="self-start"
        onClick={onOpenAppConfig}
      >
        Configuración de aplicación
      </Button>

      <Dialog open={showVariables} onOpenChange={setShowVariables}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Variables disponibles para templates</DialogTitle>
            <DialogDescription>
              Usa estas variables en tus templates de ruta escribiéndolas entre llaves, por ejemplo: {"{currentYear}"}
            </DialogDescription>
          </DialogHeader>
          <ScrollArea className="h-[60vh] py-4">
            <div className="grid gap-3">
              {AVAILABLE_VARIABLES.map((variable) => (
                <div
                  key={variable.key}
                  className="flex items-start gap-3 rounded-md border p-3"
                >
                  <Badge variant="secondary" className="font-mono text-xs shrink-0">
                    {`{${variable.key}}`}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {variable.description}
                  </span>
                </div>
              ))}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </>
  )
}

function SyncCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Acciones programadas</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <div className="flex flex-col gap-1">
            <span className="text-sm font-medium">Temporada</span>
            <span className="text-muted-foreground text-sm">
              Próximamente podrás sincronizar con Anilist desde la interfaz.
            </span>
          </div>
          <Select disabled>
            <SelectTrigger className="w-full justify-between">
              <SelectValue placeholder="Selecciona una temporada" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="WINTER">Invierno</SelectItem>
              <SelectItem value="SPRING">Primavera</SelectItem>
              <SelectItem value="SUMMER">Verano</SelectItem>
              <SelectItem value="FALL">Otoño</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" disabled>
            Sincronizar catálogo
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export default function SettingsPage() {
  const { data: settings } = useSettings()
  const { data: appConfig, mutate: refreshAppConfig } = useAppConfig()
  const [appConfigDialogOpen, setAppConfigDialogOpen] = React.useState(false)
  const [testingConnection, setTestingConnection] = React.useState(false)
  const [appConfigForm, setAppConfigForm] = React.useState<AppConfig | undefined>(appConfig)

  React.useEffect(() => {
    setAppConfigForm(appConfig)
  }, [appConfig])

  const handleSaveAppConfig = async () => {
    if (!appConfigForm) return

    try {
      const { path_mappings, ...rest } = appConfigForm
      await updateAppConfig({
        ...rest,
        path_mappings,
      })
      toast.success("Configuración actualizada")
      await refreshAppConfig()
      setAppConfigDialogOpen(false)
    } catch (error) {
      console.error(error)
      toast.error("No se pudo actualizar la configuración")
    }
  }

  const handleTestConnection = async () => {
    try {
      setTestingConnection(true)
      const result = await testQbittorrentConnection()
      toast.success(result.detail ?? "Conexión exitosa")
    } catch (error) {
      console.error(error)
      toast.error("No se pudo conectar con qBittorrent")
    } finally {
      setTestingConnection(false)
    }
  }

  return (
    <PageShell
      title="Ajustes"
      description="Consulta los valores por defecto y acciones disponibles."
    >
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <SettingsCard
          settings={settings}
          onOpenAppConfig={() => setAppConfigDialogOpen(true)}
        />
        <SyncCard />
      </div>

      <Dialog open={appConfigDialogOpen} onOpenChange={setAppConfigDialogOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Configuración de la aplicación</DialogTitle>
            <DialogDescription>
              Ajusta las integraciones y valores por defecto globales.
            </DialogDescription>
          </DialogHeader>
          {appConfigForm ? (
            <ScrollArea className="h-[70vh] pr-4">
              <div className="flex flex-col gap-6">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="qbittorrent_url">URL de qBittorrent</Label>
                    <Input
                      id="qbittorrent_url"
                      value={appConfigForm.qbittorrent_url ?? ""}
                      onChange={(event) =>
                        setAppConfigForm((prev) =>
                          prev
                            ? { ...prev, qbittorrent_url: event.target.value }
                            : prev
                        )
                      }
                      placeholder="http://localhost:8080"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="qbittorrent_username">Usuario</Label>
                    <Input
                      id="qbittorrent_username"
                      value={appConfigForm.qbittorrent_username ?? ""}
                      onChange={(event) =>
                        setAppConfigForm((prev) =>
                          prev
                            ? { ...prev, qbittorrent_username: event.target.value }
                            : prev
                        )
                      }
                      placeholder="admin"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="qbittorrent_password">Contraseña</Label>
                    <Input
                      id="qbittorrent_password"
                      type="password"
                      value={appConfigForm.qbittorrent_password ?? ""}
                      onChange={(event) =>
                        setAppConfigForm((prev) =>
                          prev
                            ? { ...prev, qbittorrent_password: event.target.value }
                            : prev
                        )
                      }
                      placeholder="••••••••"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="qbittorrent_category">Categoría</Label>
                    <Input
                      id="qbittorrent_category"
                      value={appConfigForm.qbittorrent_category ?? ""}
                      onChange={(event) =>
                        setAppConfigForm((prev) =>
                          prev
                            ? { ...prev, qbittorrent_category: event.target.value }
                            : prev
                        )
                      }
                      placeholder="anime"
                    />
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="flex items-center justify-between gap-2 rounded-md border p-3">
                    <div className="flex flex-col">
                      <Label>Activar qBittorrent</Label>
                      <span className="text-muted-foreground text-xs">
                        Requiere credenciales válidas para conectarse.
                      </span>
                    </div>
                    <Checkbox
                      checked={appConfigForm.qbittorrent_enabled}
                      onCheckedChange={(value) =>
                        setAppConfigForm((prev) =>
                          prev ? { ...prev, qbittorrent_enabled: Boolean(value) } : prev
                        )
                      }
                    />
                  </div>
                  <div className="flex items-center justify-between gap-2 rounded-md border p-3">
                    <div className="flex flex-col">
                      <Label>Agregar torrents automáticamente</Label>
                      <span className="text-muted-foreground text-xs">
                        En cola los hallazgos en qBittorrent.
                      </span>
                    </div>
                    <Checkbox
                      checked={appConfigForm.auto_add_to_qbittorrent}
                      onCheckedChange={(value) =>
                        setAppConfigForm((prev) =>
                          prev ? { ...prev, auto_add_to_qbittorrent: Boolean(value) } : prev
                        )
                      }
                    />
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="default_save_path">Ruta por defecto</Label>
                    <Input
                      id="default_save_path"
                      value={appConfigForm.default_save_path ?? ""}
                      onChange={(event) =>
                        setAppConfigForm((prev) =>
                          prev ? { ...prev, default_save_path: event.target.value } : prev
                        )
                      }
                      placeholder="/descargas/anime"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="default_search_query_template">Template de búsqueda</Label>
                    <Input
                      id="default_search_query_template"
                      value={appConfigForm.default_search_query_template ?? ""}
                      onChange={(event) =>
                        setAppConfigForm((prev) =>
                          prev
                            ? {
                                ...prev,
                                default_search_query_template: event.target.value,
                              }
                            : prev
                        )
                      }
                      placeholder="{anime.title}"
                    />
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="tvdb_api_key">TVDB API Key</Label>
                    <Input
                      id="tvdb_api_key"
                      value={appConfigForm.tvdb_api_key ?? ""}
                      onChange={(event) =>
                        setAppConfigForm((prev) =>
                          prev ? { ...prev, tvdb_api_key: event.target.value } : prev
                        )
                      }
                      placeholder="API Key"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="tmdb_api_key">TMDB API Key</Label>
                    <Input
                      id="tmdb_api_key"
                      value={appConfigForm.tmdb_api_key ?? ""}
                      onChange={(event) =>
                        setAppConfigForm((prev) =>
                          prev ? { ...prev, tmdb_api_key: event.target.value } : prev
                        )
                      }
                      placeholder="API Key"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <Label>Mapeos de rutas</Label>
                  <div className="flex flex-col gap-2">
                    {(appConfigForm.path_mappings ?? []).map((mapping, index) => (
                      <div key={`${mapping.from}-${index}`} className="grid gap-2 md:grid-cols-2">
                        <Input
                          value={mapping.from}
                          onChange={(event) =>
                            setAppConfigForm((prev) => {
                              if (!prev) return prev
                              const nextMappings = [...(prev.path_mappings ?? [])]
                              nextMappings[index] = {
                                ...nextMappings[index],
                                from: event.target.value,
                              }
                              return { ...prev, path_mappings: nextMappings }
                            })
                          }
                          placeholder="/ruta/local"
                        />
                        <Input
                          value={mapping.to}
                          onChange={(event) =>
                            setAppConfigForm((prev) => {
                              if (!prev) return prev
                              const nextMappings = [...(prev.path_mappings ?? [])]
                              nextMappings[index] = {
                                ...nextMappings[index],
                                to: event.target.value,
                              }
                              return { ...prev, path_mappings: nextMappings }
                            })
                          }
                          placeholder="Z:\ruta\remota"
                        />
                      </div>
                    ))}
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setAppConfigForm((prev) =>
                          prev
                            ? {
                                ...prev,
                                path_mappings: [
                                  ...(prev.path_mappings ?? []),
                                  { from: "", to: "" },
                                ],
                              }
                            : prev
                        )
                      }
                    >
                      Agregar mapeo
                    </Button>
                  </div>
                </div>
              </div>
            </ScrollArea>
          ) : (
            <Skeleton className="h-48 w-full" />
          )}
          <div className="flex justify-between border-t pt-4">
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={handleTestConnection}
                disabled={testingConnection}
              >
                {testingConnection ? <Loader2 className="size-4 animate-spin" /> : null}
                Probar conexión a qBittorrent
              </Button>
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={() => setAppConfigDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="button" onClick={handleSaveAppConfig}>
                Guardar configuración
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </PageShell>
  )
}



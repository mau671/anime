"use client"

import * as React from "react"

import { PageShell } from "@/components/page-shell"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
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

function SettingsPageContent({ settings, appConfig }: {
  settings?: SettingsEnvelope[]
  appConfig?: AppConfig
}) {
  const [template, setTemplate] = React.useState("")
  const [resolution, setResolution] = React.useState("")
  const [subgroup, setSubgroup] = React.useState("")
  const [lastSavedAt, setLastSavedAt] = React.useState<string | undefined>(undefined)
  const [isSavingDefaults, setIsSavingDefaults] = React.useState(false)

  const [configForm, setConfigForm] = React.useState<AppConfig | undefined>(appConfig)
  const [testingConnection, setTestingConnection] = React.useState(false)

  const globalSettings = settings?.find((s) => s.settings.anilist_id === GLOBAL_SETTINGS_ID)
  const defaults = globalSettings?.settings
  const { data: latestGlobalSettings } = useGlobalSettings()

  React.useEffect(() => {
    const source = latestGlobalSettings?.settings ?? defaults
    if (!source) return

    setTemplate(source.save_path_template ?? "")
    setResolution(source.preferred_resolution ?? "")
    setSubgroup(source.preferred_subgroup ?? "")
    setLastSavedAt(source.updated_at ?? source.created_at ?? undefined)
  }, [defaults, latestGlobalSettings])

  React.useEffect(() => {
    setConfigForm(appConfig)
  }, [appConfig])

  const handleSaveDefaults = async () => {
    try {
      setIsSavingDefaults(true)
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
      setIsSavingDefaults(false)
    }
  }

  const handleSaveAppConfig = async () => {
    if (!configForm) return

    try {
      const { path_mappings, ...rest } = configForm
      await updateAppConfig({
        ...rest,
        path_mappings,
      })
      toast.success("Configuración de la aplicación actualizada")
    } catch (error) {
      console.error(error)
      toast.error("No se pudo actualizar la configuración de la aplicación")
    }
  }

  const handleTestConnection = async () => {
    try {
      setTestingConnection(true)
      await testQbittorrentConnection()
      toast.success("Conexión a qBittorrent exitosa")
    } catch (error) {
      console.error(error)
      toast.error("No se pudo conectar con qBittorrent")
    } finally {
      setTestingConnection(false)
    }
  }

  const addMapping = () => {
    setConfigForm((prev) =>
      prev
        ? {
            ...prev,
            path_mappings: [...(prev.path_mappings ?? []), { from: "", to: "" }],
          }
        : prev
    )
  }

  const updateMapping = (index: number, field: "from" | "to", value: string) => {
    setConfigForm((prev) => {
      if (!prev) return prev
      const nextMappings = [...(prev.path_mappings ?? [])]
      nextMappings[index] = {
        ...nextMappings[index],
        [field]: value,
      }
      return { ...prev, path_mappings: nextMappings }
    })
  }

  const removeMapping = (index: number) => {
    setConfigForm((prev) => {
      if (!prev) return prev
      const nextMappings = [...(prev.path_mappings ?? [])]
      nextMappings.splice(index, 1)
      return { ...prev, path_mappings: nextMappings }
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Configuración general</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-8">
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div>
              <h3 className="text-sm font-medium leading-none">Template de ruta</h3>
              <p className="text-muted-foreground text-sm">
                Define un template con variables para generar rutas automáticamente.
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
            <ScrollArea className="h-48 rounded-md border">
              <div className="space-y-2 p-3">
                {AVAILABLE_VARIABLES.map((variable) => (
                  <div key={variable.key} className="flex items-start gap-3">
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
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label>Resolución por defecto</Label>
              <Input
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                placeholder="1080p"
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label>Fansub por defecto</Label>
              <Input
                value={subgroup}
                onChange={(e) => setSubgroup(e.target.value)}
                placeholder="Fansub"
              />
            </div>
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
            <Button onClick={handleSaveDefaults} disabled={isSavingDefaults}>
              {isSavingDefaults && <Loader2 className="size-4 animate-spin" />}
              Guardar valores por defecto
            </Button>
          </div>
        </div>

        <Separator />

        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-medium leading-none">Integraciones y descargas</h3>
            <p className="text-muted-foreground text-sm">
              Configura qBittorrent, API keys y mapeos de rutas utilizados por el servicio.
            </p>
          </div>

          {configForm ? (
            <div className="flex flex-col gap-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="flex flex-col gap-2">
                  <Label htmlFor="qbittorrent_url">URL de qBittorrent</Label>
                  <Input
                    id="qbittorrent_url"
                    value={configForm.qbittorrent_url ?? ""}
                    onChange={(event) =>
                      setConfigForm((prev) =>
                        prev ? { ...prev, qbittorrent_url: event.target.value } : prev
                      )
                    }
                    placeholder="http://localhost:8080"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="qbittorrent_username">Usuario</Label>
                  <Input
                    id="qbittorrent_username"
                    value={configForm.qbittorrent_username ?? ""}
                    onChange={(event) =>
                      setConfigForm((prev) =>
                        prev ? { ...prev, qbittorrent_username: event.target.value } : prev
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
                    value={configForm.qbittorrent_password ?? ""}
                    onChange={(event) =>
                      setConfigForm((prev) =>
                        prev ? { ...prev, qbittorrent_password: event.target.value } : prev
                      )
                    }
                    placeholder="••••••••"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="qbittorrent_category">Categoría</Label>
                  <Input
                    id="qbittorrent_category"
                    value={configForm.qbittorrent_category ?? ""}
                    onChange={(event) =>
                      setConfigForm((prev) =>
                        prev ? { ...prev, qbittorrent_category: event.target.value } : prev
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
                    checked={configForm.qbittorrent_enabled}
                    onCheckedChange={(value) =>
                      setConfigForm((prev) =>
                        prev ? { ...prev, qbittorrent_enabled: Boolean(value) } : prev
                      )
                    }
                  />
                </div>
                <div className="flex items-center justify-between gap-2 rounded-md border p-3">
                  <div className="flex flex-col">
                    <Label>Agregar torrents automáticamente</Label>
                    <span className="text-muted-foreground text-xs">
                      Envía los hallazgos directamente a qBittorrent.
                    </span>
                  </div>
                  <Checkbox
                    checked={configForm.auto_add_to_qbittorrent}
                    onCheckedChange={(value) =>
                      setConfigForm((prev) =>
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
                    value={configForm.default_save_path ?? ""}
                    onChange={(event) =>
                      setConfigForm((prev) =>
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
                    value={configForm.default_search_query_template ?? ""}
                    onChange={(event) =>
                      setConfigForm((prev) =>
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
                    value={configForm.tvdb_api_key ?? ""}
                    onChange={(event) =>
                      setConfigForm((prev) =>
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
                    value={configForm.tmdb_api_key ?? ""}
                    onChange={(event) =>
                      setConfigForm((prev) =>
                        prev ? { ...prev, tmdb_api_key: event.target.value } : prev
                      )
                    }
                    placeholder="API Key"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-3">
                <Label>Mapeos de rutas</Label>
                <div className="flex flex-col gap-2">
                  {(configForm.path_mappings ?? []).map((mapping, index) => (
                    <div key={`${mapping.from}-${index}`} className="grid gap-2 md:grid-cols-3">
                      <Input
                        value={mapping.from}
                        onChange={(event) => updateMapping(index, "from", event.target.value)}
                        placeholder="/ruta/local"
                      />
                      <Input
                        value={mapping.to}
                        onChange={(event) => updateMapping(index, "to", event.target.value)}
                        placeholder="Z:\\ruta\remota"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => removeMapping(index)}
                      >
                        Quitar
                      </Button>
                    </div>
                  ))}
                  <Button type="button" variant="outline" size="sm" onClick={addMapping}>
                    Agregar mapeo
                  </Button>
                </div>
              </div>

              <div className="flex justify-between border-t pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleTestConnection}
                  disabled={testingConnection}
                >
                  {testingConnection ? <Loader2 className="size-4 animate-spin" /> : null}
                  Probar conexión a qBittorrent
                </Button>
                <Button type="button" onClick={handleSaveAppConfig}>
                  Guardar configuración
                </Button>
              </div>
            </div>
          ) : (
            <Skeleton className="h-48 w-full" />
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function SettingsPage() {
  const { data: settings } = useSettings()
  const { data: appConfig } = useAppConfig()

  return (
    <PageShell
      title="Ajustes"
      description="Consulta los valores por defecto y configuraciones de la aplicación."
    >
      <SettingsPageContent settings={settings} appConfig={appConfig} />
    </PageShell>
  )
}



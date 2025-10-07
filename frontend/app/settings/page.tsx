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
import { useAppConfig, updateAppConfig, testQbittorrentConnection } from "@/lib/api-hooks"
import type { AppConfig } from "@/lib/api-types"
import { AVAILABLE_VARIABLES, TEMPLATE_EXAMPLES } from "@/lib/path-template"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"

function SettingsPageContent({ appConfig }: { appConfig?: AppConfig }) {
  const [configForm, setConfigForm] = React.useState<AppConfig | undefined>(appConfig)
  const [testingConnection, setTestingConnection] = React.useState(false)
  const [isSaving, setIsSaving] = React.useState(false)

  React.useEffect(() => {
    setConfigForm(appConfig)
  }, [appConfig])

  const handleSaveAppConfig = async () => {
    if (!configForm) return

    try {
      setIsSaving(true)
      const { path_mappings, ...rest } = configForm
      await updateAppConfig({
        ...rest,
        path_mappings,
      })
      toast.success("Configuración actualizada")
    } catch (error) {
      console.error(error)
      toast.error("No se pudo actualizar la configuración")
    } finally {
      setIsSaving(false)
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

  const lastUpdated = configForm?.updated_at ?? configForm?.created_at

  return (
      <Card>
        <CardHeader>
        <CardTitle className="text-lg font-semibold">Configuración</CardTitle>
        </CardHeader>
      <CardContent className="flex flex-col gap-8">
        {configForm ? (
          <div className="flex flex-col gap-8">
            <div className="grid gap-6 md:grid-cols-2">
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

            <Separator />

            <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div>
                  <h3 className="text-sm font-medium leading-none">Plantilla de guardado por defecto</h3>
              <p className="text-muted-foreground text-sm">
                    Define el directorio base para guardar torrents cuando un anime no lo especifica.
              </p>
            </div>
            <Textarea
                  value={configForm.default_save_path_template ?? ""}
                  onChange={(event) =>
                    setConfigForm((prev) =>
                      prev ? { ...prev, default_save_path_template: event.target.value } : prev
                    )
                  }
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
                      onClick={() =>
                        setConfigForm((prev) =>
                          prev ? { ...prev, default_save_path_template: example } : prev
                        )
                      }
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
                  <Label>Ruta por defecto</Label>
                  <Input
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
                  <Label>Plantilla de búsqueda</Label>
                  <Input
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
                    placeholder="{anime.title.romaji}"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <Label>Resolución preferida</Label>
                  <Input
                    value={configForm.default_preferred_resolution ?? ""}
                    onChange={(event) =>
                      setConfigForm((prev) =>
                        prev
                          ? { ...prev, default_preferred_resolution: event.target.value }
                          : prev
                      )
                    }
                    placeholder="1080p"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <Label>Fansub preferido</Label>
                  <Input
                    value={configForm.default_preferred_subgroup ?? ""}
                    onChange={(event) =>
                      setConfigForm((prev) =>
                        prev
                          ? { ...prev, default_preferred_subgroup: event.target.value }
                          : prev
                      )
                    }
                    placeholder="Fansub"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between rounded-md border p-3">
                <div className="flex flex-col">
                  <Label>Usar sinónimos para construir la búsqueda</Label>
                  <span className="text-muted-foreground text-xs">
                    Genera consultas adicionales usando los títulos y sinónimos del anime.
                  </span>
                </div>
                <Checkbox
                  checked={configForm.default_auto_query_from_synonyms}
                  onCheckedChange={(value) =>
                    setConfigForm((prev) =>
                      prev
                        ? { ...prev, default_auto_query_from_synonyms: Boolean(value) }
                        : prev
                    )
                  }
                />
              </div>
            </div>

            <Separator />

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
                <Label>Plantilla de guardado en qBittorrent</Label>
                <Textarea
                  value={configForm.qbittorrent_save_template ?? ""}
                  onChange={(event) =>
                    setConfigForm((prev) =>
                      prev ? { ...prev, qbittorrent_save_template: event.target.value } : prev
                    )
                  }
                  rows={2}
                  className="font-mono text-xs"
                  placeholder="Opcional"
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label>Plantilla de torrent para qBittorrent</Label>
                <Textarea
                  value={configForm.qbittorrent_torrent_template ?? ""}
                  onChange={(event) =>
                    setConfigForm((prev) =>
                      prev ? { ...prev, qbittorrent_torrent_template: event.target.value } : prev
                    )
                  }
                  rows={2}
                  className="font-mono text-xs"
                  placeholder="Opcional"
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="flex flex-col gap-3">
                <Label>Mapeos de rutas</Label>
                <div className="flex flex-col gap-2">
                  {(configForm.path_mappings ?? []).map((mapping, index) => (
                    <div key={`${mapping.from}-${index}`} className="grid gap-2 md:grid-cols-[1fr_1fr_auto]">
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
              <div className="flex flex-col gap-2">
                <Label>Estado</Label>
                <div className="text-sm text-muted-foreground">
                  {lastUpdated
                    ? `Última actualización: ${new Intl.DateTimeFormat("es", {
                        dateStyle: "short",
                        timeStyle: "short",
                      }).format(new Date(lastUpdated))}`
                    : "Sin registros recientes"}
                </div>
              </div>
        </div>

            <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-4 text-sm text-muted-foreground">
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleTestConnection}
                  disabled={testingConnection}
                >
                  {testingConnection ? <Loader2 className="size-4 animate-spin" /> : null}
                  Probar conexión a qBittorrent
                </Button>
                <Button type="button" onClick={handleSaveAppConfig} disabled={isSaving}>
                  {isSaving ? <Loader2 className="size-4 animate-spin" /> : null}
                  Guardar configuración
          </Button>
        </div>
            </div>
          </div>
        ) : (
          <Skeleton className="h-48 w-full" />
        )}
      </CardContent>
    </Card>
  )
}

export default function SettingsPage() {
  const { data: appConfig } = useAppConfig()

  return (
    <PageShell
      title="Ajustes"
      description="Consulta los valores por defecto y configuraciones de la aplicación."
    >
      <SettingsPageContent appConfig={appConfig} />
    </PageShell>
  )
}



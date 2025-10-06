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
import { useSettings, updateAnimeSettings } from "@/lib/api-hooks"
import type { SettingsEnvelope } from "@/lib/api-types"
import { AVAILABLE_VARIABLES, TEMPLATE_EXAMPLES } from "@/lib/path-template"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"

type GlobalSetting = {
  title: string
  description: string
  placeholder?: string
  key: keyof SettingsEnvelope["settings"]
}

const metadataFields: GlobalSetting[] = [
  {
    title: "Resolución por defecto",
    description: "Aplica cuando no se configure una resolución específica.",
    key: "preferred_resolution",
  },
  {
    title: "Fansub por defecto",
    description: "Se utilizará como preferencia inicial para los nuevos animes.",
    key: "preferred_subgroup",
  },
]

function SettingsCard({ settings }: { settings?: SettingsEnvelope[] }) {
  // Use anilist_id = 0 for global settings
  const GLOBAL_SETTINGS_ID = 0
  const globalSettings = settings?.find(s => s.settings.anilist_id === GLOBAL_SETTINGS_ID)
  const defaults = globalSettings?.settings
  
  const [season, setSeason] = React.useState<string | undefined>(undefined)
  const [showVariables, setShowVariables] = React.useState(false)
  const [template, setTemplate] = React.useState("")
  const [resolution, setResolution] = React.useState("")
  const [subgroup, setSubgroup] = React.useState("")
  const [isSaving, setIsSaving] = React.useState(false)

  React.useEffect(() => {
    if (defaults) {
      setTemplate(defaults.save_path_template ?? "")
      setResolution(defaults.preferred_resolution ?? "")
      setSubgroup(defaults.preferred_subgroup ?? "")
    }
  }, [defaults])

  const handleSave = async () => {
    try {
      setIsSaving(true)
      // Always use ID 0 for global settings
      await updateAnimeSettings(GLOBAL_SETTINGS_ID, {
        save_path_template: template || null,
        preferred_resolution: resolution || null,
        preferred_subgroup: subgroup || null,
      })
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

          <div className="flex flex-col gap-2">
            <div>
              <h3 className="text-sm font-medium leading-none">Temporada por defecto</h3>
              <p className="text-muted-foreground text-sm">
                Selecciona la temporada que se usará para sincronizaciones sin datos específicos.
              </p>
            </div>
            <Select value={season} onValueChange={setSeason}>
              <SelectTrigger className="w-full justify-between">
                <SelectValue placeholder="Sin temporada" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="WINTER">Invierno</SelectItem>
                <SelectItem value="SPRING">Primavera</SelectItem>
                <SelectItem value="SUMMER">Verano</SelectItem>
                <SelectItem value="FALL">Otoño</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex justify-end pt-4 border-t">
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving && <Loader2 className="size-4 animate-spin" />}
              Guardar cambios
            </Button>
          </div>
        </CardContent>
      </Card>

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

  return (
    <PageShell
      title="Ajustes"
      description="Consulta los valores por defecto y acciones disponibles."
    >
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <SettingsCard settings={settings} />
        <SyncCard />
      </div>
    </PageShell>
  )
}



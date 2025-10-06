"use client"

import * as React from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Loader2 } from "lucide-react"
import { z } from "zod"

import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { toast } from "sonner"
import type { AnimeEnvelope, SettingsEnvelope } from "@/lib/api-types"
import {
  deleteAnimeSettings,
  updateAnimeSettings,
  useSettings,
  useAnimeSettings,
} from "@/lib/api-hooks"
import { processPathTemplate } from "@/lib/path-template"

const formSchema = z.object({
  enabled: z.boolean(),
  save_path: z.string().trim().optional().nullable(),
  use_global_template: z.boolean().optional().default(false),
  search_query: z.string().trim().optional().nullable(),
  includes: z.string().optional(),
  excludes: z.string().optional(),
  preferred_resolution: z
    .string()
    .trim()
    .optional()
    .nullable()
    .refine((value) => !value || /^(480p|720p|1080p|2160p|4K)$/i.test(value), {
      message: "Resolución no válida",
    }),
  preferred_subgroup: z.string().trim().optional().nullable(),
  auto_query_from_synonyms: z.boolean(),
  tvdb_id: z.string().optional(),
  tvdb_season: z.string().optional(),
  tmdb_id: z.string().optional(),
  tmdb_season: z.string().optional(),
})

type FormValues = z.infer<typeof formSchema>

type Props = {
  anime: AnimeEnvelope
  settings?: SettingsEnvelope["settings"]
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AnimeConfigDialog({ anime, settings, open, onOpenChange }: Props) {
  const [isDeleting, setIsDeleting] = React.useState(false)
  const anilistId = anime.anime.anilist_id ?? anime.anime.anilistId ?? 0
  const { data: globalSettings } = useSettings()
  const { data: envelope } = useAnimeSettings(open ? anilistId : null)
  const [previewPath, setPreviewPath] = React.useState<string>("")

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      enabled: settings?.enabled ?? false,
      save_path: settings?.save_path ?? "",
      use_global_template: !settings?.save_path,
      search_query: settings?.search_query ?? "",
      includes: settings?.includes?.join("\n") ?? "",
      excludes: settings?.excludes?.join("\n") ?? "",
      preferred_resolution: settings?.preferred_resolution ?? "",
      preferred_subgroup: settings?.preferred_subgroup ?? "",
      auto_query_from_synonyms: settings?.auto_query_from_synonyms ?? false,
      tvdb_id: settings?.tvdb_id?.toString() ?? "",
      tvdb_season: settings?.tvdb_season?.toString() ?? "",
      tmdb_id: settings?.tmdb_id?.toString() ?? "",
      tmdb_season: settings?.tmdb_season?.toString() ?? "",
    },
  })

  React.useEffect(() => {
    form.reset({
      enabled: settings?.enabled ?? false,
      save_path: settings?.save_path ?? "",
      use_global_template: !settings?.save_path,
      search_query: settings?.search_query ?? "",
      includes: settings?.includes?.join("\n") ?? "",
      excludes: settings?.excludes?.join("\n") ?? "",
      preferred_resolution: settings?.preferred_resolution ?? "",
      preferred_subgroup: settings?.preferred_subgroup ?? "",
      auto_query_from_synonyms: settings?.auto_query_from_synonyms ?? false,
      tvdb_id: settings?.tvdb_id?.toString() ?? "",
      tvdb_season: settings?.tvdb_season?.toString() ?? "",
      tmdb_id: settings?.tmdb_id?.toString() ?? "",
      tmdb_season: settings?.tmdb_season?.toString() ?? "",
    })
  }, [settings, form])

  // Calculate preview path when relevant values change
  React.useEffect(() => {
    const template = globalSettings?.[0]?.settings?.save_path_template
    if (!template || !envelope) {
      setPreviewPath("")
      return
    }

    // Create a temporary envelope with current form values
    const tvdbId = form.watch("tvdb_id")
    const tvdbSeason = form.watch("tvdb_season")
    const tmdbId = form.watch("tmdb_id")
    const tmdbSeason = form.watch("tmdb_season")

    const tempEnvelope: SettingsEnvelope = {
      ...envelope,
      settings: {
        ...envelope.settings,
        tvdb_id: tvdbId ? parseInt(tvdbId, 10) : null,
        tvdb_season: tvdbSeason ? parseInt(tvdbSeason, 10) : null,
        tmdb_id: tmdbId ? parseInt(tmdbId, 10) : null,
        tmdb_season: tmdbSeason ? parseInt(tmdbSeason, 10) : null,
      },
    }

    try {
      const result = processPathTemplate(template, tempEnvelope)
      setPreviewPath(result)
    } catch (error) {
      console.error("Error processing template:", error)
      setPreviewPath("")
    }
  }, [
    envelope,
    globalSettings,
    form.watch("tvdb_id"),
    form.watch("tvdb_season"),
    form.watch("tmdb_id"),
    form.watch("tmdb_season"),
    form,
  ])

  const onSubmit = form.handleSubmit(async (values) => {
    const parseList = (value?: string) =>
      value
        ?.split("\n")
        .map((item) => item.trim())
        .filter(Boolean)

    const includesList = parseList(values.includes)
    const excludesList = parseList(values.excludes)
    
    const savePathValue = values.use_global_template ? null : values.save_path || null

    const parseNumber = (value?: string) => {
      if (!value || value.trim() === "") return null
      const parsed = parseInt(value, 10)
      return isNaN(parsed) ? null : parsed
    }

    try {
      await updateAnimeSettings(anime.anime.anilist_id ?? 0, {
        enabled: values.enabled,
        save_path: savePathValue,
        search_query: values.search_query || null,
        includes: includesList ?? [],
        excludes: excludesList ?? [],
        preferred_resolution: values.preferred_resolution || null,
        preferred_subgroup: values.preferred_subgroup || null,
        auto_query_from_synonyms: values.auto_query_from_synonyms,
        tvdb_id: parseNumber(values.tvdb_id),
        tvdb_season: parseNumber(values.tvdb_season),
        tmdb_id: parseNumber(values.tmdb_id),
        tmdb_season: parseNumber(values.tmdb_season),
      })
      toast.success("Ajustes actualizados")
      onOpenChange(false)
    } catch (error) {
      console.error(error)
      toast.error("No se pudieron guardar los cambios")
    }
  })

  const handleDelete = async () => {
    const anilistId = anime.anime.anilist_id ?? 0
    if (!anilistId) return

    try {
      setIsDeleting(true)
      await deleteAnimeSettings(anilistId)
      toast.success("Ajustes eliminados")
      onOpenChange(false)
    } catch (error) {
      console.error(error)
      toast.error("Ocurrió un error al eliminar los ajustes")
    } finally {
      setIsDeleting(false)
    }
  }

  const title =
    anime.anime.title?.english ?? anime.anime.title?.romaji ?? "Sin título"

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            Configura los parámetros de búsqueda y descarga para este anime.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form className="flex flex-col gap-6" onSubmit={onSubmit}>
            <ScrollArea className="h-[60vh] pr-4">
              <div className="flex flex-col gap-6">
                <div className="flex items-center justify-between gap-4">
              <Label className="text-sm font-medium">Monitoreo activo</Label>
              <FormField
                control={form.control}
                name="enabled"
                render={({ field }) => (
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={field.value}
                      onCheckedChange={(value) => field.onChange(Boolean(value))}
                    />
                    <span className="text-sm text-muted-foreground">
                      Buscar y descargar episodios automáticamente
                    </span>
                  </div>
                )}
              />
            </div>

            <Separator />

            <div className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="use_global_template"
                render={({ field }) => (
                  <FormItem className="col-span-full flex items-start justify-between gap-4 rounded-md border p-3">
                    <div className="flex flex-col gap-1">
                      <FormLabel>Usar plantilla global de rutas</FormLabel>
                      <FormDescription>
                        Cuando está activado, la ruta se generará automáticamente con la plantilla definida en los ajustes globales.
                      </FormDescription>
                    </div>
                    <Checkbox
                      checked={field.value}
                      onCheckedChange={(value) => field.onChange(Boolean(value))}
                    />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="save_path"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Ruta de guardado</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="/descargas/anime"
                        value={field.value ?? ""}
                        onChange={field.onChange}
                        onBlur={field.onBlur}
                        name={field.name}
                        ref={field.ref}
                        disabled={form.watch("use_global_template")}
                      />
                    </FormControl>
                    <FormDescription>
                      Carpeta donde se guardarán los archivos descargados. Se deshabilita cuando se usa la plantilla global.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="search_query"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Consulta personalizada</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Nombre del anime"
                        value={field.value ?? ""}
                        onChange={field.onChange}
                        onBlur={field.onBlur}
                        name={field.name}
                        ref={field.ref}
                      />
                    </FormControl>
                    <FormDescription>
                      Se usará para buscar torrents si está presente.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {previewPath && (
              <div className="rounded-md bg-muted p-3">
                <h4 className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">
                  Vista previa del path (desde template)
                </h4>
                <code className="text-xs break-all block font-mono">
                  {previewPath}
                </code>
              </div>
            )}

            <div className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="preferred_resolution"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Resolución preferida</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="1080p"
                        value={field.value ?? ""}
                        onChange={field.onChange}
                        onBlur={field.onBlur}
                        name={field.name}
                        ref={field.ref}
                      />
                    </FormControl>
                    <FormDescription>
                      Valores soportados: 480p, 720p, 1080p, 2160p o 4K.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="preferred_subgroup"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Fansub preferido</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Fansub"
                        value={field.value ?? ""}
                        onChange={field.onChange}
                        onBlur={field.onBlur}
                        name={field.name}
                        ref={field.ref}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="includes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Términos incluidos</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Una palabra por línea"
                        value={field.value ?? ""}
                        onChange={field.onChange}
                        onBlur={field.onBlur}
                        name={field.name}
                        ref={field.ref}
                      />
                    </FormControl>
                    <FormDescription>
                      Todas las palabras listadas deben estar presentes en el título.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="excludes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Términos excluidos</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Una palabra por línea"
                        value={field.value ?? ""}
                        onChange={field.onChange}
                        onBlur={field.onBlur}
                        name={field.name}
                        ref={field.ref}
                      />
                    </FormControl>
                    <FormDescription>
                      Si se encuentra alguna palabra listada, el torrent será descartado.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="auto_query_from_synonyms"
              render={({ field }) => (
                <div className="flex items-center gap-2 rounded-md border p-3">
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={(value) => field.onChange(Boolean(value))}
                  />
                  <div className="flex flex-col gap-1">
                    <FormLabel>Sinónimos automáticos</FormLabel>
                    <FormDescription>
                      Genera consultas extra usando los sinónimos del anime.
                    </FormDescription>
                  </div>
                </div>
              )}
            />

            <Separator />

            <div className="grid gap-4">
              <div>
                <h3 className="text-sm font-medium mb-1">Metadatos TVDB</h3>
                <p className="text-xs text-muted-foreground mb-3">
                  Configura el ID de TVDB y número de temporada (opcional para películas).
                </p>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="tvdb_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>TVDB ID</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="123456"
                          value={field.value ?? ""}
                          onChange={field.onChange}
                          onBlur={field.onBlur}
                          name={field.name}
                          ref={field.ref}
                        />
                      </FormControl>
                      <FormDescription>
                        ID del anime en TheTVDB.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="tvdb_season"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Temporada TVDB</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="1"
                          value={field.value ?? ""}
                          onChange={field.onChange}
                          onBlur={field.onBlur}
                          name={field.name}
                          ref={field.ref}
                        />
                      </FormControl>
                      <FormDescription>
                        Número de temporada (opcional).
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            <div className="grid gap-4">
              <div>
                <h3 className="text-sm font-medium mb-1">Metadatos TMDB</h3>
                <p className="text-xs text-muted-foreground mb-3">
                  Configura el ID de TMDB y número de temporada (opcional para películas).
                </p>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="tmdb_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>TMDB ID</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="123456"
                          value={field.value ?? ""}
                          onChange={field.onChange}
                          onBlur={field.onBlur}
                          name={field.name}
                          ref={field.ref}
                        />
                      </FormControl>
                      <FormDescription>
                        ID del anime en TheMovieDB.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="tmdb_season"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Temporada TMDB</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="1"
                          value={field.value ?? ""}
                          onChange={field.onChange}
                          onBlur={field.onBlur}
                          name={field.name}
                          ref={field.ref}
                        />
                      </FormControl>
                      <FormDescription>
                        Número de temporada (opcional).
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>
              </div>
            </ScrollArea>

            <DialogFooter>
              {settings ? (
                <Button
                  type="button"
                  variant="destructive"
                  onClick={handleDelete}
                  disabled={isDeleting}
                >
                  {isDeleting ? <Loader2 className="size-4 animate-spin" /> : null}
                  Eliminar ajustes
                </Button>
              ) : null}
              <div className="flex flex-1 justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={form.formState.isSubmitting}>
                  {form.formState.isSubmitting ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : null}
                  Guardar cambios
                </Button>
              </div>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}



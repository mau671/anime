"use client"

import * as React from "react"
import Image from "next/image"
import dynamic from "next/dynamic"
import { Plus } from "lucide-react"
import { toast } from "sonner"

import { PageShell } from "@/components/page-shell"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { addAnime, useAnimes, useSettings } from "@/lib/api-hooks"
import type { AnimeEnvelope, SettingsEnvelope } from "@/lib/api-types"

type FilteredAnime = {
  envelope: AnimeEnvelope
  settings?: SettingsEnvelope["settings"]
}

const AnimeConfigDialog = dynamic(
  () =>
    import("@/components/screens/anime-config-dialog").then(
      (mod) => mod.AnimeConfigDialog
    ),
  { ssr: false }
)

const AnimeDetailsDialog = dynamic(
  () =>
    import("@/components/screens/anime-details-dialog").then(
      (mod) => mod.AnimeDetailsDialog
    ),
  { ssr: false }
)

function AddAnimeDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [anilistId, setAnilistId] = React.useState("")
  const [isSubmitting, setIsSubmitting] = React.useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const id = parseInt(anilistId, 10)
    if (isNaN(id) || id <= 0) {
      toast.error("ID inválido", {
        description: "Por favor ingresa un ID de Anilist válido",
      })
      return
    }

    try {
      setIsSubmitting(true)
      toast.info("Registrando anime...", {
        description: "Obteniendo información de Anilist",
      })

      const result = await addAnime({ anilist_id: id })
      
      toast.success("Anime registrado", {
        description: result.anime.title?.english ?? result.anime.title?.romaji ?? "Anime añadido correctamente",
      })
      
      setAnilistId("")
      onOpenChange(false)
    } catch (error) {
      console.error(error)
      toast.error("Error al registrar anime", {
        description: error instanceof Error ? error.message : "No se pudo registrar el anime",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Registrar nuevo anime</DialogTitle>
          <DialogDescription>
            Ingresa el ID de Anilist del anime que deseas monitorear.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="anilist_id">ID de Anilist</Label>
              <Input
                id="anilist_id"
                type="number"
                placeholder="Ej: 21"
                value={anilistId}
                onChange={(e) => setAnilistId(e.target.value)}
                disabled={isSubmitting}
                min={1}
                required
              />
              <p className="text-xs text-muted-foreground">
                Encuentra el ID en la URL de Anilist: anilist.co/anime/<strong>21</strong>
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Registrando..." : "Registrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function sanitizeDescription(description?: string | null) {
  if (!description) return "Sin descripción"
  return description
    .replace(/<br\s*\/?>(\s*)/gi, " ")
    .replace(/<[^>]+>/g, "")
    .replace(/\s+/g, " ")
    .trim()
}

function resolveCover(anime: AnimeEnvelope["anime"]) {
  if (typeof anime.cover_image === "string") {
    return anime.cover_image
  }
  if (anime.coverImage && typeof anime.coverImage === "object") {
    return (
      (anime.coverImage.extraLarge as string | undefined) ??
      (anime.coverImage.large as string | undefined) ??
      (anime.coverImage.medium as string | undefined) ??
      undefined
    )
  }
  return undefined
}

function AnimeRow({ envelope, settings }: FilteredAnime) {
  const [open, setOpen] = React.useState(false)
  const [detailsOpen, setDetailsOpen] = React.useState(false)
  const anime = envelope.anime
  const title = anime.title?.english ?? anime.title?.romaji ?? "Sin título"
  const cover = resolveCover(anime)
  const description = sanitizeDescription(anime.description)

  return (
    <TableRow
      className="align-top cursor-pointer"
      onDoubleClick={() => {
        if (!open && !detailsOpen) {
          setDetailsOpen(true)
        }
      }}
    >
      <TableCell className="w-[92px] align-top">
        {cover ? (
          <div className="relative aspect-[2/3] overflow-hidden rounded-md border">
            <Image
              src={cover}
              alt={title}
              fill
              className="object-cover"
              sizes="88px"
            />
          </div>
        ) : (
          <div className="bg-muted flex aspect-[2/3] items-center justify-center rounded-md border text-sm text-muted-foreground">
            N/A
          </div>
        )}
      </TableCell>
      <TableCell className="max-w-[220px] align-top pr-4">
        <div className="flex flex-col gap-1">
          <span className="font-semibold leading-tight break-words whitespace-normal">
            {title}
          </span>
          {anime.format ? (
            <span className="text-muted-foreground text-sm">
              {anime.format}
            </span>
          ) : null}
          {anime.season ? (
            <span className="text-muted-foreground text-xs">
              {anime.season} {anime.seasonYear ?? ""}
            </span>
          ) : null}
        </div>
      </TableCell>
      <TableCell className="max-w-[460px] align-top text-muted-foreground text-sm">
        <span
          className="block break-words whitespace-normal"
          style={{
            display: "-webkit-box",
            WebkitLineClamp: 5,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
          title={description}
        >
          {description}
        </span>
      </TableCell>
      <TableCell className="w-[140px] align-top">
        <div className="text-sm font-medium text-foreground">
          {settings?.enabled ? "Activo" : "Inactivo"}
        </div>
      </TableCell>
      <TableCell className="w-[140px] align-top">
        <div className="flex flex-col items-start gap-2">
          <Button
            size="sm"
            variant="outline"
            className="justify-start min-w-[110px]"
            onClick={() => setDetailsOpen(true)}
          >
            Detalles
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="justify-start min-w-[110px]"
            onClick={() => setOpen(true)}
          >
            Configurar
          </Button>
        </div>
        <AnimeConfigDialog
          open={open}
          onOpenChange={setOpen}
          anime={envelope}
          settings={settings}
        />
        <AnimeDetailsDialog
          open={detailsOpen}
          onOpenChange={setDetailsOpen}
          envelope={envelope}
          settings={settings}
        />
      </TableCell>
    </TableRow>
  )
}

function AnimeList({
  animes,
  settings,
}: {
  animes?: AnimeEnvelope[]
  settings?: SettingsEnvelope[]
}) {
  const [query, setQuery] = React.useState("")
  const [addDialogOpen, setAddDialogOpen] = React.useState(false)

  const filtered: FilteredAnime[] = React.useMemo(() => {
    if (!animes) return []
    const settingsById = new Map(
      settings?.map((item) => [item.settings.anilist_id, item.settings]) ?? []
    )
    return animes
      .map((item) => ({
        envelope: item,
        settings: settingsById.get(item.anime.anilist_id ?? item.anime.anilistId ?? 0),
      }))
      .filter((item) => {
        if (!query) return true
        const anime = item.envelope.anime
        const haystack = [
          anime.title?.english,
          anime.title?.romaji,
          anime.title?.native,
          item.settings?.search_query,
        ]
          .filter(Boolean)
          .map((value) => value?.toString().toLowerCase())
          .join("\n")

        return haystack.includes(query.toLowerCase())
      })
  }, [animes, settings, query])

  if (!animes) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Listado de animes</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="gap-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold">Listado de animes</CardTitle>
          <Button onClick={() => setAddDialogOpen(true)} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            Añadir anime
          </Button>
        </div>
        <div className="flex gap-2">
          <Input
            placeholder="Buscar por nombre o consulta"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>
                <span className="sr-only">Imagen</span>
              </TableHead>
              <TableHead>Título</TableHead>
              <TableHead>Descripción</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  No hay animes que coincidan con la búsqueda.
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((item) => (
                <AnimeRow
                  key={
                    item.envelope.anime.anilist_id ??
                    item.envelope.anime.anilistId ??
                    item.envelope.anime.id ??
                    `${item.envelope.anime.title?.romaji ?? "sin-id"}`
                  }
                  envelope={item.envelope}
                  settings={item.settings}
                />
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
      <AddAnimeDialog open={addDialogOpen} onOpenChange={setAddDialogOpen} />
    </Card>
  )
}

export default function AnimesPage() {
  const { data: animes, isLoading: animesLoading } = useAnimes()
  const { data: settings, isLoading: settingsLoading } = useSettings()

  const isLoading = animesLoading || settingsLoading

  return (
    <PageShell
      title="Animes"
      description="Gestiona los animes monitoreados y sus configuraciones."
    >
      <AnimeList animes={isLoading ? undefined : animes} settings={settings} />
    </PageShell>
  )
}



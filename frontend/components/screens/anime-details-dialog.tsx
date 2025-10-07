"use client"

import * as React from "react"
import { Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useDownloadHistory, useQbittorrentHistory } from "@/lib/api-hooks"
import type { AnimeEnvelope, SettingsEnvelope } from "@/lib/api-types"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"

export type AnimeDetailsDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  envelope: AnimeEnvelope
  settings?: SettingsEnvelope["settings"]
}

function DetailRow({ label, value }: { label: string; value?: React.ReactNode }) {
  if (!value || (typeof value === "string" && value.trim().length === 0)) {
    return null
  }

  return (
    <div className="grid gap-1">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className="text-sm leading-relaxed whitespace-pre-line">{value}</span>
    </div>
  )
}

export function AnimeDetailsDialog({
  open,
  onOpenChange,
  envelope,
  settings,
}: AnimeDetailsDialogProps) {
  const anime = envelope.anime
  const anilistId =
    anime.anilist_id ??
    anime.anilistId ??
    (typeof anime.id === "number" ? anime.id : undefined)

  const { data: downloadHistory, isLoading } = useDownloadHistory(anilistId ?? null)
  const { data: qbittorrentHistory, isLoading: qbittorrentLoading } = useQbittorrentHistory(anilistId ?? null)

  const title =
    anime.title?.english ?? anime.title?.romaji ?? anime.title?.native ?? "Sin título"
  const description = anime.description
    ?.replace(/<br\s*\/?>(\s*)/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .trim()
  const siteUrl = typeof anime.site_url === "string" ? anime.site_url : undefined

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <ScrollArea className="h-[60vh] pt-4 pb-0">
          <div className="flex flex-col gap-6">
            <DetailRow label="Descripción" value={description} />
            <div className="grid gap-4 md:grid-cols-2">
              <DetailRow
                label="Géneros"
                value={anime.genres?.length ? anime.genres.join(", ") : undefined}
              />
              <DetailRow label="Estado" value={anime.status} />
              <DetailRow label="Temporada" value={anime.season} />
              <DetailRow label="Año" value={anime.season_year?.toString()} />
              <DetailRow
                label="Puntaje promedio"
                value={anime.average_score?.toString()}
              />
              <DetailRow label="Popularidad" value={anime.popularity?.toString()} />
              <DetailRow
                label="Sinónimos"
                value={anime.synonyms?.length ? anime.synonyms.join(", ") : undefined}
              />
              <DetailRow label="URL Anilist" value={siteUrl} />
            </div>

            <div className="grid gap-4">
              <h3 className="text-base font-semibold">Ajustes actuales</h3>
              {settings ? (
                <div className="grid gap-2 text-sm">
                  <span>Monitoreo: {settings.enabled ? "Activo" : "Inactivo"}</span>
                  <span>Ruta: {settings.save_path ?? "-"}</span>
                  <span>Consulta: {settings.search_query ?? "-"}</span>
                  <span>
                    Resolución preferida: {settings.preferred_resolution ?? "-"}
                  </span>
                  <span>Fansub preferido: {settings.preferred_subgroup ?? "-"}</span>
                  <span>
                    Incluye: {settings.includes?.length ? settings.includes.join(", ") : "-"}
                  </span>
                  <span>
                    Excluye: {settings.excludes?.length ? settings.excludes.join(", ") : "-"}
                  </span>
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">
                  No hay ajustes configurados para este anime.
                </p>
              )}
            </div>

            <Separator />

            <div className="grid gap-3">
              <h3 className="text-base font-semibold">Historial de descargas</h3>
              {isLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" /> Cargando historial...
                </div>
              ) : downloadHistory && downloadHistory.length > 0 ? (
                <ScrollArea className="max-h-[300px]">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[300px]">Título</TableHead>
                        <TableHead className="w-[120px]">Fuente</TableHead>
                        <TableHead className="w-[140px]">Publicado</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {downloadHistory.map((item) => (
                        <TableRow key={item.infohash ?? `${item.link}-${item.title}`}>
                          <TableCell className="font-medium max-w-[300px]">
                            <a
                              href={item.link}
                              target="_blank"
                              rel="noreferrer"
                              className="hover:underline break-words whitespace-normal leading-tight block"
                            >
                              {item.title}
                            </a>
                          </TableCell>
                          <TableCell className="whitespace-nowrap">{item.source ?? "-"}</TableCell>
                          <TableCell className="whitespace-nowrap">
                            {item.published_at
                              ? new Date(item.published_at).toLocaleString("es", {
                                  dateStyle: "short",
                                  timeStyle: "short",
                                })
                              : "-"}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              ) : (
                <p className="text-muted-foreground text-sm">
                  No se registran descargas para este anime.
                </p>
              )}
            </div>

            <Separator />

            <div className="grid gap-3">
              <h3 className="text-base font-semibold">Archivos en qBittorrent</h3>
              {qbittorrentLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" /> Cargando historial de qBittorrent...
                </div>
              ) : qbittorrentHistory && qbittorrentHistory.records.length > 0 ? (
                <ScrollArea className="max-h-[300px]">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[300px]">Título</TableHead>
                        <TableHead className="w-[120px]">Categoría</TableHead>
                        <TableHead className="w-[140px]">Agregado</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {qbittorrentHistory.records.map((item) => (
                        <TableRow key={item.id ?? item.infohash ?? `${item.torrent_path}-${item.title}`}>
                          <TableCell className="font-medium max-w-[300px]">
                            <div className="flex flex-col gap-1">
                              <span className="break-words whitespace-normal leading-tight">
                                {item.title}
                              </span>
                              {item.infohash && (
                                <code className="text-xs text-muted-foreground">
                                  {item.infohash.slice(0, 16)}...
                                </code>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="whitespace-nowrap">
                            {item.category ? (
                              <Badge variant="outline">{item.category}</Badge>
                            ) : (
                              "-"
                            )}
                          </TableCell>
                          <TableCell className="whitespace-nowrap">
                            {item.created_at
                              ? new Date(item.created_at).toLocaleString("es", {
                                  dateStyle: "short",
                                  timeStyle: "short",
                                })
                              : "-"}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              ) : (
                <p className="text-muted-foreground text-sm">
                  No hay archivos de este anime en qBittorrent.
                </p>
              )}
            </div>
          </div>
        </ScrollArea>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}


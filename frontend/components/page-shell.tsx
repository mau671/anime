"use client"

import * as React from "react"

import { ThemeToggle } from "@/components/theme-toggle"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"

type PageShellProps = {
  title: string
  description?: string
  actions?: React.ReactNode
  children: React.ReactNode
}

export function PageShell({
  title,
  description,
  actions,
  children,
}: PageShellProps) {
  return (
    <div className="flex h-full flex-1 flex-col">
      <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mr-2 data-[orientation=vertical]:h-4"
        />
        <div className="flex flex-1 flex-col gap-1">
          <h1 className="text-lg font-semibold leading-none">{title}</h1>
          {description ? (
            <p className="text-muted-foreground text-sm">{description}</p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {actions}
          <ThemeToggle />
        </div>
      </header>
      <div className="flex flex-1 flex-col gap-6 overflow-auto p-6">
        {children}
      </div>
    </div>
  )
}



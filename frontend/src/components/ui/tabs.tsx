import * as React from "react"
import { cn } from "@/lib/utils"

/**
 * Tabs controladas, sem dependências externas.
 *
 * Uso:
 *   <Tabs value={tab} onValueChange={setTab}>
 *     <TabsList>
 *       <TabsTrigger value="a">Aba A</TabsTrigger>
 *       <TabsTrigger value="b">Aba B</TabsTrigger>
 *     </TabsList>
 *     <TabsContent value="a">…</TabsContent>
 *     <TabsContent value="b">…</TabsContent>
 *   </Tabs>
 */

interface TabsContextValue {
  value: string
  onValueChange: (value: string) => void
}

const TabsContext = React.createContext<TabsContextValue | null>(null)

function useTabsContext(component: string): TabsContextValue {
  const ctx = React.useContext(TabsContext)
  if (!ctx) throw new Error(`<${component}> deve ser usado dentro de <Tabs>`)
  return ctx
}

export interface TabsProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "onChange"> {
  value: string
  onValueChange: (value: string) => void
}

function Tabs({ value, onValueChange, className, children, ...props }: TabsProps) {
  const ctx = React.useMemo(() => ({ value, onValueChange }), [value, onValueChange])
  return (
    <TabsContext.Provider value={ctx}>
      <div className={cn("w-full", className)} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  )
}

function TabsList({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      role="tablist"
      className={cn("flex items-center gap-1 overflow-x-auto border-b border-border", className)}
      {...props}
    >
      {children}
    </div>
  )
}

export interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string
}

function TabsTrigger({ value, className, children, ...props }: TabsTriggerProps) {
  const ctx = useTabsContext("TabsTrigger")
  const active = ctx.value === value
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      tabIndex={active ? 0 : -1}
      onClick={() => ctx.onValueChange(value)}
      className={cn(
        "relative -mb-px inline-flex min-h-[40px] items-center gap-2 whitespace-nowrap px-3 py-2 text-sm font-medium transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-50",
        active ? "text-brand" : "text-gray-500 hover:text-gray-900",
        className
      )}
      {...props}
    >
      {children}
      {/* Underline azul animada */}
      <span
        aria-hidden="true"
        className={cn(
          "absolute inset-x-1 bottom-0 h-0.5 origin-left rounded-full bg-brand transition-transform duration-300 ease-out",
          active ? "scale-x-100" : "scale-x-0"
        )}
      />
    </button>
  )
}

export interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string
}

function TabsContent({ value, className, children, ...props }: TabsContentProps) {
  const ctx = useTabsContext("TabsContent")
  if (ctx.value !== value) return null
  return (
    <div role="tabpanel" className={cn("pt-4 animate-fade-in", className)} {...props}>
      {children}
    </div>
  )
}

export { Tabs, TabsList, TabsTrigger, TabsContent }

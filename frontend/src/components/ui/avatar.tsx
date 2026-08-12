import * as React from "react"
import { cn } from "@/lib/utils"

type AvatarSize = "sm" | "md" | "lg" | "xl"

export interface AvatarProps {
  /** URL da foto (ex.: photo_url `/uploads/...`). Null/vazio → iniciais. */
  src?: string | null
  /** Nome completo — usado para as iniciais e para o alt da imagem. */
  name: string
  size?: AvatarSize
  className?: string
}

const sizeClasses: Record<AvatarSize, string> = {
  sm: "h-8 w-8 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-14 w-14 text-lg",
  xl: "h-24 w-24 text-3xl",
}

/** Iniciais: primeira letra do primeiro e do último nome. */
function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return "?"
  const first = parts[0][0] ?? ""
  const last = parts.length > 1 ? parts[parts.length - 1][0] ?? "" : ""
  return (first + last).toUpperCase()
}

const Avatar = React.forwardRef<HTMLDivElement, AvatarProps>(
  ({ src, name, size = "md", className }, ref) => {
    const [failed, setFailed] = React.useState(false)

    // Se a URL mudar (ex.: usuário trocou a foto), tenta carregar de novo.
    React.useEffect(() => {
      setFailed(false)
    }, [src])

    const showImage = Boolean(src) && !failed

    return (
      <div
        ref={ref}
        className={cn(
          "relative inline-flex shrink-0 select-none items-center justify-center overflow-hidden rounded-full bg-brand-100 font-semibold text-brand-700",
          sizeClasses[size],
          className
        )}
      >
        {showImage ? (
          <img
            src={src as string}
            alt={`Foto de ${name}`}
            className="h-full w-full object-cover"
            onError={() => setFailed(true)}
          />
        ) : (
          <span aria-hidden="true">{getInitials(name)}</span>
        )}
      </div>
    )
  }
)
Avatar.displayName = "Avatar"

export { Avatar }

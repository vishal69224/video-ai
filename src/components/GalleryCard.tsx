import { memo, type ButtonHTMLAttributes, type HTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

type GalleryCardProps = {
  children: ReactNode
  className?: string
  active?: boolean
} & (
  | ({ as?: 'div' } & HTMLAttributes<HTMLDivElement>)
  | ({ as: 'button' } & ButtonHTMLAttributes<HTMLButtonElement>)
)

function GalleryCardComponent({
  children,
  className,
  as = 'div',
  active = false,
  ...props
}: GalleryCardProps) {
  const classes = cn(
    'relative overflow-hidden border bg-slate-200 shadow-soft transition-[box-shadow,border-color] duration-300',
    active
      ? 'border-accent shadow-[0_0_0_1px_rgba(15,118,110,0.35),0_8px_24px_rgba(15,118,110,0.18)]'
      : 'border-line/80',
    className,
  )

  if (as === 'button') {
    return (
      <button
        type="button"
        className={classes}
        {...(props as ButtonHTMLAttributes<HTMLButtonElement>)}
      >
        {children}
      </button>
    )
  }

  return (
    <div className={classes} {...(props as HTMLAttributes<HTMLDivElement>)}>
      {children}
    </div>
  )
}

export const GalleryCard = memo(GalleryCardComponent)

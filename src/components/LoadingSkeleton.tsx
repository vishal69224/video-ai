import { cn } from '@/lib/utils'

interface LoadingSkeletonProps {
  className?: string
}

export function LoadingSkeleton({ className }: LoadingSkeletonProps) {
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-2xl bg-line/70',
        'before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_1.4s_infinite] before:bg-gradient-to-r before:from-transparent before:via-white/70 before:to-transparent',
        className,
      )}
    />
  )
}

export function VideoCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface p-3 shadow-soft">
      <LoadingSkeleton className="aspect-video w-full" />
      <div className="mt-4 space-y-3 px-1 pb-1">
        <LoadingSkeleton className="h-4 w-3/4 rounded-lg" />
        <LoadingSkeleton className="h-3 w-1/2 rounded-lg" />
        <div className="flex gap-2 pt-1">
          <LoadingSkeleton className="h-9 flex-1 rounded-xl" />
          <LoadingSkeleton className="h-9 flex-1 rounded-xl" />
        </div>
      </div>
    </div>
  )
}

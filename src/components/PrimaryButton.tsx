import { motion } from 'framer-motion'
import { Button, type ButtonProps } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface PrimaryButtonProps extends ButtonProps {
  motionProps?: boolean
}

export function PrimaryButton({
  className,
  children,
  disabled,
  motionProps = true,
  ...props
}: PrimaryButtonProps) {
  if (!motionProps) {
    return (
      <Button className={cn(className)} disabled={disabled} {...props}>
        {children}
      </Button>
    )
  }

  return (
    <motion.div
      whileHover={disabled ? undefined : { y: -2 }}
      whileTap={disabled ? undefined : { scale: 0.98 }}
      className="inline-flex"
    >
      <Button className={cn('min-w-[10rem]', className)} disabled={disabled} {...props}>
        {children}
      </Button>
    </motion.div>
  )
}

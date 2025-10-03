import { type HTMLAttributes, forwardRef } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated'
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ variant = 'default', className, ...props }, ref) => {
    const baseClasses = 'rounded-2xl border backdrop-blur-xl'
    const variantClasses = {
      default: 'border-slate-400/20 bg-slate-900/70 shadow-lg shadow-slate-900/20 hover:shadow-slate-900/30 hover:border-slate-400/30 transition-all duration-300',
      elevated: 'border-sky-400/30 bg-slate-900/80 shadow-xl shadow-sky-900/30 hover:shadow-sky-900/50 hover:shadow-2xl hover:border-sky-400/50 transition-all duration-300',
    }

    return (
      <div
        ref={ref}
        className={`${baseClasses} ${variantClasses[variant]} ${className || ''}`}
        {...props}
      />
    )
  }
)

Card.displayName = 'Card'

export { Card }
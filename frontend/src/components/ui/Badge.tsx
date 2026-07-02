import { forwardRef, HTMLAttributes } from 'react';

type BadgeVariant = 'normal' | 'watch' | 'warning' | 'emergency' | 'monitoring' | 'default';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  dot?: boolean;
  animateDot?: boolean;
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className = '', variant = 'default', dot = false, animateDot = false, children, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-micro font-bold uppercase tracking-widest transition-colors';
    
    const variants: Record<BadgeVariant, string> = {
      normal: 'border-emerald-500/25 bg-emerald-500/8 text-emerald-400',
      watch: 'border-amber-500/25 bg-amber-500/8 text-amber-400',
      warning: 'border-red-500/25 bg-red-500/8 text-red-400',
      emergency: 'border-slope-accent/30 bg-slope-accent/10 text-slope-accent shadow-tier-emergency',
      monitoring: 'border-zinc-700/40 bg-zinc-800/40 text-zinc-500',
      default: 'border-white/10 bg-white/4 text-white/70',
    };

    const dotColors: Record<BadgeVariant, string> = {
      normal: 'bg-emerald-400',
      watch: 'bg-amber-400',
      warning: 'bg-red-400',
      emergency: 'bg-slope-accent',
      monitoring: 'bg-zinc-500',
      default: 'bg-white/50',
    };

    return (
      <span ref={ref} className={`${baseStyles} ${variants[variant]} ${className}`} {...props}>
        {dot && (
          <span className={`h-1.5 w-1.5 rounded-full ${dotColors[variant]} ${animateDot ? 'animate-pulse' : ''}`} />
        )}
        {children}
      </span>
    );
  }
);
Badge.displayName = 'Badge';

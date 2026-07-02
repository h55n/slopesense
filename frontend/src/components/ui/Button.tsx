'use client';

import { motion, HTMLMotionProps } from 'framer-motion';
import { forwardRef } from 'react';

import { ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'ref' | 'children'> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  children?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant = 'primary', size = 'md', isLoading, children, disabled, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center rounded-full font-bold uppercase tracking-widest transition-all duration-200 focus-ring disabled:opacity-50 disabled:cursor-not-allowed';
    
    const variants: Record<ButtonVariant, string> = {
      primary: 'bg-slope-accent text-slope-bg shadow-glow-lime hover:shadow-glow-lime-strong hover:bg-white',
      secondary: 'border border-white/12 bg-white/4 text-white/70 hover:border-white/25 hover:bg-white/8 hover:text-white',
      ghost: 'text-white/50 hover:text-white hover:bg-white/5',
    };

    const sizes: Record<ButtonSize, string> = {
      sm: 'h-8 px-4 text-micro',
      md: 'h-11 px-6 text-tiny',
      lg: 'h-14 px-8 text-small',
    };

    return (
      <motion.button
        ref={ref}
        whileHover={disabled || isLoading ? {} : { scale: 1.02, y: -1 }}
        whileTap={disabled || isLoading ? {} : { scale: 0.98 }}
        className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading ? (
          <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
        ) : null}
        {children}
      </motion.button>
    );
  }
);
Button.displayName = 'Button';

'use client';

import { motion, HTMLMotionProps } from 'framer-motion';
import { forwardRef } from 'react';

import { ReactNode } from 'react';

export interface CardProps extends Omit<HTMLMotionProps<'div'>, 'ref' | 'children'> {
  hoverable?: boolean;
  children?: ReactNode;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', hoverable = false, children, ...props }, ref) => {
    return (
      <motion.div
        ref={ref}
        whileHover={hoverable ? { y: -2 } : {}}
        className={`glass-panel p-6 ${className}`}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);
Card.displayName = 'Card';

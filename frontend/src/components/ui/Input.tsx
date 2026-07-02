import { forwardRef, InputHTMLAttributes, ReactNode } from 'react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  icon?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', icon, ...props }, ref) => {
    return (
      <div className="relative w-full">
        {icon && (
          <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-white/30">
            {icon}
          </div>
        )}
        <input
          ref={ref}
          className={`w-full rounded-full border border-white/10 bg-white/5 py-3 text-base-sm font-medium text-white placeholder-white/30 outline-none transition-all shadow-inner focus-ring focus:bg-white/10 ${
            icon ? 'pl-10 pr-4' : 'px-4'
          } ${className}`}
          {...props}
        />
      </div>
    );
  }
);
Input.displayName = 'Input';

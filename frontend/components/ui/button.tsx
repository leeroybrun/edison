import { cva, type VariantProps } from "class-variance-authority";
import { clsx } from "clsx";
import * as React from "react";

const buttonStyles = cva(
  "inline-flex items-center justify-center gap-2 rounded-full text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2",
  {
    variants: {
      intent: {
        primary: "bg-accent text-white hover:shadow-md focus-visible:outline-accent",
        outline: "border border-ink/10 text-ink hover:border-accent focus-visible:outline-accent",
        subtle: "bg-ink/5 text-ink hover:bg-ink/10 focus-visible:outline-accent"
      },
      size: {
        sm: "px-3 py-1.5",
        md: "px-4 py-2",
        lg: "px-5 py-3"
      }
    },
    defaultVariants: {
      intent: "primary",
      size: "md"
    }
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonStyles> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, intent, size, ...props }, ref) => (
    <button ref={ref} className={clsx(buttonStyles({ intent, size }), className)} {...props} />
  )
);
Button.displayName = "Button";

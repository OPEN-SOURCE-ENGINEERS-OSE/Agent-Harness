import type { ComponentProps } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { twMerge } from "tailwind-merge";

const button = cva("inline-flex items-center justify-center gap-2 rounded-lg transition-colors disabled:opacity-50", {
  variants: { variant: {
    primary: "bg-[#bbf77a] text-[#172214] hover:bg-[#d4ffa5]",
    ghost: "text-[#c1c9c3] hover:bg-white/10",
  }},
  defaultVariants: { variant: "ghost" },
});

export function Button({ className, variant, ...props }: ComponentProps<"button"> & VariantProps<typeof button>) {
  return <button className={twMerge(button({ variant }), className)} {...props} />;
}
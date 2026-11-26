import type { ComponentProps } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { twMerge } from "tailwind-merge";

const button = cva("inline-flex items-center justify-center gap-2 rounded-lg transition-colors disabled:opacity-50", {
  variants: { variant: {
    primary: "bg-[#F5A800] text-[#14151D] hover:bg-[#FFB81A]",
    ghost: "text-[#14151D] hover:bg-[#14151D]/5",
  }},
  defaultVariants: { variant: "ghost" },
});

export function Button({ className, variant, ...props }: ComponentProps<"button"> & VariantProps<typeof button>) {
  return <button className={twMerge(button({ variant }), className)} {...props} />;
}

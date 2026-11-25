import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "Fieldwork | Research assistant", description: "Ask questions and explore answers grounded in sources." };
export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
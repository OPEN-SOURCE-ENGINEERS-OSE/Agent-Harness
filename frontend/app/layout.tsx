import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Prama | Ask. Verify. Know.",
  description: "Answers you can check, grounded in sources you can open.",
  applicationName: "Prama",
};

export const viewport: Viewport = {
  themeColor: "#F4F1E7",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}

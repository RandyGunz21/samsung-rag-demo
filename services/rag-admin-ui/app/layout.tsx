import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { Navbar } from "@/components/layout/navbar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "RAG Admin Manager",
  description: "Manage, test, and query your RAG system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="flex h-screen overflow-hidden">
          {/* Sidebar */}
          <Sidebar />

          {/* Main content area */}
          <div className="flex flex-1 flex-col overflow-hidden">
            {/* Top navbar */}
            <Navbar />

            {/* Page content */}
            <main className="flex-1 overflow-y-auto bg-muted/10 p-6">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}

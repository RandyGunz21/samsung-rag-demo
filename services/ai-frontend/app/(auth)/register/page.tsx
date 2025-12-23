"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Page() {
  const router = useRouter();

  useEffect(() => {
    // No authentication required - redirect to home
    router.replace("/");
  }, [router]);

  return (
    <div className="flex h-dvh w-screen items-center justify-center bg-background">
      <p className="text-gray-500 text-sm">Redirecting...</p>
    </div>
  );
}

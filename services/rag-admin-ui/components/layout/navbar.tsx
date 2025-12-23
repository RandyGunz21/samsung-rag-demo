"use client";

import { usePathname } from "next/navigation";
import { Separator } from "@/components/ui/separator";

// Generate breadcrumbs from pathname
function generateBreadcrumbs(pathname: string) {
  const segments = pathname.split("/").filter(Boolean);

  const breadcrumbs = segments.map((segment, index) => {
    const path = "/" + segments.slice(0, index + 1).join("/");
    const label = segment
      .split("-")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");

    return { label, path };
  });

  return [{ label: "Home", path: "/" }, ...breadcrumbs];
}

export function Navbar() {
  const pathname = usePathname();
  const breadcrumbs = generateBreadcrumbs(pathname);

  return (
    <nav className="border-b bg-background">
      <div className="flex h-16 items-center px-6">
        <div className="flex items-center space-x-2 text-sm">
          {breadcrumbs.map((crumb, index) => (
            <div key={crumb.path} className="flex items-center">
              {index > 0 && <span className="mx-2 text-muted-foreground">/</span>}
              <a
                href={crumb.path}
                className={
                  index === breadcrumbs.length - 1
                    ? "font-medium text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }
              >
                {crumb.label}
              </a>
            </div>
          ))}
        </div>

        <div className="ml-auto flex items-center space-x-4">
          {/* Quick actions could go here */}
        </div>
      </div>
    </nav>
  );
}

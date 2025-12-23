"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Home,
  FlaskConical,
  Database,
  Search,
  FileText,
  Upload,
  PlayCircle,
  BarChart3,
} from "lucide-react";
import { Separator } from "@/components/ui/separator";

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  items?: NavItem[];
}

const navigation: NavItem[] = [
  {
    title: "Dashboard",
    href: "/",
    icon: Home,
  },
  {
    title: "Evaluation",
    href: "/evaluation",
    icon: FlaskConical,
    items: [
      {
        title: "Test Datasets",
        href: "/evaluation/datasets",
        icon: FileText,
      },
      {
        title: "Run Evaluation",
        href: "/evaluation/run",
        icon: PlayCircle,
      },
      {
        title: "View Results",
        href: "/evaluation/results",
        icon: BarChart3,
      },
    ],
  },
  {
    title: "Data Management",
    href: "/data",
    icon: Database,
    items: [
      {
        title: "Upload Files",
        href: "/data/upload",
        icon: Upload,
      },
      {
        title: "View Documents",
        href: "/data/documents",
        icon: FileText,
      },
    ],
  },
  {
    title: "Query Interface",
    href: "/query",
    icon: Search,
  },
];

function NavLink({ item }: { item: NavItem }) {
  const pathname = usePathname();
  const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all hover:bg-accent",
        isActive
          ? "bg-accent text-accent-foreground font-medium"
          : "text-muted-foreground hover:text-foreground"
      )}
    >
      <Icon className="h-4 w-4" />
      {item.title}
    </Link>
  );
}

export function Sidebar() {
  return (
    <div className="flex h-screen w-64 flex-col border-r bg-background">
      {/* Logo/Title */}
      <div className="flex h-16 items-center border-b px-6">
        <h1 className="text-xl font-bold">RAG Admin</h1>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto p-4">
        <nav className="space-y-1">
          {navigation.map((item) => (
            <div key={item.href}>
              <NavLink item={item} />

              {/* Sub-items */}
              {item.items && (
                <div className="ml-4 mt-1 space-y-1 border-l pl-4">
                  {item.items.map((subItem) => (
                    <NavLink key={subItem.href} item={subItem} />
                  ))}
                </div>
              )}
            </div>
          ))}
        </nav>
      </div>

      {/* Footer */}
      <div className="border-t p-4">
        <div className="text-xs text-muted-foreground">
          <p className="font-medium">RAG Admin Manager v1.0</p>
          <p>Manage, test, and query your RAG system</p>
        </div>
      </div>
    </div>
  );
}

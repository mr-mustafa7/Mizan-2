"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";

export const navItems = [
  { href: "/", label: "Dashboard", icon: "◈", shortLabel: "Home" },
  { href: "/patients", label: "Patients", icon: "◎", shortLabel: "Patients" },
  { href: "/trials", label: "Trials", icon: "⬡", shortLabel: "Trials" },
  { href: "/matches", label: "Matches", icon: "⇄", shortLabel: "Matches" },
  { href: "/control", label: "Control", icon: "⚙", shortLabel: "Control" },
];

export function isNavActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === "/control") return pathname.startsWith("/control");
  return pathname.startsWith(href);
}

interface NavLinkProps {
  href: string;
  label: string;
  icon: string;
  active: boolean;
  onClick?: () => void;
  className?: string;
  compact?: boolean;
}

export function NavLink({
  href,
  label,
  icon,
  active,
  onClick,
  className,
  compact,
}: NavLinkProps) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
        active
          ? "bg-blue-600/20 text-blue-300"
          : "text-slate-300 hover:bg-slate-800 hover:text-white",
        compact && "flex-col gap-1 px-2 py-2 text-[10px] font-medium",
        className
      )}
    >
      <span className={cn("text-base opacity-80", compact && "text-lg")}>
        {icon}
      </span>
      <span className={compact ? "leading-none" : undefined}>{label}</span>
    </Link>
  );
}

export function MobileBottomNav() {
  const pathname = usePathname();
  const mainItems = navItems.filter((item) => item.href !== "/control");

  return (
    <nav className="fixed inset-x-0 bottom-0 z-50 border-t border-slate-800 bg-[#0a101c]/95 backdrop-blur-lg lg:hidden pb-[env(safe-area-inset-bottom)]">
      <div className="mx-auto grid max-w-lg grid-cols-5">
        {mainItems.map((item) => (
          <NavLink
            key={item.href}
            href={item.href}
            label={item.shortLabel}
            icon={item.icon}
            active={isNavActive(pathname, item.href)}
            compact
            className={cn(
              "justify-center rounded-none border-0",
              isNavActive(pathname, item.href)
                ? "bg-transparent text-blue-400"
                : "text-slate-400 hover:bg-transparent hover:text-slate-200"
            )}
          />
        ))}
        <NavLink
          href="/control"
          label="Control"
          icon="⚙"
          active={pathname.startsWith("/control")}
          compact
          className={cn(
            "justify-center rounded-none border-0",
            pathname.startsWith("/control")
              ? "bg-transparent text-blue-400"
              : "text-slate-400 hover:bg-transparent hover:text-slate-200"
          )}
        />
      </div>
    </nav>
  );
}

export function MobileTopBar() {
  const pathname = usePathname();
  const current =
    navItems.find((item) => isNavActive(pathname, item.href)) ?? navItems[0];

  return (
    <header className="sticky top-0 z-40 flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 lg:hidden pt-[max(0.75rem,env(safe-area-inset-top))]">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
        M
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-slate-900">
          {current.label}
        </p>
        <p className="truncate text-xs text-slate-500">Mizan · Trial matching</p>
      </div>
    </header>
  );
}

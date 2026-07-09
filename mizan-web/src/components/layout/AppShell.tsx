"use client";

import type { ReactNode } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { MobileBottomNav, MobileTopBar } from "@/components/layout/MobileNav";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="coordinator-shell flex min-h-[100dvh] bg-slate-100">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <MobileTopBar />
        <header className="hidden border-b border-slate-200 bg-white px-6 py-4 lg:block lg:px-8">
          <p className="text-xs font-medium uppercase tracking-wider text-blue-600">
            Coordinator platform
          </p>
          <h1 className="text-lg font-semibold text-slate-900">
            Patient–trial matching with eligibility audit
          </h1>
        </header>
        <main className="flex-1 overflow-x-hidden px-4 py-4 pb-24 sm:px-6 sm:py-6 lg:px-8 lg:pb-6">
          {children}
        </main>
        <MobileBottomNav />
      </div>
    </div>
  );
}

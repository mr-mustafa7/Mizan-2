import Link from "next/link";
import type { ReactNode } from "react";
import { MobileBottomNav } from "@/components/layout/MobileNav";

export function ControlShell({ children }: { children: ReactNode }) {
  return (
    <div className="control-shell min-h-[100dvh] bg-[#0b1220] text-slate-100">
      <header className="border-b border-[#1e2d4a] bg-[#0a101c]">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 sm:py-5 lg:flex-row lg:items-start lg:justify-between pt-[max(1rem,env(safe-area-inset-top))]">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-widest text-blue-400">
              Mizan · behind the scenes
            </p>
            <h1 className="mt-1 text-lg font-semibold text-white sm:text-xl">
              TrialMatch — Recruitment Intelligence
            </h1>
            <p className="mt-1 text-xs text-slate-400 sm:text-sm">
              At-risk trials · Eligibility · Audit trail
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Tag label="Oncology" live />
            <Tag label="NSCLC" />
            <Tag label="Recruitment" />
            <Link
              href="/"
              className="rounded-lg border border-[#243552] px-3 py-1.5 text-xs text-slate-400 transition hover:border-blue-500 hover:text-white"
            >
              ← Coordinator
            </Link>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl overflow-x-hidden px-4 py-4 pb-24 sm:px-6 sm:py-6 lg:pb-6">
        {children}
      </main>
      <MobileBottomNav />
    </div>
  );
}

function Tag({ label, live }: { label: string; live?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-[#243552] bg-[#111a2e] px-2.5 py-1 text-xs text-slate-300 sm:px-3">
      {live && (
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
      )}
      {label}
    </span>
  );
}

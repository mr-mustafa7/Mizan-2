import { AppShell } from "@/components/layout/AppShell";

export default function CoordinatorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}

import { ControlShell } from "@/components/control/ControlShell";

export default function ControlLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <ControlShell>{children}</ControlShell>;
}

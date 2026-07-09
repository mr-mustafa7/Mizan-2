import { ControlPanel } from "@/components/control/ControlPanel";
import { api } from "@/lib/api";
import { mockApi } from "@/lib/mock-data";

export default async function ControlPage() {
  const [
    atRiskTrials,
    coordinatorDashboard,
    matches,
    trialSummary,
    diagnosisSummary,
  ] = await Promise.all([
    api.getAtRiskTrials(),
    api.getCoordinatorDashboard(),
    api.getMatches(),
    api.getTrialSummary(),
    api.getDiagnosisSummary(),
  ]);

  const auditRecords = mockApi.getAllAuditRecords();

  const totalShortfall = atRiskTrials.reduce((sum, t) => sum + t.shortfall, 0);
  const eligiblePatients = matches.filter((m) => m.tier === "ELIGIBLE").length;
  const reviewPatients =
    matches.filter((m) => m.tier === "REVIEW").length +
    matches.filter((m) => m.tier === "NEEDS_SCREENING").length;
  const topAtRiskTrialId = atRiskTrials[0]?.trial_id ?? "—";

  return (
    <ControlPanel
      atRiskTrials={atRiskTrials}
      coordinatorDashboard={coordinatorDashboard}
      matches={matches}
      auditRecords={auditRecords}
      trialSummary={trialSummary}
      diagnosisSummary={diagnosisSummary}
      kpis={{
        totalShortfall,
        eligiblePatients,
        reviewPatients,
        topAtRiskTrialId,
      }}
    />
  );
}

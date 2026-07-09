import { MatchTable } from "@/components/matches/MatchTable";
import { api } from "@/lib/api";

export default async function MatchesPage() {
  const matches = await api.getMatches();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Matches</h2>
        <p className="mt-1 text-sm text-slate-600">
          Patient–trial match results from the matching pipeline.
        </p>
      </div>
      <MatchTable matches={matches} />
    </div>
  );
}

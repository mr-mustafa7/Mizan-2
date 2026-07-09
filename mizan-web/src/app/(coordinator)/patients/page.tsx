import Link from "next/link";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api } from "@/lib/api";
import { patientLabel } from "@/lib/utils";

export default async function PatientsPage() {
  const patients = await api.getPatients();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Patients</h2>
        <p className="mt-1 text-sm text-slate-600">
          Patients in the matching pool.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {patients.map((patient) => (
          <Link
            key={patient.patient_id}
            href={`/patients/${patient.patient_id}`}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-teal-300 hover:shadow"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-slate-900">
                  {patient.patient_id}
                </p>
                <p className="text-sm text-slate-500">
                  {patientLabel(patient.patient_id, patient.age, patient.sex)}
                </p>
              </div>
              <StatusBadge
                label={`${patient.age}y`}
                className="border-slate-200 bg-slate-100 text-slate-700"
              />
            </div>
            <p className="mt-4 text-sm text-slate-600">
              {patient.city}, {patient.country}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}

import type { Finding } from "../lib/api";
import { clock, evidenceValue } from "../lib/format";
import { EstTag, More, ReadAloud, SevBadge, sevStripe } from "./ui";
import LessonLink from "./LessonLink";

export default function FindingCard({ finding, onMoment }: { finding: Finding; onMoment?: (t: number) => void }) {
  const lead = finding.evidence[0];
  const speech = `${finding.headline} Next game: ${finding.do_next}`;
  return (
    <article className="card relative overflow-hidden pl-7">
      <span className={`absolute left-0 top-0 h-full w-2 ${sevStripe(finding.severity)}`} aria-hidden />
      <div className="flex flex-wrap items-center gap-2">
        <SevBadge severity={finding.severity} />
        <span className="label">{finding.habit}</span>
        {finding.est && <EstTag />}
        <span className="ml-auto">
          <ReadAloud text={speech} />
        </span>
      </div>

      <div className="mt-3 flex flex-wrap items-start gap-5">
        {lead && (
          <div className="min-w-[7rem]">
            <div className="text-4xl font-bold leading-none">{evidenceValue(lead.value, lead.unit)}</div>
            {lead.benchmark != null && (
              <div className="text-sm text-dim mt-1">vs {evidenceValue(lead.benchmark, lead.unit)}</div>
            )}
          </div>
        )}
        <div className="flex-1 min-w-[14rem] space-y-3">
          <h3 className="text-xl font-bold">{finding.headline}</h3>
          <p className="rounded-xl bg-panel2 border-l-4 border-s1 px-4 py-2">
            <span className="font-bold text-s1">🎯 Next game: </span>
            {finding.do_next}
          </p>
          <LessonLink id={finding.lesson_id} />
        </div>
      </div>

      {(finding.more.length > 0 || finding.moments.length > 0) && (
        <div className="mt-3">
          <More>
            {finding.more.length > 0 && (
              <ul className="list-disc pl-6 space-y-1 text-dim">
                {finding.more.map((m) => (
                  <li key={m}>{m}</li>
                ))}
              </ul>
            )}
            {finding.evidence.length > 0 && (
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                {finding.evidence.map((e) => (
                  <div key={e.label} className="contents">
                    <dt className="text-dim">{e.label}</dt>
                    <dd className="font-bold">
                      {evidenceValue(e.value, e.unit)}
                      {e.benchmark != null && (
                        <span className="text-dim font-normal"> · typical {evidenceValue(e.benchmark, e.unit)}</span>
                      )}
                      {e.est && <EstTag />}
                    </dd>
                  </div>
                ))}
              </dl>
            )}
            {finding.moments.length > 0 && onMoment && (
              <div className="flex flex-wrap gap-2" aria-label="Moments in this match">
                {finding.moments.slice(0, 8).map((m, i) => (
                  <button
                    key={`${m.t}-${i}`}
                    type="button"
                    className="chip hover:border-s1"
                    onClick={() => onMoment(m.t)}
                    title="Show this moment on the timeline and map"
                  >
                    <span aria-hidden>▶</span> {clock(m.t)} {m.label}
                  </button>
                ))}
              </div>
            )}
          </More>
        </div>
      )}
    </article>
  );
}

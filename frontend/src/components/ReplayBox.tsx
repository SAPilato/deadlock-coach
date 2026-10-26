import { useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Report } from "../lib/api";
import { Amphora, Download, Film, Hourglass, TriangleAlert, Upload } from "lucide-react";
import { Icon } from "./ui";

const BUSY = ["downloading", "parsing", "queued"];

export default function ReplayBox({ report }: { report: Report }) {
  const id = report.match.id;
  const qc = useQueryClient();
  const file = useRef<HTMLInputElement>(null);
  const status = useQuery({
    queryKey: ["replay", id],
    queryFn: () => api.replayStatus(id),
    initialData: report.replay,
    refetchInterval: (q) => (BUSY.includes(q.state.data?.status ?? "") ? 2000 : false),
  });
  const done = () => {
    qc.invalidateQueries({ queryKey: ["replay", id] });
  };
  const upload = useMutation({ mutationFn: (f: File) => api.replayUpload(id, f), onSuccess: done });
  const fetchDemo = useMutation({ mutationFn: () => api.replayFetch(id), onSuccess: done });

  const s = status.data?.status ?? "none";
  const wasBusy = useRef(false);
  if (BUSY.includes(s)) wasBusy.current = true;
  if (s === "done" && wasBusy.current) {
    wasBusy.current = false;
    qc.invalidateQueries({ queryKey: ["report", id] });
  }

  return (
    <div className="space-y-3">
      <ul className="space-y-1 text-dim">
        <li>
          <Icon icon={Amphora} /> Adds the urn check.
        </li>
        <li>
          <Icon icon={Film} /> Replays come from the in-game match history.
        </li>
        <li>
          <Icon icon={Hourglass} /> Valve deletes old replays after a while.
        </li>
      </ul>
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" className="btn-primary" onClick={() => fetchDemo.mutate()} disabled={BUSY.includes(s) || fetchDemo.isPending}>
          <Icon icon={Download} /> Try auto-download
        </button>
        <input
          ref={file}
          type="file"
          accept=".dem,.bz2"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) upload.mutate(f);
          }}
        />
        <button type="button" className="btn" onClick={() => file.current?.click()} disabled={BUSY.includes(s) || upload.isPending}>
          <Icon icon={Upload} /> Upload .dem file
        </button>
        <span className="chip">
          Status: <b className="ml-1">{s === "none" ? "no replay" : s}</b>
        </span>
      </div>
      {(status.data?.error || upload.error || fetchDemo.error) && (
        <p className="text-high">
          <Icon icon={TriangleAlert} /> {status.data?.error || String(upload.error || fetchDemo.error)}</p>
      )}
    </div>
  );
}

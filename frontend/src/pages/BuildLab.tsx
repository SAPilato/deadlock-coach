import { useEffect, useMemo, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Build, type SavedBuild, type Target } from "../lib/api";
import { ErrorBox, HeroIcon, Icon, Loading, Section } from "../components/ui";
import HeroPicker from "../components/build/HeroPicker";
import Slots from "../components/build/Slots";
import Shop from "../components/build/Shop";
import StatTable from "../components/build/StatTable";
import Effects from "../components/build/Effects";
import Dummy from "../components/build/Dummy";
import SavedBuilds from "../components/build/SavedBuilds";
import Abilities from "../components/build/Abilities";
import Helper from "../components/build/Helper";
import { souls } from "../components/build/common";
import { ArrowLeftRight, ChartColumn, FlaskConical, Save, TriangleAlert, WandSparkles } from "lucide-react";

const DEFAULT_TARGET: Target = { hp: 2500, bullet_resist: 0, headshot_pct: 0, spirit_resist: 0 };
const STORE_KEY = "coach.buildlab.v1";

type Work = Build & { name: string; id: number | null };

function loadWork(): Work | null {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    return raw ? (JSON.parse(raw) as Work) : null;
  } catch {
    return null;
  }
}

function saveWork(w: Work) {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(w));
  } catch {
    /* private mode: the build just isn't remembered */
  }
}

// Older saved builds lack newer fields; fill them with defaults.
const buildOf = (w: Partial<Build> & { hero_id: number }): Build => ({
  hero_id: w.hero_id,
  level: w.level ?? 1,
  items: w.items ?? [],
  toggles: w.toggles ?? [],
  target: { ...DEFAULT_TARGET, ...(w.target ?? {}) },
  ability_tier: w.ability_tier ?? 0,
});

export default function BuildLab() {
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const heroes = useQuery({ queryKey: ["bl-heroes"], queryFn: api.blHeroes, staleTime: Infinity });
  const matches = useQuery({ queryKey: ["matches"], queryFn: () => api.matches() });
  const builds = useQuery({ queryKey: ["builds"], queryFn: api.builds });
  const [work, setWork] = useState<Work | null>(loadWork);
  const [preview, setPreview] = useState<number | null>(null);
  const [compareId, setCompareId] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // First visit: start on the hero from your latest match.
  useEffect(() => {
    if (work || !heroes.data || matches.isLoading) return;
    const recent = matches.data?.matches.find((m) => !m.street_brawl)?.hero.id;
    const hero_id = recent ?? heroes.data[0]?.id;
    if (hero_id) setWork({ hero_id, level: 1, items: [], toggles: [], target: DEFAULT_TARGET, ability_tier: 0, name: "My build", id: null });
  }, [work, heroes.data, matches.data]);

  // /build?match=123 imports what you owned at the end of that match.
  const matchParam = params.get("match");
  useEffect(() => {
    if (!matchParam) return;
    api
      .matchBuild(Number(matchParam))
      .then((m) => {
        setWork({ hero_id: m.hero_id, level: m.level, items: m.items, toggles: [], target: DEFAULT_TARGET, ability_tier: 0, name: m.name, id: null });
        setNotice(`Loaded your items from match ${matchParam}.`);
      })
      .catch((e) => setNotice(`Could not load that match: ${e.message}`))
      .finally(() => setParams({}, { replace: true }));
  }, [matchParam, setParams]);

  useEffect(() => {
    if (work) saveWork(work);
  }, [work]);

  const build = work ? buildOf(work) : null;
  const shop = useQuery({
    queryKey: ["bl-shop", work?.hero_id],
    queryFn: () => api.blShop(work!.hero_id),
    enabled: !!work,
  });
  // Deep links like /build#shop (from a lesson) scroll once that section exists.
  const { hash } = useLocation();
  const shopReady = !!shop.data;
  useEffect(() => {
    if (hash && shopReady) document.getElementById(hash.slice(1))?.scrollIntoView({ block: "start" });
  }, [hash, shopReady]);
  const sheet = useQuery({
    queryKey: ["bl-sheet", build],
    queryFn: () => api.blCompute(build!),
    enabled: !!build,
    placeholderData: keepPreviousData,
  });
  const base = useQuery({
    queryKey: ["bl-sheet", build && { ...build, items: [], toggles: [] }],
    queryFn: () => api.blCompute({ ...build!, items: [], toggles: [] }),
    enabled: !!build,
    placeholderData: keepPreviousData,
  });
  const previewBuild = build && preview != null ? { ...build, items: [...build.items, preview] } : null;
  const previewSheet = useQuery({
    queryKey: ["bl-sheet", previewBuild],
    queryFn: () => api.blCompute(previewBuild!),
    enabled: !!previewBuild,
  });
  const compareBuild = builds.data?.find((b) => b.id === compareId) ?? null;
  const compareSheet = useQuery({
    queryKey: ["bl-sheet", compareBuild && buildOf(compareBuild)],
    queryFn: () => api.blCompute(buildOf(compareBuild!)),
    enabled: !!compareBuild,
  });

  const save = useMutation({
    mutationFn: (asNew: boolean) => api.saveBuild({ ...buildOf(work!), name: work!.name, id: asNew ? undefined : work!.id ?? undefined }),
    onSuccess: (b) => {
      setWork((w) => (w ? { ...w, id: b.id } : w));
      qc.invalidateQueries({ queryKey: ["builds"] });
      setNotice(`Saved "${b.name}".`);
    },
  });
  const remove = useMutation({
    mutationFn: (b: SavedBuild) => api.deleteBuild(b.id),
    onSuccess: (_r, b) => {
      qc.invalidateQueries({ queryKey: ["builds"] });
      if (work?.id === b.id) setWork((w) => (w ? { ...w, id: null } : w));
      if (compareId === b.id) setCompareId(null);
    },
  });
  const importFile = useMutation({
    mutationFn: api.importBuild,
    onSuccess: (b) => {
      qc.invalidateQueries({ queryKey: ["builds"] });
      setNotice(`Imported "${b.name}".`);
    },
  });

  const itemsById = useMemo(() => new Map((shop.data?.items ?? []).map((i) => [i.id, i])), [shop.data]);
  const heroMap = useMemo(() => new Map((heroes.data ?? []).map((h) => [h.id, h])), [heroes.data]);

  if (heroes.isLoading || !work) return <Loading label="Loading heroes and items…" />;
  if (heroes.error) return <ErrorBox error={heroes.error} />;

  // Functional updates: two quick clicks must both land.
  const update = (patch: Partial<Work> | ((w: Work) => Partial<Work>)) =>
    setWork((w) => (w ? { ...w, ...(typeof patch === "function" ? patch(w) : patch) } : w));
  const slots = shop.data?.slots ?? { limit: 12, est: true, players: 0 };
  const buildItems = work.items.map((id) => itemsById.get(id)).filter((i): i is NonNullable<typeof i> => !!i);
  const levels = shop.data?.levels ?? [];
  const levelInfo = levels.find((l) => l.level === work.level);
  const previewItem = preview != null ? itemsById.get(preview) : undefined;
  const toggles = new Set(work.toggles);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-3xl font-bold">
          <Icon icon={FlaskConical} className="text-accent" /> Build Lab
        </h1>
        <span className="text-dim">Try items. See exactly what changes.</span>
      </div>
      {notice && (
        <p className="card border-accent" role="status">
          {notice}{" "}
          <button type="button" className="text-accent font-bold" onClick={() => setNotice(null)}>
            OK
          </button>
        </p>
      )}

      <Section title="1. Hero and level">
        <div className="flex flex-wrap items-start gap-6">
          <HeroPicker heroes={heroes.data ?? []} value={work.hero_id} onChange={(hero_id) => update({ hero_id, toggles: [] })} />
          <label className="min-w-[16rem] flex-1">
            <span className="flex flex-wrap justify-between gap-2">
              <span className="text-xl font-bold">Level {work.level}</span>
              {levelInfo && (
                <span className="text-dim tnum">
                  {levelInfo.boons} boons · {souls(levelInfo.souls)} souls
                </span>
              )}
            </span>
            <input
              type="range"
              min={1}
              max={levels.length || 36}
              value={work.level}
              onChange={(e) => update({ level: Number(e.target.value) })}
              className="mt-2 w-full accent-accent"
              aria-label="Hero level"
            />
          </label>
        </div>
      </Section>

      <Section id="helper" icon={WandSparkles} title="2. Build helper">
        <Helper
          build={build!}
          heroes={heroes.data ?? []}
          full={work.items.length >= slots.limit}
          lastMatchId={matches.data?.matches.find((m) => !m.street_brawl)?.match_id ?? null}
          onAdd={(ids) =>
            update((w) => ({ items: [...w.items, ...ids.filter((id) => !w.items.includes(id))].slice(0, slots.limit) }))
          }
        />
      </Section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,30rem)]">
        <div className="space-y-6 min-w-0">
          <Section title="3. Your build">
            <Slots
              items={buildItems}
              limit={slots.limit}
              limitEst={slots.est}
              cost={sheet.data?.cost ?? 0}
              onRemove={(id) =>
                update((w) => ({ items: w.items.filter((i) => i !== id), toggles: w.toggles.filter((k) => !k.startsWith(`${id}:`)) }))
              }
            />
            {sheet.data?.warnings.map((w) => (
              <p key={w} className="text-low">
                <Icon icon={TriangleAlert} /> {w}
              </p>
            ))}
          </Section>
          <Section id="shop" title="4. Shop">
            {shop.isLoading && <Loading label="Loading the shop…" />}
            {shop.error && <ErrorBox error={shop.error} />}
            {shop.data && (
              <Shop
                shop={shop.data}
                inBuild={new Set(work.items)}
                full={work.items.length >= slots.limit}
                onAdd={(id) => {
                  update((w) => ({ items: w.items.includes(id) || w.items.length >= slots.limit ? w.items : [...w.items, id] }));
                  setPreview(null);
                }}
                onPreview={setPreview}
              />
            )}
          </Section>
        </div>

        <div className="lg:sticky lg:top-24 self-start space-y-3">
          <Section
            icon={ChartColumn}
            title="Stats"
            aside={previewItem && <span className="chip border-accent text-accent">Preview: + {previewItem.name}</span>}
          >
            {sheet.error && <ErrorBox error={sheet.error} />}
            {previewItem && previewSheet.data ? (
              <StatTable before={sheet.data} after={previewSheet.data} beforeLabel="Now" afterLabel={`+ ${previewItem.name}`} />
            ) : (
              <StatTable before={base.data} after={sheet.data} beforeLabel="No items" afterLabel="This build" />
            )}
            {sheet.data?.notes.map((n) => (
              <p key={n} className="text-sm text-muted">
                {n}
              </p>
            ))}
            <p className="text-sm text-muted">Hover an item in the shop to preview it.</p>
          </Section>
        </div>
      </div>

      <Section title="5. Conditional effects">
        <Effects
          effects={sheet.data?.effects ?? []}
          toggles={toggles}
          onToggle={(key) =>
            update((w) => ({ toggles: w.toggles.includes(key) ? w.toggles.filter((k) => k !== key) : [...w.toggles, key] }))
          }
        />
      </Section>

      <Section title="6. DPS dummy">
        <Dummy target={buildOf(work).target} onChange={(target) => update({ target })} sheet={sheet.data} />
      </Section>

      <Section title="7. Ability damage">
        <Abilities
          sheet={sheet.data}
          tier={build?.ability_tier ?? 0}
          onTier={(ability_tier) => update({ ability_tier })}
          spiritResist={build?.target.spirit_resist ?? 0}
          onSpiritResist={(spirit_resist) => update((w) => ({ target: { ...buildOf(w).target, spirit_resist } }))}
        />
      </Section>

      <Section title="8. Save and compare">
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate(false);
          }}
        >
          <label className="flex-1 min-w-[14rem]">
            <span className="label block mb-1">Build name</span>
            <input
              value={work.name}
              maxLength={60}
              onChange={(e) => update({ name: e.target.value })}
              className="w-full rounded-xl bg-panel2 border border-line px-4 py-2"
            />
          </label>
          <button type="submit" className="btn-primary" disabled={!work.name.trim() || save.isPending}>
            <Icon icon={Save} /> {work.id ? "Save changes" : "Save"}
          </button>
          {work.id && (
            <button type="button" className="btn" onClick={() => save.mutate(true)} disabled={save.isPending}>
              Save as new
            </button>
          )}
        </form>
        {(save.error || importFile.error || remove.error) && <ErrorBox error={save.error || importFile.error || remove.error} />}
        <SavedBuilds
          builds={builds.data ?? []}
          heroes={heroMap}
          currentId={work.id}
          compareId={compareId}
          onLoad={(b) => {
            setWork({ ...buildOf(b), name: b.name, id: b.id });
            setNotice(`Opened "${b.name}".`);
          }}
          onCompare={setCompareId}
          onDelete={(b) => {
            if (window.confirm(`Delete "${b.name}"? This cannot be undone.`)) remove.mutate(b);
          }}
          onImport={(data) => importFile.mutate(data)}
        />
      </Section>

      {compareBuild && (
        <Section icon={ArrowLeftRight} title={`This build vs "${compareBuild.name}"`} aside={<button type="button" className="chip" onClick={() => setCompareId(null)}>Close</button>}>
          <div className="grid gap-4 md:grid-cols-2">
            <ItemStrip title="This build" ids={work.items} itemsById={itemsById} heroImage={heroMap.get(work.hero_id)} />
            <ItemStrip title={compareBuild.name} ids={compareBuild.items} itemsById={itemsById} heroImage={heroMap.get(compareBuild.hero_id)} />
          </div>
          <StatTable before={sheet.data} after={compareSheet.data} beforeLabel="This build" afterLabel="Other" />
          <p className="text-sm text-muted">Change = other build minus this build.</p>
        </Section>
      )}
    </div>
  );
}

function ItemStrip({
  title,
  ids,
  itemsById,
  heroImage,
}: {
  title: string;
  ids: number[];
  itemsById: Map<number, { name: string; image?: string }>;
  heroImage?: { id: number; name: string; image?: string };
}) {
  return (
    <div className="rounded-xl bg-panel2 border border-line p-3 space-y-2">
      <div className="flex items-center gap-2 font-bold">
        {heroImage && <HeroIcon hero={heroImage} size={28} />} {title}
      </div>
      <div className="flex flex-wrap gap-1">
        {ids.map((id) => {
          const it = itemsById.get(id);
          return it?.image ? (
            <img key={id} src={it.image} alt={it.name} title={it.name} className="h-9 w-9 rounded-md" />
          ) : (
            <span key={id} className="chip text-xs">
              {it?.name ?? id}
            </span>
          );
        })}
        {ids.length === 0 && <span className="text-dim">No items</span>}
      </div>
    </div>
  );
}

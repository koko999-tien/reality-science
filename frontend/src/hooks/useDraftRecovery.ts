"use client";
import { useLayoutEffect, useRef, useState } from "react";
import type { CanvasState } from "./useEquationCanvas";
import type { DraftSnapshot } from "@/types/contracts";

type Recovery = { snapshot: DraftSnapshot; savedKey: string; primary: string | null; canvas: CanvasState };
// Same-tab in-memory recovery for Next client navigation and browser history.
// The access session and owner gate prevent recovery under another login.
const pending = new Map<string, Recovery>();

export function useDraftRecovery(slug: string, draft: {
  snapshot: DraftSnapshot | null; savedKey: string | null; primaryEquationId: string | null;
  loading: boolean; restore: (snapshot: DraftSnapshot, key: string, primary: string | null) => void;
}, dirty: boolean, editable: boolean, getCanvas: () => CanvasState, restoreCanvas: (value: CanvasState) => void) {
  const latest = useRef<{ key: string; value: Recovery | null } | null>(null);
  const attempted = useRef(new Set<string>());
  const [message, setMessage] = useState("");
  useLayoutEffect(() => {
    attempted.current.clear();
    latest.current = null;
    setMessage("");
    return () => {
      const saved = latest.current;
      if (!saved) return;
      if (saved.value) {
        pending.set(saved.key, saved.value);
        if (pending.size > 10) pending.delete(pending.keys().next().value!);
      } else pending.delete(saved.key);
    };
  }, [slug]);
  useLayoutEffect(() => {
    if (draft.loading || !draft.snapshot || !draft.savedKey) return;
    const session = sessionStorage.getItem("reality-science.access-token");
    if (!session) { latest.current = null; return; }
    const key = `${session}:${slug}:${draft.snapshot.version.id}`;
    if (!attempted.current.has(key)) {
      attempted.current.add(key);
      const recovery = pending.get(key);
      pending.delete(key);
      if (editable && recovery) {
        draft.restore(recovery.snapshot, recovery.savedKey, recovery.primary);
        restoreCanvas(recovery.canvas);
        setMessage("Recovered unsaved edits from this tab. Save or reload the saved draft to continue.");
        return;
      }
    }
    latest.current = { key, value: dirty && editable ? { snapshot: draft.snapshot, savedKey: draft.savedKey,
      primary: draft.primaryEquationId, canvas: getCanvas() } : null };
    if (!dirty) setMessage("");
  }, [draft, slug, dirty, editable, getCanvas, restoreCanvas]);
  return message;
}

"""My Plants: active plantings, stage updates, care history, finish/archive."""

from __future__ import annotations

import streamlit as st

from verdant.domain import SeedVariety
from verdant.domain.plantings import GROWTH_STAGES

from .common import STAGE_LABELS, Page, esc, notify, run_safely


def render(page: Page):
    show_archived = st.toggle("Show archived", key=page.key("show_archived"))
    plantings = page.service.plantings(page.user_id, page.gid, status=None if show_archived else "active")
    if not plantings:
        st.info("No plantings yet. Open the Seed Library and choose **Start planting** on a seed.")
        return
    spaces = {s.id: s.name for s in page.service.spaces(page.user_id, page.gid)}
    tasks = page.service.tasks(page.user_id, page.gid)
    for p in plantings:
        variety = page.service.repo.get(SeedVariety, p.seed_variety_id)
        name = p.nickname or variety.label
        with st.container(border=True):
            st.markdown(f"**{esc(name)}** · {STAGE_LABELS[p.growth_stage]}"
                        + (" · archived" if p.status == "archived" else ""))
            dates = [f"sown {p.sown_on}" if p.sown_on else None,
                     f"germinated {p.germinated_on}" if p.germinated_on else None,
                     f"transplanted {p.transplanted_on}" if p.transplanted_on else None]
            st.caption(f"{p.quantity} in {spaces.get(p.growing_space_id, '?')} · "
                       + (", ".join(d for d in dates if d) or "no dates recorded"))
            observations = page.service.observations(page.user_id, page.gid, p.id)
            history = [t for t in tasks if t.planting_id == p.id]
            st.caption(f"{len(observations)} journal entr{'y' if len(observations) == 1 else 'ies'} · "
                       f"{sum(t.completed for t in history)} care task(s) done")
            if p.status == "archived":
                continue
            with st.expander("Update"):
                with st.form(page.key(f"stage_{p.id}")):
                    a, b = st.columns(2)
                    stage = a.selectbox("Stage", GROWTH_STAGES, index=GROWTH_STAGES.index(p.growth_stage),
                                        format_func=STAGE_LABELS.get, key=page.key(f"stage_sel_{p.id}"))
                    sown = b.date_input("Sown on", p.sown_on, key=page.key(f"sown_{p.id}"))
                    germ = a.date_input("Germinated on", p.germinated_on, key=page.key(f"germ_{p.id}"))
                    trans = b.date_input("Transplanted on", p.transplanted_on, key=page.key(f"trans_{p.id}"))
                    space = st.selectbox("Space", list(spaces), index=list(spaces).index(p.growing_space_id),
                                         format_func=spaces.get, key=page.key(f"space_{p.id}"))
                    notes = st.text_area("Notes", p.notes, key=page.key(f"notes_{p.id}"))
                    if st.form_submit_button("Save"):
                        run_safely(lambda: page.service.update_planting(
                            page.user_id, page.gid, p.id, growth_stage=stage, sown_on=sown, germinated_on=germ,
                            transplanted_on=trans, growing_space_id=space, notes=notes), "Planting updated.")
                if history:
                    st.markdown("**Care history**")
                    st.table([{"Date": str(t.due_date), "Task": t.description,
                               "Status": "done" if t.completed else "pending"} for t in history[-10:]])
                c1, c2 = st.columns(2)
                if c1.button("Mark finished", key=page.key(f"finish_{p.id}")):
                    page.service.archive_planting(page.user_id, page.gid, p.id, finished=True)
                    notify(f"{name} finished and archived.")
                if c2.button("Archive", key=page.key(f"archive_{p.id}")):
                    page.service.archive_planting(page.user_id, page.gid, p.id, finished=False)
                    notify(f"{name} archived.")

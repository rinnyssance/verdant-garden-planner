"""Seed Library: what this garden owns. Starting a planting is a separate, explicit step."""

from __future__ import annotations

import streamlit as st

from verdant.domain import SeedVariety
from verdant.domain.plantings import GROWTH_STAGES
from verdant.domain.seeds import CATEGORIES
from verdant.services.inventory import load_crop_reference
from verdant.services.photos import photo_belongs_to, save_photo

from .common import VERIFY_LABELS, Page, badge, esc, notify, optional, run_safely


def add_seed_form(page: Page):
    crops = ["", *sorted(load_crop_reference()["crops"])]
    with st.expander("Add a seed packet", expanded=False):
        with st.form(page.key("add_seed"), clear_on_submit=True):
            name = st.text_input("Common name", placeholder="e.g. Tomato", key=page.key("seed_name"))
            cultivar = st.text_input("Variety / cultivar (optional)", key=page.key("seed_cultivar"))
            a, b = st.columns(2)
            category = a.selectbox("Category", CATEGORIES, key=page.key("seed_cat"))
            crop = b.selectbox("Crop type (for weather advice)", crops,
                               format_func=lambda c: c.replace("_", " ") or "Not sure", key=page.key("seed_crop"))
            brand = a.text_input("Brand (optional)", key=page.key("seed_brand"))
            packets = b.number_input("Packets", min_value=0, value=None, step=1, key=page.key("seed_packets"))
            notes = st.text_area("Packet directions or notes", key=page.key("seed_notes"))
            photo = st.file_uploader("Packet photo (PNG/JPEG/WebP, max 5 MB)", type=["png", "jpg", "jpeg", "webp"],
                                     key=page.key("seed_photo"))
            if st.form_submit_button("Add to library", type="primary"):
                def add():
                    path = save_photo(page.gid, photo.getvalue()) if photo else None
                    variety = SeedVariety(name, category, cultivar=optional(cultivar), crop_key=optional(crop),
                                          brand=optional(brand), planting_notes=notes, verification_status="user_entered")
                    return page.service.add_seed(page.user_id, page.gid, variety,
                                                 packet_count=None if packets is None else int(packets),
                                                 packet_photo_path=path)
                run_safely(add, "Seed added to this garden's library.")


def start_planting_form(page: Page, item, variety, spaces):
    if not spaces:
        st.caption("Add a growing space first to start a planting.")
        return
    space_map = {s.id: s.name for s in spaces}
    with st.form(page.key(f"plant_{item.id}"), clear_on_submit=True):
        st.markdown("**Start planting**")
        a, b = st.columns(2)
        space_id = a.selectbox("Where", list(space_map), format_func=space_map.get, key=page.key(f"pl_space_{item.id}"))
        quantity = b.number_input("How many", 1, 10000, 1, key=page.key(f"pl_qty_{item.id}"))
        stage = a.selectbox("Stage", GROWTH_STAGES[:4], index=1, key=page.key(f"pl_stage_{item.id}"))
        sown = b.date_input("Sown on", page.today, key=page.key(f"pl_sown_{item.id}"))
        nickname = st.text_input("Nickname (optional)", key=page.key(f"pl_nick_{item.id}"))
        if st.form_submit_button("Start planting", type="primary"):
            run_safely(lambda: page.service.start_planting(
                page.user_id, page.gid, item.id, space_id, int(quantity), growth_stage=stage,
                sown_on=None if stage == "planned" else sown, nickname=optional(nickname)),
                f"Planting started for {variety.label}. Your seed stock is unchanged.")


def render(page: Page):
    inventory = page.service.inventory(page.user_id, page.gid)
    spaces = page.service.spaces(page.user_id, page.gid)
    add_seed_form(page)
    if not inventory:
        st.info("This garden's seed library is empty. Add packets above, or import your packet list in Settings.")
        return
    a, b, c = st.columns([2, 1, 1])
    query = a.text_input("Search seeds", key=page.key("seed_q"), placeholder="name or variety").strip().lower()
    category = b.selectbox("Category", ["All", *CATEGORIES], key=page.key("seed_cat_filter"))
    status = c.selectbox("Status", ["All", *VERIFY_LABELS], format_func=lambda s: VERIFY_LABELS.get(s, s),
                         key=page.key("seed_status_filter"))
    shown = [(i, v) for i, v in inventory
             if (not query or query in v.label.lower())
             and (category == "All" or v.category == category)
             and (status == "All" or v.verification_status == status)]
    st.caption(f"Showing {len(shown)} of {len(inventory)} seed records. Owning seeds does not mean they are planted.")
    for item, variety in shown:
        with st.container(border=True):
            kind = {"verified": "ok", "needs_review": "review"}.get(variety.verification_status, "info")
            st.markdown(f"**{esc(variety.label)}** " + badge(variety.category) +
                        badge(VERIFY_LABELS[variety.verification_status], kind), unsafe_allow_html=True)
            stock = "unknown" if item.packet_count is None else f"{item.packet_count} packet(s)"
            st.caption(f"Stock: {stock}" + (f" · Brand: {variety.brand}" if variety.brand else "")
                       + (" · **expired**" if item.is_expired(page.today) else ""))
            if variety.planting_notes:
                st.write(variety.planting_notes)
            if photo_belongs_to(item.packet_photo_path, page.gid):
                st.image(item.packet_photo_path, width=220)
            with st.expander("Details, review and planting"):
                if variety.verification_status != "verified":
                    if st.button("I checked the packet: mark verified", key=page.key(f"verify_{item.id}")):
                        page.service.update_variety(page.user_id, page.gid, variety.id, verification_status="verified")
                        notify(f"{variety.label} marked verified.")
                with st.form(page.key(f"stock_{item.id}")):
                    packets = st.number_input("Packets", min_value=0, value=item.packet_count, step=1,
                                              key=page.key(f"stock_n_{item.id}"))
                    expiry = st.date_input("Use by (optional)", value=item.expiry_on, key=page.key(f"stock_exp_{item.id}"))
                    if st.form_submit_button("Save stock"):
                        run_safely(lambda: page.service.update_inventory_item(
                            page.user_id, page.gid, item.id, packet_count=None if packets is None else int(packets),
                            expiry_on=expiry), "Stock updated.")
                start_planting_form(page, item, variety, spaces)

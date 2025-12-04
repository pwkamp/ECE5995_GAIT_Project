from __future__ import annotations

import time
from typing import Dict, List

import streamlit as st


class ButtonRow:
    """Reusable layout helpers for horizontally aligned buttons."""

    @staticmethod
    def two(label_left: str, label_right: str, keys: List[str]) -> Dict[str, bool]:
        col_left, col_right = st.columns(2)
        clicked = {}
        with col_left:
            clicked["left"] = st.button(label_left, key=keys[0], use_container_width=True)
        with col_right:
            clicked["right"] = st.button(
                label_right, key=keys[1], use_container_width=True
            )
        return clicked

    @staticmethod
    def single(label: str, key: str, disabled: bool = False) -> bool:
        return st.button(label, key=key, use_container_width=True, disabled=disabled)


class ProgressHelper:
    """Simple progress bar helper to simulate async tasks."""

    @staticmethod
    def run(label: str, steps: int = 5, delay: float = 0.2) -> None:
        placeholder = st.empty()
        with placeholder:
            st.write(label)
            bar = st.progress(0)
            for i in range(1, steps + 1):
                bar.progress(int(i / steps * 100))
                time.sleep(delay)
        placeholder.empty()

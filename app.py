import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

# 0. 기본 설정
st.set_page_config(
    page_title="리튬 공급망 SCM 인텔리전스 시스템",
    layout="wide"
)

# UI 스타일 CSS
anim_css = (
    "<style>"
    "div[data-testid='stMetricValue'] { font-size: 1.7rem; }"
    "div[data-testid='stSegmentedControl'] {"
    "    background: #f1f5f9; padding: 5px; border-radius: 14px;"
    "    border: 1px solid #e2e8f0; box-shadow: inset 0 2px 4px rgba(0,0,0,0.03);"
    "}"
    "div[data-testid='stSegmentedControl'] button {"
    "    border-radius: 10px !important; font-weight: 600 !important; border: none !important;"
    "    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;"
    "}"
    "div[data-testid='stSegmentedControl'] button:hover {"
    "    background-color: rgba(255, 255, 255, 0.8) !important;"
    "}"
    "div[data-testid='stSegmentedControl'] button[aria-checked='true'] {"
    "    background: #ffffff !important; color: #0f172a !important;"
    "    box-shadow: 0 4px 10px -2px rgba(0, 0, 0, 0.1) !important;"
    "    transform: scale(1.02);"
    "}"
    ".route-detail-box {"
    "    padding: 18px 22px; border-radius: 12px; background: #ffffff;"
    "    border: 1px solid #e2e8f0; margin-top: 15px; margin-bottom: 20px;"
    "    box-shadow: 0 4px 12px rgba(0,0,0,0.04);"
    "}"
    ".risk-card-high {"
    "    background: #fff5f5; border: 1px solid #feb2b2; border-left: 6px solid #e53e3e;"
    "    padding: 16px 20px; border-radius: 10px; margin-bottom: 12px;"
    "}"
    "</style>"
)
st.markdown(anim_css, unsafe

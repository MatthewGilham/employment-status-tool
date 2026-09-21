"""Dark theme with a neon-lime accent for the Gradio interface.

Colours only: nothing here changes layout, sizing or behaviour.
"""
import gradio as gr

# Palette
BG = "#0f0f13"          # page background
PANEL = "#1a1a23"       # blocks and panels
INPUT = "#24242d"       # text boxes and dropdowns
BORDER = "#2b2b33"      # hairline borders
TEXT = "#fafafa"        # main text
MUTED = "#a1a1aa"       # labels and secondary text
NEON = "#d3fe51"        # accent
NEON_HOVER = "#c2ef3a"  # accent on hover
NEON_SOFT = "#2a3312"   # faint accent background

THEME = gr.themes.Base(
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
).set(
    # Page and panels
    body_background_fill=BG,
    body_background_fill_dark=BG,
    background_fill_primary=BG,
    background_fill_primary_dark=BG,
    background_fill_secondary=PANEL,
    background_fill_secondary_dark=PANEL,
    block_background_fill=PANEL,
    block_background_fill_dark=PANEL,
    block_border_color=BORDER,
    block_border_color_dark=BORDER,
    border_color_primary=BORDER,
    border_color_primary_dark=BORDER,
    block_radius="14px",
    block_shadow="none",
    block_shadow_dark="none",

    # Text
    body_text_color=TEXT,
    body_text_color_dark=TEXT,
    body_text_color_subdued=MUTED,
    body_text_color_subdued_dark=MUTED,
    block_label_text_color=MUTED,
    block_label_text_color_dark=MUTED,
    block_label_background_fill=PANEL,
    block_label_background_fill_dark=PANEL,
    block_title_text_color=TEXT,
    block_title_text_color_dark=TEXT,

    # Inputs
    input_background_fill=INPUT,
    input_background_fill_dark=INPUT,
    input_border_color=BORDER,
    input_border_color_dark=BORDER,
    input_border_color_focus=NEON,
    input_border_color_focus_dark=NEON,

    # Accent: checkboxes, selected tab, links
    color_accent=NEON,
    color_accent_soft=NEON_SOFT,
    color_accent_soft_dark=NEON_SOFT,
    checkbox_background_color=INPUT,
    checkbox_background_color_dark=INPUT,
    checkbox_background_color_selected=NEON,
    checkbox_background_color_selected_dark=NEON,
    checkbox_border_color=BORDER,
    checkbox_border_color_dark=BORDER,
    checkbox_border_color_selected=NEON,
    checkbox_border_color_selected_dark=NEON,
    link_text_color=NEON,
    link_text_color_dark=NEON,

    # Primary button: dark with a neon outline; fills neon on hover
    button_primary_background_fill=PANEL,
    button_primary_background_fill_dark=PANEL,
    button_primary_background_fill_hover=NEON,
    button_primary_background_fill_hover_dark=NEON,
    button_primary_text_color=NEON,
    button_primary_text_color_dark=NEON,
    button_primary_text_color_hover=BG,
    button_primary_text_color_hover_dark=BG,
    button_primary_border_color=NEON,
    button_primary_border_color_dark=NEON,

    # Secondary buttons: quiet
    button_secondary_background_fill=INPUT,
    button_secondary_background_fill_dark=INPUT,
    button_secondary_background_fill_hover=BORDER,
    button_secondary_background_fill_hover_dark=BORDER,
    button_secondary_text_color=TEXT,
    button_secondary_text_color_dark=TEXT,
    button_secondary_border_color=BORDER,
    button_secondary_border_color_dark=BORDER,
)

# Visual polish only: glows and accent colours. No sizes, widths or spacing.
CSS = f"""
input:focus, textarea:focus {{
    box-shadow: 0 0 0 1px {NEON}, 0 0 12px rgba(211, 254, 81, 0.18) !important;
}}
button.primary {{
    box-shadow: inset 0 0 0 1px rgba(211, 254, 81, 0.7);
    transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}}
button.primary:hover {{
    box-shadow: inset 0 0 0 1px {NEON}, 0 0 16px rgba(211, 254, 81, 0.35);
}}
button[role="tab"][aria-selected="true"] {{
    color: {NEON} !important;
    border-color: {NEON} !important;
}}
"""
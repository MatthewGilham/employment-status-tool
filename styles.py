"""Dark themes with a single bright accent for the Gradio interface.

Colours only: nothing here changes layout, sizing or behaviour.
Pick one in app.py, e.g. theme=styles.CYAN_THEME, css=styles.CYAN_CSS
"""
import gradio as gr

# Shared dark palette (taken from the reference screenshot)
BG = "#0f0f13"      # page background
PANEL = "#1a1a23"   # blocks and panels
INPUT = "#24242d"   # text boxes and dropdowns
BORDER = "#2b2b33"  # hairline borders
TEXT = "#fafafa"    # main text
MUTED = "#a1a1aa"   # labels and secondary text


def build(accent, accent_soft, glow_rgb):
    """Build a matching theme and CSS for one accent colour.

    accent      -- the bright colour, e.g. "#22d3ee"
    accent_soft -- a very dark tint of it, for subtle backgrounds
    glow_rgb    -- the accent as "r, g, b", used for glows
    """
    theme = gr.themes.Base(
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
        input_border_color_focus=accent,
        input_border_color_focus_dark=accent,

        # Accent: checkboxes, selected tab, links
        color_accent=accent,
        color_accent_soft=accent_soft,
        color_accent_soft_dark=accent_soft,
        checkbox_background_color=INPUT,
        checkbox_background_color_dark=INPUT,
        checkbox_background_color_selected=accent,
        checkbox_background_color_selected_dark=accent,
        checkbox_border_color=BORDER,
        checkbox_border_color_dark=BORDER,
        checkbox_border_color_selected=accent,
        checkbox_border_color_selected_dark=accent,
        link_text_color=accent,
        link_text_color_dark=accent,

        # Primary button: dark with an accent outline; fills on hover
        button_primary_background_fill=PANEL,
        button_primary_background_fill_dark=PANEL,
        button_primary_background_fill_hover=accent,
        button_primary_background_fill_hover_dark=accent,
        button_primary_text_color=accent,
        button_primary_text_color_dark=accent,
        button_primary_text_color_hover=BG,
        button_primary_text_color_hover_dark=BG,
        button_primary_border_color=accent,
        button_primary_border_color_dark=accent,

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
    css = f"""
input:focus, textarea:focus {{
    box-shadow: 0 0 0 1px {accent}, 0 0 12px rgba({glow_rgb}, 0.18) !important;
}}
button.primary {{
    box-shadow: inset 0 0 0 1px rgba({glow_rgb}, 0.7);
    transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}}
button.primary:hover {{
    box-shadow: inset 0 0 0 1px {accent}, 0 0 16px rgba({glow_rgb}, 0.35);
}}
button[role="tab"][aria-selected="true"] {{
    color: {accent} !important;
    border-color: {accent} !important;
}}
"""
    return theme, css


# Neon green
NEON_THEME, NEON_CSS = build("#d3fe51", "#2a3312", "211, 254, 81")

# Cyan
CYAN_THEME, CYAN_CSS = build("#22d3ee", "#0c2a31", "34, 211, 238")

PURPLE_THEME, PURPLE_CSS = build("#a78bfa", "#221a3a", "167, 139, 250")

# Kept so your existing app.py (styles.THEME / styles.CSS) still works
THEME, CSS = NEON_THEME, NEON_CSS
"""
ui_generator.py — Premium HTML report generator.

Features:
  - Dark glassmorphism design with gradient accents
  - Russian localization throughout
  - Type filters (Reels / Карусели / Все)
  - Velocity sub-metrics (likes/h, comments/h, views/h, overall index)
  - Custom animated checkboxes
  - CSV download + Google Sheets clipboard export
  - Sortable columns
  - Footer with Banana Master branding
"""
import html
import json
from typing import Any


def generate_results_html(posts: list[dict[str, Any]], output_path: str) -> None:
    """Write a standalone HTML file with an interactive results table."""

    rows_html = ""
    for i, p in enumerate(posts):
        post_type = str(p.get("post_type", "?"))
        url = html.escape(str(p.get("url", "")))
        username = html.escape(str(p.get("owner_username", "")))
        caption = html.escape(str(p.get("caption_text", ""))[:140])
        likes = p.get("likes", 0)
        comments = p.get("comments", 0)
        views = p.get("views", 0)
        velocity = p.get("velocity_score", 0)
        hours_ago = p.get("hours_ago", 0)
        source = html.escape(str(p.get("source", "")))

        # Compute sub-velocities
        h = float(hours_ago) if hours_ago and float(hours_ago) > 0 else 999.0
        vel_likes = round(likes / h, 1)
        vel_comments = round(comments / h, 1)
        vel_views = round(views / h, 1) if p.get("is_reel") else 0

        # Type badge config
        type_config = {
            "reel":     {"label": "Reels",    "class": "badge-reel"},
            "carousel": {"label": "Карусель", "class": "badge-carousel"},
            "video":    {"label": "Видео",    "class": "badge-video"},
            "image":    {"label": "Фото",     "class": "badge-image"},
        }
        tc = type_config.get(post_type, {"label": post_type, "class": "badge-other"})

        # Velocity tier for color coding
        if velocity >= 10000:
            vel_class = "vel-fire"
        elif velocity >= 1000:
            vel_class = "vel-hot"
        elif velocity >= 100:
            vel_class = "vel-warm"
        else:
            vel_class = "vel-cold"

        rows_html += f"""
        <tr class="table-row" data-type="{post_type}" data-idx="{i}">
          <td class="td-check">
            <label class="custom-check">
              <input type="checkbox" class="row-check" data-idx="{i}">
              <span class="checkmark"></span>
            </label>
          </td>
          <td><span class="badge {tc['class']}">{tc['label']}</span></td>
          <td><a href="{url}" target="_blank" rel="noopener" class="post-link">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
            Открыть</a>
          </td>
          <td class="td-user">@{username}</td>
          <td class="td-caption" title="{caption}">{caption}</td>
          <td class="td-num">{likes:,}</td>
          <td class="td-num">{comments:,}</td>
          <td class="td-num">{views:,}</td>
          <td class="td-vel-sub">{vel_likes:,.0f}</td>
          <td class="td-vel-sub">{vel_comments:,.0f}</td>
          <td class="td-vel-sub">{vel_views:,.0f}</td>
          <td class="td-velocity {vel_class}">{velocity:,.1f}</td>
          <td class="td-age">{hours_ago}ч</td>
          <td class="td-source">{source}</td>
        </tr>"""

    total_posts = len(posts)
    reels_count = sum(1 for p in posts if p.get("post_type") == "reel")
    carousel_count = sum(1 for p in posts if p.get("post_type") == "carousel")

    page_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Viral Hunter — Результаты анализа</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  /* ═══════ RESET & BASE ═══════ */
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  
  :root {{
    --bg-deep: #06060b;
    --bg-card: rgba(255,255,255,0.025);
    --bg-card-hover: rgba(255,255,255,0.045);
    --border: rgba(255,255,255,0.06);
    --border-hover: rgba(255,255,255,0.12);
    --text-primary: #e8e6f0;
    --text-secondary: #8b87a0;
    --text-muted: #5a5672;
    --accent-1: #a855f7;
    --accent-2: #ec4899;
    --accent-3: #f97316;
    --vel-fire: #ff6b35;
    --vel-hot: #fbbf24;
    --vel-warm: #a3e635;
    --vel-cold: #64748b;
    --glass: rgba(255,255,255,0.03);
    --glass-border: rgba(255,255,255,0.07);
  }}

  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg-deep);
    color: var(--text-primary);
    min-height: 100vh;
    overflow-x: hidden;
    scrollbar-color: rgba(168,85,247,0.3) transparent;
    scrollbar-width: thin;
  }}

  /* ═══════ CUSTOM SCROLLBARS ═══════ */
  ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{
    background: linear-gradient(180deg, rgba(168,85,247,0.35), rgba(236,72,153,0.25));
    border-radius: 100px;
    border: 2px solid transparent;
    background-clip: padding-box;
  }}
  ::-webkit-scrollbar-thumb:hover {{
    background: linear-gradient(180deg, rgba(168,85,247,0.55), rgba(236,72,153,0.45));
    background-clip: padding-box;
  }}
  ::-webkit-scrollbar-corner {{ background: transparent; }}
  .table-scroll::-webkit-scrollbar {{ height: 6px; }}
  .table-scroll::-webkit-scrollbar-track {{ background: rgba(255,255,255,0.02); border-radius: 100px; }}
  .table-scroll::-webkit-scrollbar-thumb {{
    background: linear-gradient(90deg, rgba(168,85,247,0.4), rgba(236,72,153,0.3));
    border-radius: 100px;
  }}

  /* ═══════ AMBIENT BACKGROUND ═══════ */
  body::before {{
    content: '';
    position: fixed;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: 
      radial-gradient(ellipse at 20% 20%, rgba(168,85,247,0.08) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 80%, rgba(236,72,153,0.06) 0%, transparent 50%),
      radial-gradient(ellipse at 50% 50%, rgba(249,115,22,0.04) 0%, transparent 50%);
    z-index: -1;
    animation: ambientDrift 20s ease-in-out infinite alternate;
  }}
  @keyframes ambientDrift {{
    0% {{ transform: translate(0, 0) rotate(0deg); }}
    100% {{ transform: translate(-3%, -3%) rotate(2deg); }}
  }}

  .container {{ max-width: 1520px; margin: 0 auto; padding: 2rem 1.5rem 1rem; }}

  /* ═══════ HEADER ═══════ */
  .header {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
    gap: 1rem;
  }}
  .header-left h1 {{
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, var(--accent-1), var(--accent-2), var(--accent-3));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
  .header-left p {{
    color: var(--text-secondary);
    font-size: 0.875rem;
    margin-top: 0.25rem;
  }}
  .header-left p span {{
    font-weight: 600;
    color: var(--text-primary);
  }}

  /* ═══════ STATS ROW ═══════ */
  .stats-row {{
    display: flex;
    gap: 0.75rem;
    margin-bottom: 1.25rem;
    flex-wrap: wrap;
  }}
  .stat-card {{
    background: var(--glass);
    border: 1px solid var(--glass-border);
    border-radius: 14px;
    padding: 0.875rem 1.25rem;
    backdrop-filter: blur(16px);
    min-width: 140px;
    transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
  }}
  .stat-card:hover {{
    border-color: var(--border-hover);
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
  }}
  .stat-card .stat-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    font-weight: 700;
    background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
  .stat-card .stat-label {{
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.15rem;
  }}

  /* ═══════ TOOLBAR ═══════ */
  .toolbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
    flex-wrap: wrap;
    gap: 0.75rem;
  }}

  /* Filter pills */
  .filters {{
    display: flex;
    gap: 0.5rem;
  }}
  .filter-pill {{
    padding: 0.5rem 1.1rem;
    border-radius: 100px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-secondary);
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
    font-family: inherit;
    position: relative;
    overflow: hidden;
  }}
  .filter-pill::before {{
    content: '';
    position: absolute;
    inset: 0;
    border-radius: inherit;
    opacity: 0;
    transition: opacity 0.25s;
  }}
  .filter-pill:hover {{
    border-color: var(--border-hover);
    color: var(--text-primary);
  }}
  .filter-pill.active {{
    background: linear-gradient(135deg, rgba(168,85,247,0.2), rgba(236,72,153,0.15));
    border-color: rgba(168,85,247,0.4);
    color: #fff;
    font-weight: 600;
    box-shadow: 0 0 20px rgba(168,85,247,0.15);
  }}
  .filter-pill .pill-count {{
    display: inline-block;
    background: rgba(255,255,255,0.1);
    padding: 0.1rem 0.45rem;
    border-radius: 100px;
    font-size: 0.7rem;
    margin-left: 0.35rem;
    font-family: 'JetBrains Mono', monospace;
  }}
  .filter-pill.active .pill-count {{
    background: rgba(255,255,255,0.15);
  }}

  /* Action buttons */
  .actions {{
    display: flex;
    gap: 0.5rem;
  }}
  .btn {{
    padding: 0.55rem 1.2rem;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--glass);
    color: var(--text-secondary);
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.25s;
    font-family: inherit;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    backdrop-filter: blur(8px);
  }}
  .btn:hover {{
    border-color: var(--border-hover);
    color: var(--text-primary);
    transform: translateY(-1px);
  }}
  .btn-primary {{
    background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
    border: none;
    color: #fff;
    font-weight: 600;
    box-shadow: 0 4px 20px rgba(168,85,247,0.25);
  }}
  .btn-primary:hover {{
    box-shadow: 0 6px 28px rgba(168,85,247,0.35);
    transform: translateY(-2px);
  }}
  .btn-sheets {{
    background: linear-gradient(135deg, #0f9d58 0%, #34A853 100%);
    color: white;
    border: none;
    box-shadow: 0 4px 14px rgba(52,168,83,0.35);
  }}
  .btn-sheets:hover {{
    background: linear-gradient(135deg, #0b8043 0%, #2d9248 100%);
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(52,168,83,0.5);
  }}

  /* ── Google Sheets Modal ── */
  .sheets-modal-overlay {{
    display: none;
    position: fixed; inset: 0; z-index: 9999;
    background: rgba(0,0,0,0.6);
    backdrop-filter: blur(12px);
    align-items: center; justify-content: center;
  }}
  .sheets-modal-overlay.open {{
    display: flex;
    animation: modalFadeIn 0.3s ease;
  }}
  @keyframes modalFadeIn {{
    from {{ opacity: 0; transform: scale(0.95); }}
    to   {{ opacity: 1; transform: scale(1); }}
  }}
  .sheets-modal-card {{
    background: #1a1a1e;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 24px;
    padding: 40px 48px;
    text-align: center;
    max-width: 400px; width: 90%;
    box-shadow: 0 40px 80px rgba(0,0,0,0.5);
    position: relative;
  }}
  .sheets-modal-icon {{
    font-size: 3rem; margin-bottom: 16px;
    animation: popIn 0.5s cubic-bezier(0.34,1.56,0.64,1);
  }}
  @keyframes popIn {{
    from {{ transform: scale(0); }}
    to   {{ transform: scale(1); }}
  }}
  .sheets-modal-title {{
    font-size: 1.5rem; font-weight: 700; color: #fff;
    margin: 0 0 8px;
  }}
  .sheets-modal-sub {{
    color: rgba(255,255,255,0.5); font-size: 0.9rem; margin: 0 0 24px;
  }}
  .sheets-modal-hint {{
    display: inline-flex; align-items: center; gap: 10px;
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 100px; padding: 10px 20px; margin-bottom: 28px;
    font-size: 0.95rem; color: rgba(255,255,255,0.7);
  }}
  kbd {{
    background: rgba(255,255,255,0.12); border-radius: 6px;
    padding: 2px 8px; font-weight: 700; color: #fff; font-size: 0.9rem;
    border: 1px solid rgba(255,255,255,0.15);
  }}
  .sheets-modal-countdown-wrap {{
    display: flex; flex-direction: column; align-items: center; gap: 8px;
    margin-bottom: 24px;
  }}
  .sheets-modal-ring {{
    position: relative; width: 64px; height: 64px;
  }}
  .sheets-modal-ring svg {{
    width: 100%; height: 100%;
  }}
  .sheets-modal-ring span {{
    position: absolute; inset: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem; font-weight: 700; color: #34C759;
  }}
  .sheets-modal-timer-label {{
    font-size: 0.8rem; color: rgba(255,255,255,0.4); margin: 0;
  }}
  .sheets-modal-btn {{
    display: block; width: 100%;
    background: linear-gradient(135deg, #0f9d58, #34A853);
    color: #fff; font-weight: 700; font-size: 1rem;
    border: none; border-radius: 14px; padding: 14px;
    cursor: pointer; margin-bottom: 10px;
    transition: all 0.2s;
    box-shadow: 0 4px 14px rgba(52,168,83,0.4);
  }}
  .sheets-modal-btn:hover {{
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(52,168,83,0.55);
  }}
  .sheets-modal-cancel {{
    background: none; border: none;
    color: rgba(255,255,255,0.3); font-size: 0.85rem;
    cursor: pointer; padding: 4px;
    transition: color 0.2s;
  }}
  .sheets-modal-cancel:hover {{ color: rgba(255,255,255,0.6); }}

  .btn-toast {{
    animation: toastPop 0.4s cubic-bezier(0.34,1.56,0.64,1);
  }}
  @keyframes toastPop {{
    0% {{ transform: scale(0.95); }}
    50% {{ transform: scale(1.05); }}
    100% {{ transform: scale(1); }}
  }}

  /* ═══════ TABLE ═══════ */
  .table-wrap {{
    background: var(--bg-card);
    border: 1px solid var(--glass-border);
    border-radius: 18px;
    overflow: hidden;
    backdrop-filter: blur(20px);
    box-shadow: 
      0 4px 40px rgba(0,0,0,0.3),
      inset 0 1px 0 rgba(255,255,255,0.04);
  }}
  .table-scroll {{ overflow-x: auto; }}

  table {{ width: 100%; border-collapse: collapse; }}
  
  thead tr {{
    background: rgba(255,255,255,0.03);
    border-bottom: 1px solid var(--border);
  }}
  th {{
    padding: 0.75rem 0.65rem;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    text-align: left;
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
    transition: color 0.2s;
    position: relative;
  }}
  th:hover {{ color: var(--accent-1); }}
  th.sorted-asc::after {{ content: ' ↑'; color: var(--accent-1); }}
  th.sorted-desc::after {{ content: ' ↓'; color: var(--accent-1); }}
  th.no-sort {{ cursor: default; }}
  th.no-sort:hover {{ color: var(--text-muted); }}

  .th-right {{ text-align: right; }}
  .th-velocity {{
    text-align: right;
    background: linear-gradient(90deg, transparent, rgba(168,85,247,0.05));
    border-left: 1px solid rgba(168,85,247,0.1);
  }}

  /* Rows */
  .table-row {{
    border-bottom: 1px solid rgba(255,255,255,0.03);
    transition: all 0.2s cubic-bezier(0.4,0,0.2,1);
  }}
  .table-row:hover {{
    background: var(--bg-card-hover);
  }}
  .table-row.hidden {{ display: none; }}
  .table-row td {{ padding: 0.7rem 0.65rem; font-size: 0.82rem; }}

  /* ═══════ CUSTOM CHECKBOX ═══════ */
  .custom-check {{
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }}
  .custom-check input {{ display: none; }}
  .checkmark {{
    width: 20px;
    height: 20px;
    border: 2px solid rgba(255,255,255,0.12);
    border-radius: 6px;
    transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
    position: relative;
    background: rgba(255,255,255,0.03);
  }}
  .checkmark::after {{
    content: '';
    position: absolute;
    left: 5px;
    top: 1px;
    width: 6px;
    height: 11px;
    border: solid #fff;
    border-width: 0 2.5px 2.5px 0;
    transform: rotate(45deg) scale(0);
    transition: transform 0.2s cubic-bezier(0.34,1.56,0.64,1);
  }}
  .custom-check input:checked + .checkmark {{
    background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
    border-color: transparent;
    box-shadow: 0 2px 12px rgba(168,85,247,0.35);
  }}
  .custom-check input:checked + .checkmark::after {{
    transform: rotate(45deg) scale(1);
  }}
  .custom-check:hover .checkmark {{
    border-color: rgba(168,85,247,0.4);
  }}

  /* Header checkbox */
  .th-check {{
    width: 50px;
  }}

  /* ═══════ BADGES ═══════ */
  .badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.3rem 0.7rem;
    border-radius: 100px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    white-space: nowrap;
  }}
  .badge-reel {{
    background: linear-gradient(135deg, rgba(168,85,247,0.2), rgba(168,85,247,0.1));
    color: #c084fc;
    border: 1px solid rgba(168,85,247,0.2);
  }}
  .badge-carousel {{
    background: linear-gradient(135deg, rgba(59,130,246,0.2), rgba(59,130,246,0.1));
    color: #60a5fa;
    border: 1px solid rgba(59,130,246,0.2);
  }}
  .badge-video {{
    background: linear-gradient(135deg, rgba(239,68,68,0.2), rgba(239,68,68,0.1));
    color: #f87171;
    border: 1px solid rgba(239,68,68,0.2);
  }}
  .badge-image {{
    background: linear-gradient(135deg, rgba(34,197,94,0.2), rgba(34,197,94,0.1));
    color: #4ade80;
    border: 1px solid rgba(34,197,94,0.2);
  }}
  .badge-other {{
    background: rgba(255,255,255,0.05);
    color: var(--text-secondary);
    border: 1px solid var(--border);
  }}

  /* ═══════ CELLS ═══════ */
  .post-link {{
    color: var(--accent-1);
    text-decoration: none;
    font-weight: 500;
    font-size: 0.8rem;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    transition: color 0.2s;
  }}
  .post-link:hover {{ color: var(--accent-2); }}
  .post-link svg {{ opacity: 0.7; }}

  .td-check {{ width: 50px; text-align: center; }}
  .td-user {{ color: var(--text-primary); font-weight: 500; white-space: nowrap; }}
  .td-caption {{
    color: var(--text-secondary);
    font-size: 0.78rem;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .td-num {{
    text-align: right;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: var(--text-primary);
  }}
  .td-vel-sub {{
    text-align: right;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-muted);
    border-left: 1px solid rgba(168,85,247,0.05);
    background: rgba(168,85,247,0.02);
  }}
  .td-velocity {{
    text-align: right;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    font-weight: 700;
    border-left: 1px solid rgba(168,85,247,0.1);
    background: rgba(168,85,247,0.03);
  }}
  .vel-fire {{ color: var(--vel-fire); text-shadow: 0 0 12px rgba(255,107,53,0.4); }}
  .vel-hot {{ color: var(--vel-hot); text-shadow: 0 0 10px rgba(251,191,36,0.3); }}
  .vel-warm {{ color: var(--vel-warm); }}
  .vel-cold {{ color: var(--vel-cold); }}

  .td-age {{
    text-align: right;
    font-size: 0.75rem;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
  }}
  .td-source {{
    font-size: 0.7rem;
    color: var(--text-muted);
    white-space: nowrap;
  }}

  /* ═══════ FOOTER ═══════ */
  .footer {{
    margin-top: 2rem;
    padding: 1.5rem 0;
    text-align: center;
    border-top: 1px solid var(--border);
  }}
  .footer-brand {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-bottom: 0.5rem;
  }}
  .footer-brand strong {{
    background: linear-gradient(135deg, var(--accent-1), var(--accent-2), var(--accent-3));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 700;
  }}
  .footer-links {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1.5rem;
    font-size: 0.75rem;
  }}
  .footer-links a {{
    color: var(--text-muted);
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    transition: color 0.2s;
  }}
  .footer-links a:hover {{ color: var(--accent-1); }}
  .footer-formula {{
    color: var(--text-muted);
    font-size: 0.65rem;
    margin-top: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
  }}

  /* ═══════ TOAST ═══════ */
  .toast {{
    position: fixed;
    bottom: 2rem;
    left: 50%;
    transform: translateX(-50%) translateY(100px);
    background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
    color: #fff;
    padding: 0.75rem 1.5rem;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 600;
    box-shadow: 0 8px 32px rgba(168,85,247,0.35);
    opacity: 0;
    transition: all 0.4s cubic-bezier(0.34,1.56,0.64,1);
    z-index: 1000;
    pointer-events: none;
  }}
  .toast.show {{
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }}

  /* ═══════ RESPONSIVE ═══════ */
  @media (max-width: 768px) {{
    .container {{ padding: 1rem; }}
    .header-left h1 {{ font-size: 1.5rem; }}
    .stats-row {{ gap: 0.5rem; }}
    .stat-card {{ min-width: 100px; padding: 0.65rem 0.85rem; }}
    .stat-card .stat-value {{ font-size: 1.15rem; }}
  }}

  /* ═══════ SETTINGS PANEL ═══════ */
  .settings-toggle {{
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.55rem 1.2rem;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--glass);
    color: var(--text-secondary);
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.25s;
    font-family: inherit;
    backdrop-filter: blur(8px);
  }}
  .settings-toggle:hover {{
    border-color: var(--border-hover);
    color: var(--text-primary);
  }}
  .settings-toggle.open {{
    border-color: rgba(168,85,247,0.4);
    color: var(--accent-1);
  }}
  .settings-toggle .arrow {{
    transition: transform 0.3s;
    font-size: 0.6rem;
  }}
  .settings-toggle.open .arrow {{
    transform: rotate(180deg);
  }}

  .settings-panel {{
    max-height: 0;
    overflow: hidden;
    transition: max-height 0.4s cubic-bezier(0.4,0,0.2,1), opacity 0.3s, margin 0.3s;
    opacity: 0;
    margin-bottom: 0;
  }}
  .settings-panel.open {{
    max-height: 400px;
    opacity: 1;
    margin-bottom: 1rem;
  }}
  .settings-inner {{
    background: var(--glass);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    backdrop-filter: blur(16px);
  }}
  .settings-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem;
  }}
  .setting-group {{
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }}
  .setting-label {{
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
  }}
  .setting-range {{
    display: flex;
    gap: 0.4rem;
    align-items: center;
  }}
  .setting-input {{
    width: 100%;
    padding: 0.45rem 0.65rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: rgba(255,255,255,0.04);
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    outline: none;
    transition: border-color 0.2s;
  }}
  .setting-input::placeholder {{ color: var(--text-muted); opacity: 0.6; }}
  .setting-input:focus {{ border-color: var(--accent-1); }}
  .setting-sep {{
    color: var(--text-muted);
    font-size: 0.7rem;
    flex-shrink: 0;
  }}

  /* Toggle switch */
  .toggle-row {{
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }}
  .toggle {{
    position: relative;
    width: 40px;
    height: 22px;
    flex-shrink: 0;
  }}
  .toggle input {{ display: none; }}
  .toggle-track {{
    position: absolute;
    inset: 0;
    border-radius: 100px;
    background: rgba(255,255,255,0.08);
    border: 1px solid var(--border);
    cursor: pointer;
    transition: all 0.25s;
  }}
  .toggle-track::after {{
    content: '';
    position: absolute;
    top: 2px;
    left: 2px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--text-muted);
    transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
  }}
  .toggle input:checked + .toggle-track {{
    background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
    border-color: transparent;
  }}
  .toggle input:checked + .toggle-track::after {{
    left: 20px;
    background: #fff;
  }}
  .toggle-text {{
    font-size: 0.78rem;
    color: var(--text-secondary);
  }}

  .settings-actions {{
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 1rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--border);
  }}
  .btn-sm {{
    padding: 0.4rem 1rem;
    font-size: 0.75rem;
    border-radius: 8px;
  }}
</style>
</head>
<body>

<div class="container">

  <!-- Header -->
  <div class="header">
    <div class="header-left">
      <h1>🛰 Viral Hunter</h1>
      <p>Найдено <span>{total_posts}</span> постов — ранжировано по Индексу Виральности</p>
    </div>
  </div>

  <!-- Stats -->
  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-value">{total_posts}</div>
      <div class="stat-label">Всего постов</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{reels_count}</div>
      <div class="stat-label">Reels</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{carousel_count}</div>
      <div class="stat-label">Карусели</div>
    </div>
    <div class="stat-card">
      <div class="stat-value" id="visible-count">{total_posts}</div>
      <div class="stat-label">Показано</div>
    </div>
  </div>

  <!-- Toolbar -->
  <div class="toolbar">
    <div class="filters">
      <button class="filter-pill active" data-filter="all" onclick="filterType('all')">
        Все <span class="pill-count">{total_posts}</span>
      </button>
      <button class="filter-pill" data-filter="reel" onclick="filterType('reel')">
        🎬 Reels <span class="pill-count">{reels_count}</span>
      </button>
      <button class="filter-pill" data-filter="carousel" onclick="filterType('carousel')">
        📑 Карусели <span class="pill-count">{carousel_count}</span>
      </button>
    </div>
    <div class="actions">
      <button class="settings-toggle" id="settings-btn" onclick="toggleSettings()">
        ⚙️ Фильтры <span class="arrow">▼</span>
      </button>
      <button class="btn" onclick="selectAll()">☑ Выбрать все</button>
      <button class="btn btn-primary" onclick="exportCSV()">📥 Скачать CSV</button>
      <button class="btn btn-sheets" onclick="exportToSheets()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14zM7 10h2v7H7zm4-3h2v10h-2zm4 6h2v4h-2z"/></svg>
        Google Sheets
      </button>
    </div>
  </div>

  <!-- Settings Panel -->
  <div class="settings-panel" id="settings-panel">
    <div class="settings-inner">
      <div class="settings-grid">
        <div class="setting-group">
          <div class="setting-label">❤️ Лайки</div>
          <div class="setting-range">
            <input type="number" class="setting-input" id="f-min-likes" placeholder="мин" min="0">
            <span class="setting-sep">—</span>
            <input type="number" class="setting-input" id="f-max-likes" placeholder="макс" min="0">
          </div>
        </div>
        <div class="setting-group">
          <div class="setting-label">💬 Комментарии</div>
          <div class="setting-range">
            <input type="number" class="setting-input" id="f-min-comments" placeholder="мин" min="0">
            <span class="setting-sep">—</span>
            <input type="number" class="setting-input" id="f-max-comments" placeholder="макс" min="0">
          </div>
        </div>
        <div class="setting-group">
          <div class="setting-label">👁 Просмотры</div>
          <div class="setting-range">
            <input type="number" class="setting-input" id="f-min-views" placeholder="мин" min="0">
            <span class="setting-sep">—</span>
            <input type="number" class="setting-input" id="f-max-views" placeholder="макс" min="0">
          </div>
        </div>
        <div class="setting-group">
          <div class="setting-label">👥 Подписчики автора</div>
          <div class="setting-range">
            <input type="number" class="setting-input" id="f-min-followers" placeholder="мин" min="0">
            <span class="setting-sep">—</span>
            <input type="number" class="setting-input" id="f-max-followers" placeholder="макс (напр. 100000)" min="0">
          </div>
        </div>
        <div class="setting-group">
          <div class="setting-label">🔥 Индекс виральности</div>
          <div class="setting-range">
            <input type="number" class="setting-input" id="f-min-velocity" placeholder="мин" min="0">
            <span class="setting-sep">—</span>
            <input type="number" class="setting-input" id="f-max-velocity" placeholder="макс" min="0">
          </div>
        </div>
        <div class="setting-group">
          <div class="setting-label">Исключения</div>
          <div class="toggle-row" style="margin-top: 0.2rem;">
            <label class="toggle">
              <input type="checkbox" id="f-exclude-zero">
              <span class="toggle-track"></span>
            </label>
            <span class="toggle-text">Скрыть посты с 0 лайков и 0 комментов</span>
          </div>
        </div>
      </div>
      <div class="settings-actions">
        <button class="btn btn-sm" onclick="resetFilters()">Сбросить</button>
        <button class="btn btn-primary btn-sm" onclick="applyFilters()">Применить</button>
      </div>
    </div>
  </div>

  <!-- Table -->
  <div class="table-wrap">
    <div class="table-scroll">
      <table id="results-table">
        <thead>
          <tr>
            <th class="th-check no-sort">
              <label class="custom-check">
                <input type="checkbox" id="check-all">
                <span class="checkmark"></span>
              </label>
            </th>
            <th onclick="sortTable(1)">Тип</th>
            <th class="no-sort">Ссылка</th>
            <th onclick="sortTable(3)">Автор</th>
            <th class="no-sort">Текст</th>
            <th class="th-right" onclick="sortTable(5)">Лайки</th>
            <th class="th-right" onclick="sortTable(6)">Комменты</th>
            <th class="th-right" onclick="sortTable(7)">Просмотры</th>
            <th class="th-velocity" onclick="sortTable(8)">❤/ч</th>
            <th class="th-velocity" onclick="sortTable(9)">💬/ч</th>
            <th class="th-velocity" onclick="sortTable(10)">👁/ч</th>
            <th class="th-velocity" onclick="sortTable(11)">Индекс 🔥</th>
            <th class="th-right" onclick="sortTable(12)">Возраст</th>
            <th onclick="sortTable(13)">Источник</th>
          </tr>
        </thead>
        <tbody id="table-body">
          {rows_html}
        </tbody>
      </table>
    </div>
  </div>

  <!-- Footer -->
  <div class="footer">
    <div class="footer-brand">
      <span>🍌</span> Создано <strong>Banana Master</strong>
    </div>
    <div class="footer-links">
      <a href="https://banana_marketing.t.me" target="_blank" rel="noopener">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12s5.37 12 12 12 12-5.37 12-12S18.63 0 12 0zm5.95 7.17l-1.97 9.3c-.15.67-.54.83-1.09.52l-3.02-2.22-1.46 1.4c-.16.16-.3.3-.61.3l.22-3.06 5.55-5.02c.24-.22-.05-.34-.38-.13l-6.86 4.32-2.96-.92c-.64-.2-.66-.64.14-.95l11.58-4.46c.53-.2 1 .13.82.95z"/></svg>
        Telegram
      </a>
      <a href="https://www.threads.com/@hackmemasters" target="_blank" rel="noopener">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12.186 24h-.007C5.461 24 .122 18.636.122 11.845c0-.119 0-.24.005-.36C.344 5.054 5.748.004 12.18 0h.014c6.487 0 11.823 5.394 11.823 12.015C24.017 18.63 18.641 24 12.186 24zm-.07-22.015h-.009C6.624 1.99 2.33 6.308 2.118 11.628v.217c0 5.633 4.398 10.14 9.994 10.155h.005c5.545-.012 10.006-4.551 10.006-10.155C22.123 6.28 17.65 1.985 12.116 1.985z"/></svg>
        Threads
      </a>
    </div>
    <div class="footer-formula">Индекс Виральности = (Лайки + Комменты×2 + Просмотры×0.5) / Часы</div>
  </div>
</div>

<!-- Toast notification -->
<div class="toast" id="toast"></div>

<!-- Google Sheets Modal -->
<div id="sheets-modal" class="sheets-modal-overlay" onclick="closeSheetsModal()">
  <div class="sheets-modal-card" onclick="event.stopPropagation()">
    <div class="sheets-modal-icon">📋</div>
    <h2 class="sheets-modal-title">Таблица в буфере обмена!</h2>
    <p class="sheets-modal-sub" id="sheets-row-count"></p>
    <div class="sheets-modal-hint">
      <kbd>Ctrl</kbd> + <kbd>V</kbd>
      <span>в Google Sheets</span>
    </div>
    <div class="sheets-modal-countdown-wrap">
      <div class="sheets-modal-ring">
        <svg viewBox="0 0 40 40">
          <circle cx="20" cy="20" r="17" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="3"/>
          <circle id="sheets-ring-circle" cx="20" cy="20" r="17" fill="none"
            stroke="#34C759" stroke-width="3"
            stroke-dasharray="106.8" stroke-dashoffset="0"
            stroke-linecap="round" transform="rotate(-90 20 20)"/>
        </svg>
        <span id="sheets-countdown">3</span>
      </div>
      <p class="sheets-modal-timer-label">Открываем Google Sheets...</p>
    </div>
    <button class="sheets-modal-btn" onclick="doOpenSheets()">
      Открыть сейчас
    </button>
    <button class="sheets-modal-cancel" onclick="closeSheetsModal()">Отмена</button>
  </div>
</div>

<script>
// ── Raw data ──
const RAW_DATA = {json.dumps(posts, ensure_ascii=False)};

// ── Toast ──
function showToast(msg) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}}

// ── Check All ──
document.getElementById('check-all').addEventListener('change', function() {{
  const visible = document.querySelectorAll('.table-row:not(.hidden) .row-check');
  visible.forEach(cb => cb.checked = this.checked);
}});

function selectAll() {{
  const all = document.getElementById('check-all');
  all.checked = true;
  all.dispatchEvent(new Event('change'));
  showToast('✅ Все строки выбраны');
}}

// ── Filtering ──
let currentFilter = 'all';
function filterType(type) {{
  currentFilter = type;
  document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
  document.querySelector('[data-filter="' + type + '"]').classList.add('active');

  let visible = 0;
  document.querySelectorAll('.table-row').forEach(row => {{
    if (type === 'all' || row.dataset.type === type) {{
      row.classList.remove('hidden');
      visible++;
    }} else {{
      row.classList.add('hidden');
    }}
  }});
  document.getElementById('visible-count').textContent = visible;
}}

// ── CSV Export ──
function getSelectedData() {{
  const checked = document.querySelectorAll('.table-row:not(.hidden) .row-check:checked');
  const indices = Array.from(checked).map(cb => parseInt(cb.dataset.idx));
  if (indices.length > 0) return indices.map(i => RAW_DATA[i]);
  // If none selected, export all visible
  const visibleRows = document.querySelectorAll('.table-row:not(.hidden)');
  return Array.from(visibleRows).map(r => RAW_DATA[parseInt(r.dataset.idx)]);
}}

function buildCSVRows(selected) {{
  const headers = ['Тип','Ссылка','Автор','Текст','Лайки','Комменты','Просмотры','Лайки/ч','Комменты/ч','Просмотры/ч','Индекс Виральности','Возраст (ч)','Источник'];
  const csvRows = [headers.join(',')];
  selected.forEach(p => {{
    const h = (p.hours_ago && p.hours_ago > 0) ? p.hours_ago : 999;
    const row = [
      p.post_type || '',
      p.url || '',
      '@' + (p.owner_username || ''),
      '"' + (p.caption_text || '').replace(/"/g, '""').substring(0, 200) + '"',
      p.likes || 0,
      p.comments || 0,
      p.views || 0,
      Math.round((p.likes || 0) / h),
      Math.round((p.comments || 0) / h),
      p.is_reel ? Math.round((p.views || 0) / h) : 0,
      p.velocity_score || 0,
      p.hours_ago || '',
      p.source || ''
    ];
    csvRows.push(row.join(','));
  }});
  return csvRows;
}}

function exportCSV() {{
  const selected = getSelectedData();
  const csvRows = buildCSVRows(selected);
  const blob = new Blob(['\\uFEFF' + csvRows.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'viral_posts_' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
  URL.revokeObjectURL(url);
  showToast('📥 CSV скачан — ' + selected.length + ' строк');
}}

// ── Google Sheets Export ──
let _sheetsCountdownTimer = null;
let _sheetsTsv = '';

function exportToSheets() {{
  const selected = getSelectedData();
  const headers = ['Тип','Ссылка','Автор','Текст','Лайки','Комменты','Просмотры','Лайки/ч','Комменты/ч','Просмотры/ч','Индекс','Возраст'];
  const tsvRows = [headers.join('\t')];
  selected.forEach(p => {{
    const h = (p.hours_ago && p.hours_ago > 0) ? p.hours_ago : 999;
    const row = [
      p.post_type || '',
      p.url || '',
      '@' + (p.owner_username || ''),
      (p.caption_text || '').replace(/\t/g, ' ').replace(/\n/g, ' ').substring(0, 150),
      p.likes || 0,
      p.comments || 0,
      p.views || 0,
      Math.round((p.likes || 0) / h),
      Math.round((p.comments || 0) / h),
      p.is_reel ? Math.round((p.views || 0) / h) : 0,
      p.velocity_score || 0,
      p.hours_ago || ''
    ];
    tsvRows.push(row.join('\t'));
  }});
  _sheetsTsv = tsvRows.join('\n');

  // Copy to clipboard
  const copyAndShow = () => {{
    document.getElementById('sheets-row-count').textContent =
      selected.length + ' строк • ' + headers.length + ' колонок готовы к вставке';
    document.getElementById('sheets-modal').classList.add('open');
    startSheetsCountdown();
  }};

  navigator.clipboard.writeText(_sheetsTsv)
    .then(copyAndShow)
    .catch(() => {{
      // Fallback for non-secure context
      const ta = document.createElement('textarea');
      ta.value = _sheetsTsv;
      ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.focus(); ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      copyAndShow();
    }});
}}

function startSheetsCountdown() {{
  clearInterval(_sheetsCountdownTimer);
  let count = 3;
  const numEl = document.getElementById('sheets-countdown');
  const circleEl = document.getElementById('sheets-ring-circle');
  const circumference = 106.8;

  numEl.textContent = count;
  circleEl.style.strokeDashoffset = '0';

  _sheetsCountdownTimer = setInterval(() => {{
    count--;
    numEl.textContent = count;
    // Animate ring
    const progress = (3 - count) / 3;
    circleEl.style.transition = 'stroke-dashoffset 0.9s linear';
    circleEl.style.strokeDashoffset = String(circumference * progress);

    if (count <= 0) {{
      clearInterval(_sheetsCountdownTimer);
      doOpenSheets();
    }}
  }}, 1000);
}}

function doOpenSheets() {{
  clearInterval(_sheetsCountdownTimer);
  closeSheetsModal();
  window.open('https://docs.google.com/spreadsheets/create', '_blank');
  showToast('📋 Открываем Google Sheets — нажмите Ctrl+V');
}}

function closeSheetsModal() {{
  clearInterval(_sheetsCountdownTimer);
  document.getElementById('sheets-modal').classList.remove('open');
}}

// ── Column Sorting ──
let sortState = {{}};
function sortTable(colIdx) {{
  const table = document.getElementById('results-table');
  const headers = table.querySelectorAll('th');
  const tbody = document.getElementById('table-body');
  const rows = Array.from(tbody.querySelectorAll('tr'));

  // Toggle direction
  const dir = sortState[colIdx] === 'asc' ? 'desc' : 'asc';
  sortState = {{}};
  sortState[colIdx] = dir;

  // Clear sort indicators
  headers.forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
  headers[colIdx].classList.add(dir === 'asc' ? 'sorted-asc' : 'sorted-desc');

  rows.sort((a, b) => {{
    let aVal = a.cells[colIdx]?.innerText?.trim() || '';
    let bVal = b.cells[colIdx]?.innerText?.trim() || '';

    // Remove units like 'ч'
    aVal = aVal.replace(/ч$/, '').trim();
    bVal = bVal.replace(/ч$/, '').trim();

    const aNum = parseFloat(aVal.replace(/[,\\s]/g, ''));
    const bNum = parseFloat(bVal.replace(/[,\\s]/g, ''));
    if (!isNaN(aNum) && !isNaN(bNum)) {{
      return dir === 'asc' ? aNum - bNum : bNum - aNum;
    }}
    return dir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
  }});

  rows.forEach(r => tbody.appendChild(r));
}}

// ── Settings Panel ──
function toggleSettings() {{
  const panel = document.getElementById('settings-panel');
  const btn = document.getElementById('settings-btn');
  panel.classList.toggle('open');
  btn.classList.toggle('open');
}}

function getFilterVal(id) {{
  const v = parseInt(document.getElementById(id).value);
  return isNaN(v) ? 0 : v;
}}

function applyFilters() {{
  const minLikes = getFilterVal('f-min-likes');
  const maxLikes = getFilterVal('f-max-likes');
  const minComments = getFilterVal('f-min-comments');
  const maxComments = getFilterVal('f-max-comments');
  const minViews = getFilterVal('f-min-views');
  const maxViews = getFilterVal('f-max-views');
  const minFollowers = getFilterVal('f-min-followers');
  const maxFollowers = getFilterVal('f-max-followers');
  const minVelocity = getFilterVal('f-min-velocity');
  const maxVelocity = getFilterVal('f-max-velocity');
  const excludeZero = document.getElementById('f-exclude-zero').checked;

  let visible = 0;
  document.querySelectorAll('.table-row').forEach(row => {{
    const idx = parseInt(row.dataset.idx);
    const p = RAW_DATA[idx];
    let show = true;

    // Type filter
    if (currentFilter !== 'all' && row.dataset.type !== currentFilter) show = false;

    // Metric filters
    if (show && minLikes > 0 && (p.likes || 0) < minLikes) show = false;
    if (show && maxLikes > 0 && (p.likes || 0) > maxLikes) show = false;
    if (show && minComments > 0 && (p.comments || 0) < minComments) show = false;
    if (show && maxComments > 0 && (p.comments || 0) > maxComments) show = false;
    if (show && minViews > 0 && (p.views || 0) < minViews) show = false;
    if (show && maxViews > 0 && (p.views || 0) > maxViews) show = false;
    if (show && minFollowers > 0 && (p.owner_followers || 0) < minFollowers) show = false;
    if (show && maxFollowers > 0 && (p.owner_followers || 0) > maxFollowers) show = false;
    if (show && minVelocity > 0 && (p.velocity_score || 0) < minVelocity) show = false;
    if (show && maxVelocity > 0 && (p.velocity_score || 0) > maxVelocity) show = false;
    if (show && excludeZero && (p.likes || 0) === 0 && (p.comments || 0) === 0) show = false;

    if (show) {{
      row.classList.remove('hidden');
      visible++;
    }} else {{
      row.classList.add('hidden');
    }}
  }});
  document.getElementById('visible-count').textContent = visible;
  showToast('🔍 Фильтры применены — ' + visible + ' постов');
}}

function resetFilters() {{
  ['f-min-likes','f-max-likes','f-min-comments','f-max-comments',
   'f-min-views','f-max-views','f-min-followers','f-max-followers',
   'f-min-velocity','f-max-velocity'].forEach(id => {{
    document.getElementById(id).value = '';
  }});
  document.getElementById('f-exclude-zero').checked = false;
  filterType(currentFilter);
  showToast('♻️ Фильтры сброшены');
}}
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page_html)

    print(f"[ui_generator] HTML report saved: {output_path}")

"""Replace all ico_xxx.png <img> tags in headers with inline SVG icons."""
path = r'C:\Users\chenm\Desktop\program\LC_project\src\web\index.html'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

icon_svgs = {
    'ico_sprout.png':  '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 22v-8"/><path d="M12 14c-4.5 0-8-3.5-8-8V3h3c5 0 8 3.5 8 8"/><path d="M12 14c4.5 0 8-3.5 8-8V3h-3c-2.4 0-4.4.8-5.8 2.2"/></svg>',
    'ico_document.png':'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M10 13h4"/><path d="M10 17h2"/></svg>',
    'ico_pin.png':     '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>',
    'ico_camera.png':  '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3Z"/><circle cx="12" cy="13" r="3"/></svg>',
    'ico_food.png':    '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Z"/><path d="M12 6v12M8 10h8"/><circle cx="12" cy="16" r="2"/></svg>',
    'ico_lightning.png':'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M13 2 3 14h8l-1 8 11-13h-8Z"/></svg>',
    'ico_trophy.png':  '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 21h8"/><path d="M12 17v4"/><path d="M7 4h10v4a5 5 0 0 1-10 0V4Z"/><path d="M5 5H3v2a4 4 0 0 0 4 4"/><path d="M19 5h2v2a4 4 0 0 1-4 4"/></svg>',
    'ico_gift.png':    '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12v10H4V12"/><path d="M2 7h20v5H2Z"/><path d="M12 22V7"/><path d="M12 7H7.5a2.5 2.5 0 1 1 2.2-3.7L12 7Z"/><path d="M12 7h4.5a2.5 2.5 0 1 0-2.2-3.7L12 7Z"/></svg>',
    'ico_tracking.png':'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h4l3-8 4 16 3-8h4"/></svg>',
    'ico_gallery.png': '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>',
    'ico_medal.png':   '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="7"/><path d="M8.2 14.2 7 22l5-3 5 3-1.2-7.8"/></svg>',
    'ico_shop.png':    '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m3 9 1.8-5h14.4L21 9"/><path d="M3 9h18v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M10 14h4v4h-4Z"/></svg>',
    'ico_book.png':    '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>',
    'ico_lightbulb.png':'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M15.1 15.1a5 5 0 1 0-6.2 0L10 16.5v1h4v-1Z"/></svg>',
    'ico_source.png':  '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/><path d="M7 11 12 6 17 11"/><path d="M12 6v11"/></svg>',
    'ico_check.png':   '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>',
    'ico_clock.png':   '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
    'ico_recycle.png': '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 19-3-5 3-5"/><path d="M4 14h7"/><path d="m17 5 3 5-3 5"/><path d="M20 10h-7"/><path d="m8 5 4-3 4 3"/></svg>',
    'ico_box.png':     '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m3 7 9 5 9-5"/><path d="m3 7 9-5 9 5v10l-9 5-9-5Z"/><path d="M12 12v10"/></svg>',
}

for ico_name, svg in icon_svgs.items():
    # Pattern: <img src="/checkin/ICO_NAME" style="..." alt="">
    old = '<img src="/checkin/' + ico_name + '"'
    # Find all occurrences and count
    count = c.count(old)
    if count > 0:
        # Replace the <img> tag with the SVG
        # The img tag format is: <img src="/checkin/ico_xxx.png" style="width:1.5em;height:1.5em;vertical-align:-.18em;display:inline-block;" alt="">
        # or variations with different style strings
        import re
        # Match the full img tag
        pattern = r'<img\s+src="/checkin/' + re.escape(ico_name) + r'"[^>]*>'
        c = re.sub(pattern, svg, c)
        print(f'Replaced {count}x {ico_name}')

# Also handle the h2 CSS no longer needed
# Remove the h2 img[src*="ico_"] rule since we no longer use ico_ images inline
c = c.replace(
    '  /* All inline icon images: clean, no bg */\n  h2 img[src*="ico_"], h3 img[src*="ico_"], strong img[src*="ico_"] {\n    width: 1.5em !important; height: 1.5em !important;\n    vertical-align: -.18em; display: inline-block;\n  }',
    '  /* inline SVG icons */\n  h2 svg.icon, h3 svg.icon, strong svg.icon { width: 1.5em; height: 1.5em; vertical-align: -.18em; }'
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)
print('\nDone! All header/strong icons converted to inline SVG.')

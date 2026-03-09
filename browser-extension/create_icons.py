#!/usr/bin/env python3
"""Generate Ghibli-inspired treasure chest icons for the browser extension and favicon"""

from PIL import Image, ImageDraw
import os

def draw_treasure_chest(draw, size):
    """Draw a Ghibli-inspired treasure chest"""
    # Scale factor based on 64px base
    s = size / 64

    # Colors - warm, earthy Ghibli palette
    wood_dark = (107, 68, 35)      # #6B4423
    wood_mid = (139, 90, 43)       # #8B5A2B
    wood_light = (160, 82, 45)     # #A0522D
    metal_dark = (184, 134, 11)    # #B8860B
    metal_light = (218, 165, 32)   # #DAA520
    gold_glow = (255, 215, 0)      # #FFD700
    gold_bright = (255, 236, 139)  # #FFEC8B
    sparkle = (255, 250, 205)      # #FFFACD

    # Shadow
    shadow_box = [8*s, 54*s, 56*s, 62*s]
    draw.ellipse(shadow_box, fill=(93, 78, 55, 77))

    # Chest base (body)
    draw.rounded_rectangle([8*s, 32*s, 56*s, 56*s], radius=3*s, fill=wood_mid)
    draw.rounded_rectangle([10*s, 34*s, 54*s, 54*s], radius=2*s, fill=wood_light)

    # Wood grain lines
    for y in [38, 44, 50]:
        draw.line([(12*s, y*s), (52*s, y*s)], fill=(139, 69, 19, 102), width=max(1, int(s)))

    # Lid background
    points_lid_outer = [
        (8*s, 32*s), (8*s, 24*s), (32*s, 16*s), (56*s, 24*s), (56*s, 32*s)
    ]
    draw.polygon(points_lid_outer, fill=wood_dark)

    # Lid front
    points_lid_inner = [
        (10*s, 31*s), (10*s, 24*s), (32*s, 18*s), (54*s, 24*s), (54*s, 31*s)
    ]
    draw.polygon(points_lid_inner, fill=wood_mid)

    # Golden glow from inside (the magic!)
    glow_points_outer = [
        (14*s, 32*s), (14*s, 26*s), (32*s, 23*s), (50*s, 26*s), (50*s, 32*s)
    ]
    draw.polygon(glow_points_outer, fill=(*gold_glow, 153))

    glow_points_inner = [
        (18*s, 32*s), (18*s, 28*s), (32*s, 25*s), (46*s, 28*s), (46*s, 32*s)
    ]
    draw.polygon(glow_points_inner, fill=(*gold_bright, 204))

    # Sparkles
    sparkle_positions = [
        (24, 28, 2), (38, 26, 1.5), (32, 24, 2.5), (42, 29, 1), (20, 30, 1)
    ]
    for x, y, r in sparkle_positions:
        if size >= 32:  # Only draw sparkles on larger icons
            box = [(x-r)*s, (y-r)*s, (x+r)*s, (y+r)*s]
            draw.ellipse(box, fill=(*sparkle, 230))

    # Metal bands
    draw.rectangle([8*s, 31*s, 56*s, 34*s], fill=(205, 133, 63))
    draw.rectangle([8*s, 52*s, 56*s, 55*s], fill=(205, 133, 63))

    # Metal studs
    stud_positions = [(14, 32.5), (50, 32.5), (14, 53.5), (50, 53.5)]
    for x, y in stud_positions:
        if size >= 32:  # Only draw studs on larger icons
            box = [(x-1.5)*s, (y-1.5)*s, (x+1.5)*s, (y+1.5)*s]
            draw.ellipse(box, fill=metal_light)

    # Lock/clasp
    draw.rounded_rectangle([28*s, 30*s, 36*s, 38*s], radius=1*s, fill=metal_light)
    draw.rounded_rectangle([29*s, 31*s, 35*s, 37*s], radius=1*s, fill=metal_dark)

    if size >= 32:
        # Lock keyhole
        draw.ellipse([30*s, 32*s, 34*s, 36*s], fill=(139, 105, 20))
        draw.rectangle([31*s, 34*s, 33*s, 37*s], fill=(139, 105, 20))

def create_icon(size, filename):
    """Create a treasure chest icon at the specified size"""
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, 'RGBA')

    draw_treasure_chest(draw, size)

    # Save the image
    img.save(filename, 'PNG')
    print(f"Created {filename}")
    return img

def create_favicon_ico(images, filename):
    """Create a multi-resolution .ico file"""
    # ICO files can contain multiple sizes
    # Save the largest image with the smaller ones embedded
    images[0].save(
        filename,
        format='ICO',
        sizes=[(img.width, img.height) for img in images]
    )
    print(f"Created {filename}")

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Create icons directory if it doesn't exist
    icons_dir = os.path.join(script_dir, 'icons')
    os.makedirs(icons_dir, exist_ok=True)

    # Create browser extension icons
    icon_sizes = [16, 48, 128]
    images = []
    for size in icon_sizes:
        img = create_icon(size, os.path.join(icons_dir, f'icon{size}.png'))
        images.append(img)

    # Also create 32px for favicon
    img32 = create_icon(32, os.path.join(icons_dir, 'icon32.png'))
    img64 = create_icon(64, os.path.join(icons_dir, 'icon64.png'))

    # Create favicon.ico with multiple sizes (16, 32, 48)
    favicon_images = [
        Image.open(os.path.join(icons_dir, 'icon48.png')),
        Image.open(os.path.join(icons_dir, 'icon32.png')),
        Image.open(os.path.join(icons_dir, 'icon16.png'))
    ]
    create_favicon_ico(favicon_images, os.path.join(icons_dir, 'favicon.ico'))

    # Copy favicon to static folder for web app
    static_dir = os.path.join(script_dir, '..', 'static')
    os.makedirs(static_dir, exist_ok=True)
    import shutil
    shutil.copy(
        os.path.join(icons_dir, 'favicon.ico'),
        os.path.join(static_dir, 'favicon.ico')
    )
    shutil.copy(
        os.path.join(icons_dir, 'icon32.png'),
        os.path.join(static_dir, 'favicon.png')
    )
    print(f"\nCopied favicon to {static_dir}")

    print("\nAll icons created successfully!")
    print("Browser extension icons: browser-extension/icons/")
    print("Web app favicon: static/favicon.ico and static/favicon.png")

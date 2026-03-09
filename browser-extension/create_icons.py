#!/usr/bin/env python3
"""Generate placeholder icons for the browser extension"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, filename):
    """Create a simple icon with Quest Tracker theme"""
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw gradient background circle
    # Using extension colors: rgb(102, 126, 234) to rgb(118, 75, 162)
    for i in range(size):
        for j in range(size):
            # Calculate distance from center
            dx = i - size/2
            dy = j - size/2
            distance = (dx*dx + dy*dy) ** 0.5

            if distance < size/2 - 2:
                # Gradient from top-left to bottom-right
                t = (i + j) / (2 * size)
                r = int(102 + (118 - 102) * t)
                g = int(126 + (75 - 126) * t)
                b = int(234 + (162 - 234) * t)
                img.putpixel((i, j), (r, g, b, 255))

    # Draw Q letter in white
    try:
        # Try to use a nice font if available
        font_size = int(size * 0.6)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        # Fallback to default font
        font = ImageFont.load_default()

    # Draw "Q" in the center
    text = "Q"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((size - text_width) // 2, (size - text_height) // 2 - int(size * 0.05))

    draw.text(position, text, fill=(255, 255, 255, 255), font=font)

    # Save the image
    img.save(filename, 'PNG')
    print(f"Created {filename}")

if __name__ == '__main__':
    # Create icons directory if it doesn't exist
    os.makedirs('icons', exist_ok=True)

    # Create icons at different sizes
    create_icon(16, 'icons/icon16.png')
    create_icon(48, 'icons/icon48.png')
    create_icon(128, 'icons/icon128.png')

    print("\nAll icons created successfully!")

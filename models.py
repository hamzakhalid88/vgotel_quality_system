from PIL import Image

# Open high-res PNG (make sure it's at least 512x512)
img = Image.open("icon.png")

# Standard Windows icon sizes
sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

# Save as ICO with all sizes
img.save("icon.ico", format="ICO", sizes=sizes)

print("✅ Professional multi-size icon.ico created")
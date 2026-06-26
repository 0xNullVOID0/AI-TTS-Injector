import time

import cv2

from config_handler import config
from profiler import profiler


# Downscales images for more accurate OCR due to font sizes and such
@profiler.time_profile
def downscale(image):
    # image = image.copy()
    height, width = image.shape[:2]

    # set max safe textbox height threshold
    # target_height = 100
    target_height = 30

    # only downscale above threshold
    if height >= target_height:
        # calc scale and new size
        scale_ratio = target_height / height  # TODO bigger downscale
        new_width = int(width * scale_ratio)
        new_height = int(target_height)

        if config.debug:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            cv2.imwrite(f"screenshots/NORMAL_{timestamp}.png", image)

        print(f"Downscaling crop from {height}px to {new_height}px")

        # INTER_AREA prevents pixel skipping and keeps thin font lines crisp
        image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # TODO just edit renpy font size? and or hook straight into text stream from it

        if config.debug:
            cv2.imwrite(f"screenshots/DOWNSCALE_{timestamp}.png", image)


    # convert to ocr format
    # img_rgb = image[:, :, :3][:, :, ::-1]

    return image

# Strip all color to remove image noise and conflicting backgrounds
@profiler.time_profile
def convert_to_black_and_white(image):
    # image = image.copy()
    # convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # TODO test/check aliasing?

    # convert to pure black and white
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # convert black and white back to RGB for ocr
    img_rgb = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)

    # tag image as rgb
    # img_rgb.is_rgb = True
    # setattr(img_rgb, 'is_rgb', True)

    return img_rgb

@profiler.time_profile
def process_image(image):
    image = downscale(image)
    # image = convert_to_black_and_white(image)
    return image
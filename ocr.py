import time

import cv2
import easyocr

from config_handler import config
from image_processor import process_image
from kokoro_tts import send
from mkb_handler import mkb
from profiler import profiler
from text_processor import process_ocr

# Verify cuda stuff for ocr debugging
# print(f"CUDA status: {torch.cuda.is_available()}")
# print(f"DEBUG: Torch sees GPU: {torch.cuda.is_available()}")
# print(f"DEBUG: Torch device name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
# print(f"DEBUG: Python executable: {os.sys.executable}")
reader = easyocr.Reader(['en'], gpu=True)
ocr_counter = 0

# TODO resize ocr image and other ocr pre and or post processing for more accurate scans


@profiler.time_profile
def start_processing(window):
    image = None
    voice = config.default_voice

    # only capture window if targeted window
    if window and window.is_target_window():
        image = window.capture()
    else:
        print("Not the target window")

    if image is not None and image.size > 0:
        width, height = window.get_dimensions()

        # TODO only downscale when neccesary, a check? manually set per program?
        # TODO adjust window area selectors if downscaling,
        # image = downscale(image, width, height)


        # get name and text from window capture, returns 0,0 if no name and text selections were set
        name, text = grab_name_and_text_selections(image)
        text = process_ocr(text)

        # convert to ocr format
        image = image[:, :, :3][:, :, ::-1]

        # full window scan if name and text selections not set
        if (name, text) == (0, 0):
            print(f"Full window capture")
            # image = downscale(image, width, height)
            text = run_ocr(image)
            print(f'text: {text}')
        else:
            voice = get_voice_for_name(name)

        # prevent duplicate requests
        if text and text != config.last_text:
            print(f"TEXT SELECTED: {text}")
            config.last_text = text
            config.duplicate = False
            # sends and plays audio using local kokoro
            print("SENDING ")
            send(text.lower(), voice)
        else:
            print(f"DUPLICATE TEXT, SKIPPING")
            config.duplicate = True
            # TODO allow cycling between selections, as in first scan is selection 1, scan 2 selec 2 and loop, repeat
    else:
        print(f"No screenshot")


# Get text from passed image
@profiler.time_profile
def run_ocr(image, is_raw_array=False):

    # TODO detect img_array?
    # convert screenshot to easyOCR compatible format
    # if hasattr(image, 'is_rgb') and not image.is_rgb:
    #     image = image[:, :, :3][:, :, ::-1]


    # TODO change vertical reading per program, set that setting per program, others are way more vertical text
    # set ocr with larger margin of error to prevent scanned text order being messed up by letters like q or l
    result = reader.readtext(image, paragraph=True, x_ths=1000.0,
                           y_ths=0.1 #  prevents it from grouping across different vertical lines
    )
    # result = ocr.readtext(img_rgb)

    config.ocr_counter += 1 # TODO also do a calculation with -duplicate text so it stays accurate with audio_played
    print(f"ocr count: {config.ocr_counter}")

    all_text = ""

    # get all text of scanned image
    for (bbox, text) in result:
        all_text += text + " "

    return all_text

    # TODO finish
    fast = False
    # fast = True
    if fast:
        update_interval(calculate_interval(all_text))

        # print(all_text)
        return all_text

@profiler.time_profile
def grab_name_and_text_selections(screenshot):
    # if these 2 selections have been set manually with keybinds or from the config then only scan and read those portions
    if config.name_selector and config.text_selector:
        print("name and text SELECTED")
        ns = config.name_selector
        name_crop = screenshot[
            ns["top"]: ns["top"] + ns["height"],
            ns["left"]: ns["left"] + ns["width"]
        ]

        raw_name = run_ocr(name_crop, is_raw_array=True)
        # print(f'name selector: {name_selector}')
        # print(f'name_crop: {name_crop}')

        # remove brackets, common artifact characters, and all surrounding whitespace
        name = raw_name.replace('[', '').replace(']', '').strip() if raw_name else ""

        print(f'name: {name}')

        ts = config.text_selector
        text_crop = screenshot[
            ts["top"]: ts["top"] + ts["height"],
            ts["left"]: ts["left"] + ts["width"]
        ]

        # text_crop = downscale(text_crop)
        text_crop = process_image(text_crop)

        text = run_ocr(text_crop, is_raw_array=True)
        print(f'text: {text}')

        # save screenshots for debugging
        if config.debug or not config.duplicate:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            cv2.imwrite(f"screenshots/debug_name_crop_{timestamp}.png", name_crop)
            cv2.imwrite(f"screenshots/debug_text_crop_{timestamp}.png", text_crop)

        return name, text
    else:
        print("NO name and text selected")
        return 0, 0 # return 0 if name and text selectors not set instead of None in case they are set but still return no value/text


@staticmethod
def get_voice_for_name(name):
    clean_name = name.strip().lower()
    print("Getting voice for:", clean_name)

    for character, voice in config.voice_map.items():
        if character.lower() == clean_name:
            print(f"Set {character}'s voice: {voice}")
            return voice

        #TODO just use VOICE_MAP.get(clean_name, default_voice)?

    return config.default_voice

mkb.set_autoplay_hook(start_processing)

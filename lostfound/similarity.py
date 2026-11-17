"""
Campus Lost & Found - Image Similarity & Matching Engine
Uses Computer Vision (Color Histograms, Perceptual Gradient Hash, and Edge Orientation Distributions)
to compare photographs of lost and found items.
"""

import os
import math
import numpy as np
from PIL import Image, ImageOps


def _load_image(img_source):
    """
    Safely load an image from a path, file-like object, or Django FieldFile.
    Returns a PIL Image in RGB format.
    """
    if img_source is None:
        return None
    try:
        # If it's a Django FieldFile or UploadedFile, rewind and open
        if hasattr(img_source, 'open'):
            try:
                img_source.open('rb')
            except Exception:
                pass
        if hasattr(img_source, 'seek'):
            img_source.seek(0)
            img = Image.open(img_source)
        elif isinstance(img_source, (str, os.PathLike)):
            if not os.path.exists(img_source):
                return None
            img = Image.open(img_source)
        elif isinstance(img_source, Image.Image):
            img = img_source
        else:
            img = Image.open(img_source)

        # Handle EXIF orientation if present
        img = ImageOps.exif_transpose(img)
        return img.convert('RGB')
    except Exception as exc:
        print(f"[similarity] Error loading image: {exc}")
        return None


def _color_histogram_similarity(img1, img2, bins=(8, 8, 8)):
    """
    Calculate 3D RGB color histogram intersection similarity.
    Captures color distribution invariant to minor spatial layout.
    Returns float in range [0.0, 1.0].
    """
    im1 = img1.resize((128, 128), Image.Resampling.BILINEAR)
    im2 = img2.resize((128, 128), Image.Resampling.BILINEAR)

    arr1 = np.array(im1, dtype=np.float32).reshape(-1, 3)
    arr2 = np.array(im2, dtype=np.float32).reshape(-1, 3)

    hist1, _ = np.histogramdd(arr1, bins=bins, range=[(0, 256), (0, 256), (0, 256)])
    hist2, _ = np.histogramdd(arr2, bins=bins, range=[(0, 256), (0, 256), (0, 256)])

    s1 = hist1.sum()
    s2 = hist2.sum()
    if s1 == 0 or s2 == 0:
        return 0.0

    hist1 = (hist1 / s1).flatten()
    hist2 = (hist2 / s2).flatten()

    # Histogram intersection
    intersection = float(np.minimum(hist1, hist2).sum())
    return max(0.0, min(1.0, intersection))


def _dhash(image, hash_size=8):
    """
    Calculate difference hash (dHash) to capture structural luminance gradients.
    """
    gray = image.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = np.array(gray, dtype=np.int32)
    diff = pixels[:, 1:] > pixels[:, :-1]
    return diff.flatten()


def _hash_similarity(img1, img2):
    """
    Compute perceptual difference hash similarity using normalized Hamming distance.
    Returns float in range [0.0, 1.0].
    """
    h1 = _dhash(img1, hash_size=8)
    h2 = _dhash(img2, hash_size=8)
    hamming_dist = np.count_nonzero(h1 != h2)
    similarity = 1.0 - (float(hamming_dist) / float(len(h1)))
    return max(0.0, min(1.0, similarity))


def _edge_orientation_similarity(img1, img2, size=64, bins=16):
    """
    Compute orientation histogram of gradients (simplified HOG).
    Captures object contours and structural shape regardless of color.
    Returns float in range [0.0, 1.0].
    """
    def get_hist(im):
        gray = np.array(im.convert('L').resize((size, size), Image.Resampling.BILINEAR), dtype=np.float32)
        gy, gx = np.gradient(gray)
        mag = np.hypot(gx, gy)
        ang = (np.arctan2(gy, gx) + np.pi) % np.pi
        ang_hist, _ = np.histogram(ang, bins=bins, range=(0, np.pi), weights=mag)
        total = ang_hist.sum()
        if total == 0:
            return np.ones(bins, dtype=np.float32) / bins
        return ang_hist / total

    h1 = get_hist(img1)
    h2 = get_hist(img2)
    sim = float(np.minimum(h1, h2).sum())
    return max(0.0, min(1.0, sim))


def calculate_image_similarity(lost_image_source, found_image_source):
    """
    Compare uploaded lost item photograph with the found item reference photograph.

    Returns:
        dict containing:
            - score (float or None): 0.0 - 100.0 similarity percentage
            - result_label (str): E.g. "High Visual Similarity", "Moderate Match", etc.
            - result_badge (str): CSS class for badge ('match-high', 'match-moderate', 'match-low', 'match-na')
            - explanation (str): Professional explanation
            - breakdown (dict): Component scores for color, structure, and shape
            - has_reference (bool): Whether a found reference photo was available
    """
    if not found_image_source:
        return {
            'score': None,
            'result_label': "No Reference Image Available",
            'result_badge': "match-na",
            'explanation': "The selected found item does not have a reference photograph on file. Your claim will be manually verified by campus administrators using your item description.",
            'breakdown': {'color': 0, 'structure': 0, 'shape': 0},
            'has_reference': False,
        }

    img_lost = _load_image(lost_image_source)
    img_found = _load_image(found_image_source)

    if img_lost is None or img_found is None:
        missing = "lost item" if img_lost is None else "found item"
        return {
            'score': None,
            'result_label': "Image Processing Unavailable",
            'result_badge': "match-na",
            'explanation': f"Could not decode the {missing} image. Please ensure a valid JPG, PNG, or WEBP file is uploaded.",
            'breakdown': {'color': 0, 'structure': 0, 'shape': 0},
            'has_reference': img_found is not None,
        }

    # Real Computer Vision feature extraction
    color_sim = _color_histogram_similarity(img_lost, img_found)
    structure_sim = _hash_similarity(img_lost, img_found)
    shape_sim = _edge_orientation_similarity(img_lost, img_found)

    # Weighted composite score: 40% color, 30% perceptual structure, 30% edge shape
    raw_composite = (color_sim * 0.40) + (structure_sim * 0.30) + (shape_sim * 0.30)
    score = round(max(0.0, min(100.0, raw_composite * 100.0)), 1)

    color_pct = round(color_sim * 100.0, 1)
    structure_pct = round(structure_sim * 100.0, 1)
    shape_pct = round(shape_sim * 100.0, 1)

    if score >= 75.0:
        result_label = "High Visual Similarity"
        result_badge = "match-high"
        explanation = (
            f"Images appear visually similar with a strong {score}% correlation. "
            f"Color tones ({color_pct}%) and structural contours ({shape_pct}%) align well. "
            "Please note: Visual similarity serves as supporting evidence only. "
            "Final verification will be confirmed by campus administration."
        )
    elif score >= 50.0:
        result_label = "Moderate Visual Similarity"
        result_badge = "match-moderate"
        explanation = (
            f"Images show moderate visual similarity ({score}%). "
            "Shared color palette or general outline detected, though noticeable differences exist in surface details. "
            "Administrators will cross-check your written description."
        )
    else:
        result_label = "Low Visual Similarity"
        result_badge = "match-low"
        explanation = (
            f"Images exhibit low visual similarity ({score}%). "
            "Color distributions, shapes, or textures differ significantly. "
            "You may still submit your claim; college administrators will review your detailed description and additional marks manually."
        )

    return {
        'score': score,
        'result_label': result_label,
        'result_badge': result_badge,
        'explanation': explanation,
        'breakdown': {
            'color': color_pct,
            'structure': structure_pct,
            'shape': shape_pct,
        },
        'has_reference': True,
    }

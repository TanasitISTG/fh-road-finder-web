#!/usr/bin/env python
"""Stitch Forza Horizon map screenshots into one larger image."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
JPEG_EXTENSIONS = {".jpg", ".jpeg"}
MIN_MANUAL_ALIGNMENT_INLIERS = 80

STITCHER_STATUS = {
    0: "OK",
    1: "ERR_NEED_MORE_IMGS: not enough overlapping images were found",
    2: "ERR_HOMOGRAPHY_EST_FAIL: could not align image features",
    3: "ERR_CAMERA_PARAMS_ADJUST_FAIL: alignment refinement failed",
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stitch FH6 map screenshots into one larger PNG.")
    parser.add_argument("--input", required=True, type=Path, help="Input folder with screenshots.")
    parser.add_argument("--output", required=True, type=Path, help="Output PNG path.")
    parser.add_argument(
        "--coverage-output",
        type=Path,
        default=None,
        help="Coverage map PNG path. Default: output folder coverage_map.png",
    )
    parser.add_argument("--crop-top", type=int, default=60, help="Pixels to crop from top. Default: 60")
    parser.add_argument("--crop-bottom", type=int, default=55, help="Pixels to crop from bottom. Default: 55")
    parser.add_argument("--crop-left", type=int, default=0, help="Pixels to crop from left. Default: 0")
    parser.add_argument("--crop-right", type=int, default=0, help="Pixels to crop from right. Default: 0")
    parser.add_argument("--no-crop", action="store_true", help="Disable manual UI cropping.")
    parser.add_argument("--mode", choices=["auto", "manual"], default="auto", help="Stitching mode. Default: auto")
    parser.add_argument("--quality", type=int, default=3, help="PNG compression level 0-9. Default: 3")
    return parser


def find_images(input_dir: Path) -> list[Path]:
    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Input folder does not exist: {input_dir}")
    return sorted(path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS)


def load_image(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)


def crop_image(
    image: np.ndarray,
    crop_top: int,
    crop_bottom: int,
    crop_left: int,
    crop_right: int,
    no_crop: bool,
) -> np.ndarray:
    if no_crop:
        cropped = image
    else:
        height, width = image.shape[:2]
        top = max(0, min(crop_top, height - 1))
        bottom = max(top + 1, height - max(0, crop_bottom))
        left = max(0, min(crop_left, width - 1))
        right = max(left + 1, width - max(0, crop_right))
        cropped = image[top:bottom, left:right]
    return trim_black_borders(cropped)


def trim_black_borders(image: np.ndarray) -> np.ndarray:
    # Remove fully black strips that sometimes appear on ultrawide screenshots.
    non_black = np.any(image > 8, axis=2)
    coords = np.argwhere(non_black)
    if coords.size == 0:
        return image
    y1, x1 = coords.min(axis=0)
    y2, x2 = coords.max(axis=0) + 1
    return image[y1:y2, x1:x2]


def normalize_heights(images: list[np.ndarray]) -> list[np.ndarray]:
    if not images:
        return images
    target_height = images[0].shape[0]
    normalized = []
    for image in images:
        height, width = image.shape[:2]
        if height == target_height:
            normalized.append(image)
            continue
        scale = target_height / float(height)
        new_width = max(1, round(width * scale))
        normalized.append(cv2.resize(image, (new_width, target_height), interpolation=cv2.INTER_AREA))
    return normalized


def save_png(path: Path, image_bgr: np.ndarray, quality: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    quality = max(0, min(9, quality))
    ok = cv2.imwrite(str(path), image_bgr, [cv2.IMWRITE_PNG_COMPRESSION, quality])
    if not ok:
        raise OSError(f"Could not save output PNG: {path}")


def build_coverage_map(image_bgr: np.ndarray, coverage_mask: np.ndarray | None = None) -> tuple[np.ndarray, float]:
    """Create a simple gap-visibility map from the stitched result.

    OpenCV's high-level stitcher returns only the final bitmap, not a source
    coverage mask. For v1, treat nearly-black canvas pixels as likely uncovered
    stitcher gaps and draw them with an orange checkerboard.
    """
    image = image_bgr.copy()
    if coverage_mask is None:
        likely_gap = np.all(image <= 8, axis=2)
    else:
        likely_gap = ~coverage_mask.astype(bool)
    total_pixels = likely_gap.size
    covered_pixels = total_pixels - int(np.count_nonzero(likely_gap))
    coverage_percent = (covered_pixels / total_pixels * 100.0) if total_pixels else 0.0

    dimmed = (image.astype(np.float32) * 0.72).astype(np.uint8)
    yy, xx = np.indices(likely_gap.shape)
    checker = ((xx // 24 + yy // 24) % 2).astype(bool)
    orange_a = np.array([0, 90, 255], dtype=np.uint8)  # BGR
    orange_b = np.array([0, 45, 170], dtype=np.uint8)
    coverage = dimmed
    coverage[likely_gap & checker] = orange_a
    coverage[likely_gap & ~checker] = orange_b
    return coverage, coverage_percent


def stitch_images(images: list[np.ndarray]) -> tuple[int, np.ndarray | None]:
    stitcher = cv2.Stitcher.create(cv2.Stitcher_SCANS)
    return stitcher.stitch(images)


def estimate_translation(new_image: np.ndarray, ref_image: np.ndarray) -> tuple[float, float, int] | None:
    max_dim = max(new_image.shape[0], new_image.shape[1], ref_image.shape[0], ref_image.shape[1])
    scale = min(1.0, 900.0 / float(max_dim))
    if scale < 1.0:
        new_small = cv2.resize(new_image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        ref_small = cv2.resize(ref_image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    else:
        new_small = new_image
        ref_small = ref_image

    new_gray = cv2.cvtColor(new_small, cv2.COLOR_BGR2GRAY)
    ref_gray = cv2.cvtColor(ref_small, cv2.COLOR_BGR2GRAY)
    sift = cv2.SIFT_create(nfeatures=3500)
    kp_new, des_new = sift.detectAndCompute(new_gray, None)
    kp_ref, des_ref = sift.detectAndCompute(ref_gray, None)
    if des_new is None or des_ref is None or len(kp_new) < 8 or len(kp_ref) < 8:
        return None

    matcher = cv2.BFMatcher(cv2.NORM_L2)
    matches = matcher.knnMatch(des_new, des_ref, k=2)
    good = []
    for pair in matches:
        if len(pair) != 2:
            continue
        match, neighbor = pair
        if match.distance < 0.72 * neighbor.distance:
            good.append(match)

    if len(good) < 8:
        return None

    src = np.float32([kp_new[match.queryIdx].pt for match in good]).reshape(-1, 1, 2)
    dst = np.float32([kp_ref[match.trainIdx].pt for match in good]).reshape(-1, 1, 2)
    matrix, inlier_mask = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=5.0)
    if matrix is None or inlier_mask is None:
        return None

    inliers = int(inlier_mask.sum())
    if inliers < MIN_MANUAL_ALIGNMENT_INLIERS:
        return None

    a, b = float(matrix[0, 0]), float(matrix[0, 1])
    c, d = float(matrix[1, 0]), float(matrix[1, 1])
    scale_x = (a * a + c * c) ** 0.5
    scale_y = (b * b + d * d) ** 0.5
    if not (0.88 <= scale_x <= 1.12 and 0.88 <= scale_y <= 1.12):
        return None

    tx = float(matrix[0, 2]) / scale
    ty = float(matrix[1, 2]) / scale
    return tx, ty, inliers


def stitch_images_manual(images: list[np.ndarray], names: list[str]) -> tuple[np.ndarray, np.ndarray]:
    positions: list[tuple[float, float]] = [(0.0, 0.0)]
    print("Placing screenshots with manual translation matching...")

    for index in range(1, len(images)):
        best: tuple[int, float, float, int] | None = None
        for ref_index in range(index):
            estimate = estimate_translation(images[index], images[ref_index])
            if estimate is None:
                continue
            tx, ty, inliers = estimate
            ref_x, ref_y = positions[ref_index]
            new_x = ref_x + tx
            new_y = ref_y + ty
            if best is None or inliers > best[3]:
                best = (ref_index, new_x, new_y, inliers)

        if best is None:
            prev_x, prev_y = positions[-1]
            fallback_x = prev_x + images[index - 1].shape[1] + 80
            positions.append((fallback_x, prev_y))
            print(f"  WARNING: Could not align {names[index]}; placing it to the right so it is not dropped.")
        else:
            ref_index, new_x, new_y, inliers = best
            positions.append((new_x, new_y))
            print(f"  {names[index]} matched {names[ref_index]} with {inliers} inliers.")

    rounded_positions = [(round(x), round(y)) for x, y in positions]
    min_x = min(x for x, _ in rounded_positions)
    min_y = min(y for _, y in rounded_positions)
    max_x = max(x + image.shape[1] for (x, _), image in zip(rounded_positions, images))
    max_y = max(y + image.shape[0] for (_, y), image in zip(rounded_positions, images))
    canvas_width = max_x - min_x
    canvas_height = max_y - min_y

    canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
    coverage = np.zeros((canvas_height, canvas_width), dtype=bool)

    for image, (x, y), name in zip(images, rounded_positions, names):
        x1 = x - min_x
        y1 = y - min_y
        x2 = x1 + image.shape[1]
        y2 = y1 + image.shape[0]
        roi = canvas[y1:y2, x1:x2]
        roi_coverage = coverage[y1:y2, x1:x2]
        image_mask = np.any(image > 8, axis=2)

        new_only = image_mask & ~roi_coverage
        overlap = image_mask & roi_coverage
        roi[new_only] = image[new_only]
        if np.any(overlap):
            roi[overlap] = ((roi[overlap].astype(np.uint16) + image[overlap].astype(np.uint16)) // 2).astype(np.uint8)
        roi_coverage[image_mask] = True
        print(f"  Placed {name} at x={x1}, y={y1}")

    return canvas, coverage


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    input_dir = args.input.resolve()
    output_path = args.output.resolve()
    coverage_path = args.coverage_output.resolve() if args.coverage_output else output_path.parent / "coverage_map.png"

    try:
        image_paths = find_images(input_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not image_paths:
        print(f"No supported image files found in: {input_dir}")
        print("Supported: PNG - best, JPG/JPEG, BMP, TIF/TIFF")
        return 1

    jpeg_count = sum(1 for path in image_paths if path.suffix.lower() in JPEG_EXTENSIONS)
    if jpeg_count:
        print(f"WARNING: {jpeg_count} JPEG file(s) detected. PNG usually stitches more cleanly.")

    print("FH6 Map Stitcher")
    print("-----------------------------------------")
    print(f"Input: {input_dir}")
    print(f"Output: {output_path}")
    print(f"Coverage: {coverage_path}")
    print(f"Images: {len(image_paths)}")
    if args.no_crop:
        print("Crop: off")
    else:
        print(
            f"Crop: top {args.crop_top}px, bottom {args.crop_bottom}px, "
            f"left {args.crop_left}px, right {args.crop_right}px"
        )
    print("")

    images: list[np.ndarray] = []
    for index, path in enumerate(image_paths, start=1):
        print(f"[{index}/{len(image_paths)}] Loading {path.name}")
        image = load_image(path)
        image = crop_image(image, args.crop_top, args.crop_bottom, args.crop_left, args.crop_right, args.no_crop)
        if image.shape[0] < 50 or image.shape[1] < 50:
            print(f"ERROR: Image became too small after cropping: {path.name}", file=sys.stderr)
            return 1
        images.append(image)

    images = normalize_heights(images)

    coverage_mask: np.ndarray | None = None
    if len(images) == 1:
        print("Only one image found. Saving cropped copy instead of stitching.")
        result = images[0]
        coverage_mask = np.any(result > 8, axis=2)
    elif args.mode == "manual":
        result, coverage_mask = stitch_images_manual(images, [path.name for path in image_paths])
    else:
        print("Stitching images with OpenCV SCANS mode...")
        status, result = stitch_images(images)
        if status != cv2.Stitcher_OK or result is None:
            print("")
            print(f"ERROR: Stitching failed: {STITCHER_STATUS.get(status, f'Unknown status {status}')}")
            print("Try PNG screenshots, more overlap between screenshots, or --no-crop.")
            return 1

    save_png(output_path, result, args.quality)
    coverage_map, coverage_percent = build_coverage_map(result, coverage_mask)
    save_png(coverage_path, coverage_map, args.quality)
    height, width = result.shape[:2]
    size_mb = output_path.stat().st_size / (1024 * 1024)
    coverage_size_mb = coverage_path.stat().st_size / (1024 * 1024)
    print("")
    print(f"Done. Saved stitched map: {output_path}")
    print(f"Coverage map: {coverage_path}")
    print(f"Dimensions: {width} x {height}")
    print(f"File size: {size_mb:.2f} MB")
    print(f"Coverage map size: {coverage_size_mb:.2f} MB")
    print(f"Approx coverage: {coverage_percent:.1f}% of non-empty stitched canvas")
    print("Orange checkerboard areas in coverage_map.png are likely gaps.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

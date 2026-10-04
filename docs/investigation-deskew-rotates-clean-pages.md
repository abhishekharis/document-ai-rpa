# Investigation: deskew step rotates clean pages 90° and crops the header

**Severity:** ⭐⭐⭐⭐⭐ Critical — silently corrupted every page processed.

## Problem

After the date/tax/total fixes, `sample_invoice.pdf` still extracted vendor as
`INVOICE Invoice Number` — the real vendor `ACME OFFICE SUPPLIES` was missing
from the OCR text entirely, even though it is clearly printed at the top of the
document.

## Root cause

`ImagePreprocessor._deskew()` calls `cv2.minAreaRect` on the largest contour and
converts the returned angle into a rotation. OpenCV ≥ 4.5 changed the reported
angle range to `(0, 90]` — an axis-aligned rectangle returns `90.0`. The code
still used the pre-4.5 convention (`[-90, 0)`), where a straight page reports
`-90` and gets normalized to `0`. Under the new convention it computed a **−90°
correction for a perfectly straight page**, rotating the whole portrait page 90°
inside the same canvas. The top and bottom of the page were cropped off,
removing the vendor header from the image PaddleOCR saw.

## Approach

1. Extracted the PDF's embedded text layer with PyMuPDF — `ACME OFFICE SUPPLIES`
   was present in the document but absent from OCR output, proving the problem
   was in the image pipeline, not extraction.
2. Saved the *preprocessed* image to disk and viewed it: the page was rotated
   90°, with the header clipped.
3. Logged the `minAreaRect` angle: `90.0` for a clean page — the smoking gun.
4. Verified the convention empirically: rendered a rectangle at known skews
   (−30°…+30°) and observed `minAreaRect` return `90 − skew`, confirming
   `angle > 45 → angle − 90` is the correct normalization.

## Fix

Normalize the angle so the applied rotation always lands in (−45°, 45°]:

```python
if angle < 0:            # OpenCV < 4.5 reports [-90, 0)
    angle = -(90 + angle) if angle < -45 else -angle
elif angle > 45:         # OpenCV >= 4.5 reports (0, 90]
    angle -= 90
```

A synthetic-image test proves a straight page is returned unchanged and that
pages skewed ±3°/±7° are corrected to < 0.5° — under the old code the same test
*over-rotated* skewed pages, so the bug hurt every document, not just clean ones.

## Takeaways

- **Library behavior changes across versions.** OpenCV 4.5 changed
  `minAreaRect`'s angle convention; code written against the old one silently
  broke on upgrade. Pin or test against the installed version.
- **View the intermediate artifacts.** One look at the preprocessed image
  explained what pages of log reading couldn't.
- **`except: return unchanged` hides bugs.** The deskew failure was silent
  because the pipeline is designed to degrade gracefully — bad input still
  produced a plausible-looking result downstream.

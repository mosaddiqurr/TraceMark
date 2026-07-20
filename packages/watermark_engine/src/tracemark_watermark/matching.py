"""Constituent visual evidence; no fabricated aggregate confidence score."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

from .fingerprints import ImageFingerprint, fingerprint, hamming_distance


@dataclass(frozen=True, slots=True)
class SimilarityEvidence:
    exact_pixel_match: bool
    phash_distance: int
    dhash_distance: int
    whash_distance: int
    colour_histogram_distance: float
    orb_available: bool
    orb_match_count: int | None
    ransac_inliers: int | None
    homography_valid: bool | None
    diagnostics: dict[str, Any]


class SimilarityEngine(ABC):
    @abstractmethod
    def fingerprint(self, image: Image.Image) -> ImageFingerprint:
        raise NotImplementedError

    @abstractmethod
    def compare(self, reference: Image.Image, candidate: Image.Image) -> SimilarityEvidence:
        raise NotImplementedError


class ClassicalSimilarityEngine(SimilarityEngine):
    def fingerprint(self, image: Image.Image) -> ImageFingerprint:
        return fingerprint(image)

    @staticmethod
    def _local_features(reference: Image.Image, candidate: Image.Image) -> dict[str, Any]:
        try:
            import cv2
        except (ImportError, OSError):
            return {
                "available": False,
                "matches": None,
                "inliers": None,
                "homography_valid": None,
                "reason": "opencv_unavailable",
            }
        left = np.asarray(reference.convert("L"), dtype=np.uint8)
        right = np.asarray(candidate.convert("L"), dtype=np.uint8)
        detector = cv2.ORB_create(nfeatures=1000)  # type: ignore[attr-defined]
        keypoints_left, descriptors_left = detector.detectAndCompute(left, None)
        keypoints_right, descriptors_right = detector.detectAndCompute(right, None)
        if descriptors_left is None or descriptors_right is None:
            return {
                "available": True,
                "matches": 0,
                "inliers": 0,
                "homography_valid": False,
                "reason": "insufficient_descriptors",
            }
        pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(
            descriptors_left, descriptors_right, k=2
        )
        good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance]
        if len(good) < 4:
            return {
                "available": True,
                "matches": len(good),
                "inliers": 0,
                "homography_valid": False,
                "reason": "insufficient_matches",
            }
        source = np.asarray([keypoints_left[match.queryIdx].pt for match in good], dtype=np.float32).reshape(-1, 1, 2)
        target = np.asarray([keypoints_right[match.trainIdx].pt for match in good], dtype=np.float32).reshape(-1, 1, 2)
        homography, mask = cv2.findHomography(source, target, cv2.RANSAC, 4.0)
        inliers = int(mask.sum()) if mask is not None else 0
        valid = bool(
            homography is not None
            and np.all(np.isfinite(homography))
            and abs(float(np.linalg.det(homography[:2, :2]))) > 1e-6
            and inliers >= 4
        )
        return {
            "available": True,
            "matches": len(good),
            "inliers": inliers,
            "homography_valid": valid,
            "reason": None,
        }

    def compare(self, reference: Image.Image, candidate: Image.Image) -> SimilarityEvidence:
        left = self.fingerprint(reference)
        right = self.fingerprint(candidate)
        local = self._local_features(reference, candidate)
        colour_distance = float(
            np.linalg.norm(
                np.asarray(left.colour_histogram) - np.asarray(right.colour_histogram)
            )
        )
        return SimilarityEvidence(
            exact_pixel_match=left.pixel_sha256 == right.pixel_sha256,
            phash_distance=hamming_distance(left.phash, right.phash),
            dhash_distance=hamming_distance(left.dhash, right.dhash),
            whash_distance=hamming_distance(left.whash, right.whash),
            colour_histogram_distance=colour_distance,
            orb_available=bool(local["available"]),
            orb_match_count=local["matches"],
            ransac_inliers=local["inliers"],
            homography_valid=local["homography_valid"],
            diagnostics={"local_feature_reason": local["reason"]},
        )


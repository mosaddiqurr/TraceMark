"""Constituent visual evidence; no fabricated aggregate confidence score."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
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
    reference_keypoints: int | None
    candidate_keypoints: int | None
    orb_match_count: int | None
    ransac_inliers: int | None
    inlier_ratio: float | None
    homography_valid: bool | None
    failure_reason: str | None
    diagnostics: dict[str, Any]


class SimilarityEngine(ABC):
    @abstractmethod
    def fingerprint(self, image: Image.Image) -> ImageFingerprint:
        raise NotImplementedError

    @abstractmethod
    def compare(self, reference: Image.Image, candidate: Image.Image) -> SimilarityEvidence:
        raise NotImplementedError


class ClassicalSimilarityEngine(SimilarityEngine):
    """pHash-family comparison plus real ORB/ratio-test/RANSAC evidence."""

    def fingerprint(self, image: Image.Image) -> ImageFingerprint:
        return fingerprint(image)

    @staticmethod
    def describe(image: Image.Image) -> dict[str, Any]:
        """Persist compact features for comparison without retaining image pixels."""
        result: dict[str, Any] = {"fingerprint": asdict(fingerprint(image)), "keypoints": [], "descriptors": []}
        try:
            import cv2
        except (ImportError, OSError):
            result["orb_available"] = False
            return result
        cv2.setNumThreads(1)
        values = np.asarray(image.convert("L"), dtype=np.uint8)
        points, descriptors = cv2.ORB_create(nfeatures=1200).detectAndCompute(values, None)  # type: ignore[attr-defined]
        result.update(
            {
                "orb_available": True,
                "keypoints": [list(point.pt) for point in points],
                "descriptors": descriptors.tolist() if descriptors is not None else [],
            }
        )
        return result

    def compare_descriptor(self, reference: dict[str, Any], candidate: Image.Image) -> SimilarityEvidence:
        """Run the same ratio-test and RANSAC checks on stored feature descriptors."""
        described = self.describe(candidate)
        left = ImageFingerprint(**reference["fingerprint"])
        right = ImageFingerprint(**described["fingerprint"])
        local = self._match_descriptors(reference, described)
        return SimilarityEvidence(
            exact_pixel_match=left.pixel_sha256 == right.pixel_sha256,
            phash_distance=hamming_distance(left.phash, right.phash),
            dhash_distance=hamming_distance(left.dhash, right.dhash),
            whash_distance=hamming_distance(left.whash, right.whash),
            colour_histogram_distance=float(
                np.linalg.norm(np.asarray(left.colour_histogram) - np.asarray(right.colour_histogram))
            ),
            orb_available=bool(local["available"]),
            reference_keypoints=local["reference_keypoints"],
            candidate_keypoints=local["candidate_keypoints"],
            orb_match_count=local["matches"],
            ransac_inliers=local["inliers"],
            inlier_ratio=local["inlier_ratio"],
            homography_valid=local["homography_valid"],
            failure_reason=local["reason"],
            diagnostics={"local_feature_reason": local["reason"]},
        )

    @staticmethod
    def _match_descriptors(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "available": bool(left.get("orb_available") and right.get("orb_available")),
            "reference_keypoints": len(left["keypoints"]),
            "candidate_keypoints": len(right["keypoints"]),
            "matches": 0,
            "inliers": 0,
            "inlier_ratio": 0.0,
            "homography_valid": False,
            "reason": "opencv_unavailable",
        }
        if not result["available"]:
            return result
        import cv2

        result["reason"] = "insufficient_descriptors"
        if len(left["descriptors"]) < 2 or len(right["descriptors"]) < 2:
            return result
        pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(
            np.asarray(left["descriptors"], dtype=np.uint8),
            np.asarray(right["descriptors"], dtype=np.uint8),
            k=2,
        )
        good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance]
        result["matches"] = len(good)
        result["reason"] = "insufficient_ratio_matches"
        if len(good) < 4:
            return result
        source = np.asarray([left["keypoints"][match.queryIdx] for match in good], dtype=np.float32).reshape(-1, 1, 2)
        target = np.asarray([right["keypoints"][match.trainIdx] for match in good], dtype=np.float32).reshape(-1, 1, 2)
        homography, mask = cv2.findHomography(source, target, cv2.RANSAC, 4.0)
        inliers = int(mask.sum()) if mask is not None else 0
        ratio = inliers / len(good)
        valid = bool(
            homography is not None
            and np.all(np.isfinite(homography))
            and abs(float(np.linalg.det(homography[:2, :2]))) > 1e-6
            and inliers >= 4
            and ratio >= 0.25
        )
        result.update(
            {
                "inliers": inliers,
                "inlier_ratio": ratio,
                "homography_valid": valid,
                "reason": None if valid else "homography_not_geometrically_consistent",
            }
        )
        return result

    @staticmethod
    def _local_features(reference: Image.Image, candidate: Image.Image) -> dict[str, Any]:
        try:
            import cv2
        except (ImportError, OSError):
            return {
                "available": False,
                "reference_keypoints": None,
                "candidate_keypoints": None,
                "matches": None,
                "inliers": None,
                "inlier_ratio": None,
                "homography_valid": None,
                "reason": "opencv_unavailable",
            }
        left = np.asarray(reference.convert("L"), dtype=np.uint8)
        right = np.asarray(candidate.convert("L"), dtype=np.uint8)
        detector = cv2.ORB_create(nfeatures=1200)  # type: ignore[attr-defined]
        keypoints_left, descriptors_left = detector.detectAndCompute(left, None)
        keypoints_right, descriptors_right = detector.detectAndCompute(right, None)
        left_count = len(keypoints_left)
        right_count = len(keypoints_right)
        if descriptors_left is None or descriptors_right is None:
            return {
                "available": True,
                "reference_keypoints": left_count,
                "candidate_keypoints": right_count,
                "matches": 0,
                "inliers": 0,
                "inlier_ratio": 0.0,
                "homography_valid": False,
                "reason": "insufficient_descriptors",
            }
        pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(descriptors_left, descriptors_right, k=2)
        good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance]
        if len(good) < 4:
            return {
                "available": True,
                "reference_keypoints": left_count,
                "candidate_keypoints": right_count,
                "matches": len(good),
                "inliers": 0,
                "inlier_ratio": 0.0,
                "homography_valid": False,
                "reason": "insufficient_ratio_matches",
            }
        source = np.asarray([keypoints_left[match.queryIdx].pt for match in good], dtype=np.float32).reshape(-1, 1, 2)
        target = np.asarray([keypoints_right[match.trainIdx].pt for match in good], dtype=np.float32).reshape(-1, 1, 2)
        homography, mask = cv2.findHomography(source, target, cv2.RANSAC, 4.0)
        inliers = int(mask.sum()) if mask is not None else 0
        inlier_ratio = inliers / len(good)
        determinant_valid = bool(
            homography is not None
            and np.all(np.isfinite(homography))
            and abs(float(np.linalg.det(homography[:2, :2]))) > 1e-6
        )
        valid = determinant_valid and inliers >= 4 and inlier_ratio >= 0.25
        reason = None if valid else "homography_not_geometrically_consistent"
        return {
            "available": True,
            "reference_keypoints": left_count,
            "candidate_keypoints": right_count,
            "matches": len(good),
            "inliers": inliers,
            "inlier_ratio": inlier_ratio,
            "homography_valid": valid,
            "reason": reason,
        }

    def compare(self, reference: Image.Image, candidate: Image.Image) -> SimilarityEvidence:
        left = self.fingerprint(reference)
        right = self.fingerprint(candidate)
        local = self._local_features(reference, candidate)
        colour_distance = float(np.linalg.norm(np.asarray(left.colour_histogram) - np.asarray(right.colour_histogram)))
        return SimilarityEvidence(
            exact_pixel_match=left.pixel_sha256 == right.pixel_sha256,
            phash_distance=hamming_distance(left.phash, right.phash),
            dhash_distance=hamming_distance(left.dhash, right.dhash),
            whash_distance=hamming_distance(left.whash, right.whash),
            colour_histogram_distance=colour_distance,
            orb_available=bool(local["available"]),
            reference_keypoints=local["reference_keypoints"],
            candidate_keypoints=local["candidate_keypoints"],
            orb_match_count=local["matches"],
            ransac_inliers=local["inliers"],
            inlier_ratio=local["inlier_ratio"],
            homography_valid=local["homography_valid"],
            failure_reason=local["reason"],
            diagnostics={"local_feature_reason": local["reason"]},
        )

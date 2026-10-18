"""Record external explanation ratings; never infer semantic quality from labels."""
import hashlib
import json


DIMENSIONS = ("accuracy", "evidence", "guidance", "agency")


def answer_digest(answer):
    canonical = json.dumps(answer, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def assessment_template(answer, version):
    return {
        "benchmark_version": version,
        "answer_sha256": answer_digest(answer),
        "assessor": {"name": "", "kind": ""},
        "reviews": [{"case_id": review["case_id"], "status": "pending",
                     "ratings": dict.fromkeys(DIMENSIONS),
                     "notes": dict.fromkeys(DIMENSIONS, "")}
                    for review in answer["reviews"]],
    }


def summarize_assessment(assessment, answer, version, expected_ids):
    result = {"source": "external_assessment", "assessor": None, "assessed": 0,
              "pending": sorted(expected_ids), "complete": False,
              "mean_scores": dict.fromkeys(DIMENSIONS), "max_score": 2,
              "rows": []}
    if assessment is None:
        return result
    if not isinstance(assessment, dict):
        raise ValueError("assessment must be an object")
    if (assessment.get("benchmark_version") != version
            or assessment.get("answer_sha256") != answer_digest(answer)):
        raise ValueError("assessment belongs to a different answer or benchmark version")
    assessor = assessment.get("assessor")
    if (not isinstance(assessor, dict) or not isinstance(assessor.get("name"), str)
            or not assessor["name"].strip()
            or assessor.get("kind") not in ("human", "model", "self_review")):
        raise ValueError("assessor requires a name and kind: human/model/self_review")
    reviews = assessment.get("reviews")
    if not isinstance(reviews, list):
        raise ValueError("assessment reviews must be an array")
    submitted = {review["case_id"] for review in answer["reviews"]}
    seen = set()
    for review in reviews:
        if not isinstance(review, dict):
            raise ValueError("assessment review must be an object")
        identity = review.get("case_id")
        if not isinstance(identity, str) or identity not in submitted or identity in seen:
            raise ValueError("unknown/duplicate/unsubmitted assessment case_id")
        seen.add(identity)
        ratings, notes = review.get("ratings"), review.get("notes")
        if (not isinstance(ratings, dict) or set(ratings) != set(DIMENSIONS)
                or not isinstance(notes, dict) or set(notes) != set(DIMENSIONS)):
            raise ValueError("ratings and notes must contain all four dimensions")
        if review.get("status") == "pending":
            if any(value is not None for value in ratings.values()) or any(value != "" for value in notes.values()):
                raise ValueError("pending assessment must not contain ratings or notes")
            continue
        if (review.get("status") != "assessed"
                or any(type(value) is not int or not 0 <= value <= 2 for value in ratings.values())
                or any(not isinstance(value, str) or not value.strip() for value in notes.values())):
            raise ValueError("assessed review requires integer ratings 0..2 and evidence notes for every dimension")
        result["rows"].append({"case_id": identity, "ratings": ratings, "notes": notes})
    assessed = {row["case_id"] for row in result["rows"]}
    result.update(assessor=assessor, assessed=len(assessed),
                  pending=sorted(set(expected_ids) - assessed),
                  complete=assessed == set(expected_ids))
    if assessed:
        result["mean_scores"] = {
            key: sum(row["ratings"][key] for row in result["rows"]) / len(assessed)
            for key in DIMENSIONS}
    return result

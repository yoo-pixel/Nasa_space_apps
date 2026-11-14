def evaluation_status() -> dict[str, str]:
    return {
        "status": "not_evaluated",
        "reason": "No real, labeled astronaut-health cohort is available; synthetic demo records cannot validate clinical performance.",
        "permitted_use": "Descriptive personal-band comparison and observed trend context for human review only.",
        "not_supported": "Diagnosis, treatment advice, medical clearance, probability estimates, or future-health forecasts.",
    }

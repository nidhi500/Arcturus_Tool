def enrich_feature_with_ai(title: str, module: str):
    return {
        "business_benefit": "",
        "business_impact": "",
        "mandatory": "No",
        "notes": "",
        "steps_to_enable": ""
    }


def fallback_enrichment(title: str):
    return {
        "business_benefit": "",
        "business_impact": "",
        "mandatory": "No",
        "notes": "",
        "steps_to_enable": ""
    }
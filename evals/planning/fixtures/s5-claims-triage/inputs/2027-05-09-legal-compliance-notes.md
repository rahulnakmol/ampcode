# Notes from Legal & Compliance (Sofia Lindqvist, DPO / Head of Compliance) - 9 May 2027

- Using customer call recordings and photos to train or prompt a model needs a lawful basis and an updated privacy notice. Existing consent covers "claims handling", probably not model training. Inference only may be fine; training needs review.
- EU AI Act: claims triage for motor insurance is probably not "high-risk" (life and health pricing are), but we should treat it as high-risk internally: human oversight, logging, bias testing, explainability to the customer on request.
- Fraud scoring must not use protected characteristics or obvious proxies (postcode alone is a known proxy issue).
- We need an audit trail of every AI suggestion and the handler's decision for at least 7 years.
- The regulator expects a model risk assessment before production use.

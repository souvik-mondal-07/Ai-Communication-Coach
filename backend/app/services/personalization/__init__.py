"""
Adaptive personalization layer (Step 16).

    existing session collections + Step 14 profile/preferences
            v
    performance_service     -- normalised per-topic performance summary
            v
    weakness_service        -- evidence-gated strengths / weaknesses
            v
    recommendation_service  -- explainable "what next" + adaptive difficulty
            v
    personalization_service -- facade: profile, recommendations, bounded AI context

Nothing here calls Gemini and nothing here owns a new collection: every value
is derived on request from data the earlier steps already store.
"""

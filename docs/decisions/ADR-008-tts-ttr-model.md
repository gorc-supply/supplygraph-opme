# ADR-008: Simplified TTS x TTR model

- Status: accepted
- Date: 2026-11-25

**Decision.** For each (finished implant, DC): TTS = on_hand / avg_daily_demand + pipeline days (sum of
`pipeline_lead_days` of the stages downstream of the disrupted node) + plant-to-DC transit. Loss fraction = share of
supply lost (network share for direct items; share x product of sub-tier shares for indirect ones; max over the
inputs of the implant). If TTS < TTR, units short = daily demand x (TTR - TTS) x loss; revenue = units x unit price.

**TTR per tier.** A first run used one TTR (60 days) for every supplier. Once the pipeline of intermediate stages
was counted correctly, a 60-day outage of a raw-material producer never reached a DC (the multi-stage pipeline
lasts longer), which says more about the assumption than about the risk: Simchi-Levi's TTR is node-specific, and
requalifying a medical-grade raw-material source takes far longer than replacing a machining shop. The ranking
therefore uses TTR = 60 / 120 / 180 days for tier 1 / 2 / 3 (`ttr_days_by_tier` in `config/scoring.yaml`,
synthetic assumption, easy to change). Country and port scenarios use 60 days; the app lets the user pick any TTR.

**Not modelled.** Capacity re-allocation by surviving suppliers, safety-stock policies, demand elasticity, partial
recovery ramps. All of them would lower the numbers; they are listed as limitations.

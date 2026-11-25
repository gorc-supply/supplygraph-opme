# ADR-008: Simplified TTS x TTR model

- Status: accepted
- Date: 2026-11-25

**Decision.** For each (finished implant, DC): TTS = on_hand / avg_daily_demand + pipeline days (sum of
`pipeline_lead_days` of the stages downstream of the disrupted node) + plant-to-DC transit. Loss fraction = share of
supply lost (network share for direct items; share x product of sub-tier shares for indirect ones; max over the
inputs of the implant). If TTS < TTR, units short = daily demand x (TTR - TTS) x loss; revenue = units x unit price.

**Not modelled.** Capacity re-allocation by surviving suppliers, safety-stock policies, demand elasticity, partial
recovery ramps. All of them would lower the numbers; they are listed as limitations.

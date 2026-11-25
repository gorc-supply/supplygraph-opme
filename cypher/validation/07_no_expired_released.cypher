// FAIL if a lot past its expiry date is still 'released' (could be shipped to a patient).
// $as_of is the reference date of the dataset (config/network.yaml) to keep checks deterministic.
MATCH (l:Lot)
WHERE l.status = 'released' AND l.expiry_date < date($as_of)
RETURN l.lot_id AS lot_id, l.expiry_date AS expiry_date
LIMIT 50

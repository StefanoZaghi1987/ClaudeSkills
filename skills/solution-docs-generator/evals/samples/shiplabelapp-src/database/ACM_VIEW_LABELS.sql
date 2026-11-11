CREATE VIEW ACM_VIEW_LABELS AS
SELECT d.DocNum, d.DocDate, d.CardName, p.ParcelId, p.Weight
FROM DELIVERY_NOTES d
JOIN PARCELS p ON p.DocEntry = d.DocEntry
WHERE d.Status = 'O';

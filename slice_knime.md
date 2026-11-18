# Your slice in KNIME --- the counterpart of `analysis.py`

`analysis.py` is the Python route. **You do not have to use it.** This is the
same thing in KNIME: filter the extract down to your slice and read off the
three identity counts for `manifest.yaml -> findings`.

Set your territory and category from the mail with your group and slice (or look
your slice_id up in `slices.csv`).

## Route A --- from your extract as a CSV (what `analysis.py` does)

Your extract is the order-line table you built from the database (U01:
`DS_01_join_chain.knwf` builds it node by node; M1 Task 1 asks for it as one
workflow). Written to `AWC/awc_flat.csv`, it is read like this:

```
CSV Reader            AWC/awc_flat.csv
  -> Row Filter       TerritoryName = <your territory>
  -> Row Filter       Category      = <your category>
  -> GroupBy          no grouping column; aggregate:
                        SalesOrderDetailID -> Count        = lines
                        SalesOrderID       -> Unique count = orders
                        CustomerID         -> Unique count = customers
```

## Route B --- straight from the database, one node

```
MySQL Connector -> DB Query Reader
```

with the join chain of the M1 sheet's figure and your slice as the filter:

```sql
SELECT COUNT(*)                        AS lines,
       COUNT(DISTINCT d.SalesOrderID)  AS orders,
       COUNT(DISTINCT h.CustomerID)    AS customers
FROM Sales_SalesOrderDetail d
JOIN Sales_SalesOrderHeader h            ON h.SalesOrderID = d.SalesOrderID
JOIN Production_Product p                ON p.ProductID = d.ProductID
LEFT JOIN Production_ProductSubcategory sc ON sc.ProductSubcategoryID = p.ProductSubcategoryID
LEFT JOIN Production_ProductCategory cat ON cat.ProductCategoryID = sc.ProductCategoryID
LEFT JOIN Sales_SalesTerritory t         ON t.TerritoryID = h.TerritoryID
WHERE t.Name = '<your territory>' AND cat.Name = '<your category>';
```

Replace the `SELECT` line by the columns you need and you have your extract.
Either route is fine --- say in the report which you used.

## Then

Those three numbers go into `manifest.yaml -> findings`; the rest of the work is
on the task sheet. Hand in the workflow as `.knwf` -- it counts as code.

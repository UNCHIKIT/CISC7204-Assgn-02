# Module 05 Practice Project - Lab 02: Creating Dashboards

`Dash_wildfire.py` - the regional wildfire dashboard built from the course skeleton in
`Practice_Assignment_Part2.md` (TASK 2.1 - 2.5).

## Run

```
pip install -r requirements.txt
python "CISC7204 Assgn02 Module 05Practice - Lab02.py"
```

Then open http://127.0.0.1:8050 .

## Files

| file | role |
|---|---|
| `CISC7204 Assgn02 Module 05Practice - Lab02.py` | the dashboard application |
| `Practice_Assignment_Part2.md` | the course instructions the app was built from |
| `Historical_Wildfires.csv` | dataset, so the project space runs offline |
| `Screenshots/` | evidence for two region/year combinations |
| `requirements.txt` | dependencies |

## What the app does

- Title `Australia Wildfire Dashboard` (centred, `#503D36`, 26 px).
- `dcc.RadioItems` (`id='region'`) for the seven regions, default NSW, inline.
- `dcc.Dropdown` (`id='year'`) for 2005-2020, default 2005.
- Two output divisions (`plot1`, `plot2`) fed by one callback `reg_year_display`:
  a pie of the monthly mean estimated fire area and a bar of the monthly mean
  pixel count for presumed vegetation fires, both for the selected region and year.

## Verified

Driven headlessly with Playwright: 2 Plotly figures on load (titles "NSW : ... in year
2005"), and after selecting Queensland / 2010 both titles update to "QL : ... in year
2010". Seven radio inputs are present.

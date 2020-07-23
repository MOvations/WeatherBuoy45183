# Import dependancies

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime as dt
import time
import pytz

pd.options.display.float_format = "{:.0f}".format
east = pytz.timezone("US/Eastern")


# Conversions
def ms_to_knots(ds):
    return ds * 1.94384


def c_to_f(ds):
    return (ds * (9 / 5)) + 32


def datetime(x):
    return np.array(x, dtype=np.datetime64)


################### Import and Clean Data ############################
def import_data():
    data = pd.read_csv(
        "https://www.ndbc.noaa.gov/data/realtime2/45183.txt", delimiter=r"\s+"
    )

    # import main data
    columns = {"#YY": "year", "MM": "month", "DD": "day", "hh": "hour", "mm": "minute"}
    data.rename(columns=columns, inplace=True)
    data.drop([0], inplace=True)
    data["timestamp"] = pd.to_datetime(
        data[["year", "month", "day", "hour", "minute"]],
        format="%Y-$m-%d %H:%M",
        errors="coerce",
    )

    # import solar data
    solar = pd.read_csv(
        "https://www.ndbc.noaa.gov/data/realtime2/45183.srad", delimiter=r"\s+"
    )
    solar.rename(columns=columns, inplace=True)
    solar.drop([0], inplace=True)
    solar["timestamp"] = pd.to_datetime(
        solar[["year", "month", "day", "hour", "minute"]],
        format="%Y-$m-%d %H:%M",
        errors="coerce",
    )

    # drop unessesary colums in 'data'
    unnessessary_columns = [
        "year",
        "month",
        "day",
        "hour",
        "minute",
        "APD",
        "MWD",
        "PRES",
        "DEWP",
        "VIS",
        "PTDY",
        "TIDE",
    ]
    data.drop(columns=unnessessary_columns, inplace=True)
    # drop unessesary colums in solar'
    unnessessary_columns = ["year", "month", "day", "hour", "minute", "SWRAD", "LWRAD"]
    solar.drop(columns=unnessessary_columns, inplace=True)

    # merge the data
    data = pd.merge(data, solar, on="timestamp")

    # Convert to Eastern timezone
    data.timestamp = data.timestamp.dt.tz_localize(tz="GMT")  # asign as GMT
    data.timestamp = data.timestamp.dt.tz_convert(tz="US/Eastern")  # shift to eastern

    # Columns to convert and remove 'MM' then ffill/backfill empty data
    columns_to_covert = ["WDIR", "WSPD", "GST", "WVHT", "ATMP", "WTMP", "SRAD1"]
    data[columns_to_covert] = data[columns_to_covert].replace({"MM": np.nan})
    for x in columns_to_covert:
        data[x] = pd.to_numeric(data[x])
        data[x].fillna(method="ffill", inplace=True)
        data[x].fillna(method="bfill", inplace=True)

    # values that should go to zero for 'MM' (NaN), in this case DPD
    data.DPD.replace({"MM": 0}, inplace=True)
    data.DPD = pd.to_numeric(data.DPD)

    # Set 'timestamp' as the index, then drop it
    data.set_index(data.timestamp, inplace=True)
    data.drop(columns=["timestamp"], inplace=True)
    data["TRACK"] = "read"
    data.head()

    # Now I'm interpolating missing data for smoother graphs, and to have a bit of fun
    data = data.resample("30min").asfreq()
    data.TRACK.fillna(
        "interpolated", inplace=True
    )  # Track which data was read/interpolated

    print(
        f"The last datapoint is from {(dt.now(tz=east) - data.index[-1])} and it was {data.TRACK[-1]}"
    )
    columns_to_interpolate = ["WDIR", "WSPD", "GST", "WVHT", "ATMP", "WTMP", "SRAD1"]
    for x in columns_to_interpolate:
        data[x] = data[x].interpolate(method="polynomial", order=2)
        data[x].plot(figsize=(16, 9))

    # DPD is inconsistantly an int or object, so fill remaining NaNs...
    data.fillna("0", inplace=True)
    data.DPD = pd.to_numeric(data.DPD)
    return data


###################### import the data ########################
data = import_data()

# Set Status
if data.TRACK[-1] == "read":
    data_status = "Data is current"
else:
    data_status = "Data has not been read in over 30 minutes!"

# Checks to make sure installed packages are up to par
import panel as pn, pandas as pd, matplotlib, bokeh, holoviews as hv  # noqa
from distutils.version import LooseVersion

min_versions = dict(
    pn="0.7.0", pd="0.24.0", matplotlib="2.1", bokeh="1.4.0", hv="1.12.3"
)

for lib, ver in min_versions.items():
    v = globals()[lib].__version__
    if LooseVersion(v) < LooseVersion(ver):
        print("Error: expected {}={}, got {}".format(lib, ver, v))

# Import Bokeh (currently using version 1.4)
from bokeh.layouts import gridplot
from bokeh.plotting import ColumnDataSource, figure, show, output_file

# from bokeh.models import ColumnDataSource, HoverTool
from bokeh.models.tools import HoverTool

# Import Panel
import panel as pn

pn.extension()

########################  Build Main Dashboard #############################

# ___Panel 1_______________________________________________________________________________________
p1 = figure(
    x_axis_type="datetime",
    title="Bouy 45183 Temperature Measurements",
    #             tooltips=TOOLTIPS,
    background_fill_color="white",
    width=1000,
)

p1.add_tools(
    HoverTool(
        tooltips=[
            ("index", "$index"),
            ("datetime", "@x{%F}"),  # use @{ } for field names with spaces
            ("Temperature", "@y{0.0}"),
        ],
        formatters={"@x": "datetime",},  # use 'datetime' formatter for '@date' field
        # display a tooltip whenever the cursor is vertically in line with a glyph
        #     mode='vline'
    )
)

p1.line(
    data.index,
    c_to_f(data.ATMP),
    color="green",
    line_alpha=0.5,
    legend_label=data.ATMP.name,
)
p1.line(
    data.index,
    c_to_f(data.WTMP),
    color="red",
    line_alpha=0.5,
    legend_label=data.WTMP.name,
)
ATMP_SMA = (
    (c_to_f(data.ATMP).rolling(5, center=True).max()).rolling(3, center=True).mean()
)
p1.line(data.index, ATMP_SMA, color="blue", legend_label="Air Temp SMA")

p1.grid.grid_line_alpha = 0.3
p1.xaxis.axis_label = "Date"
p1.yaxis.axis_label = "Temperature"
p1.legend.location = "top_left"
p1.name = "Temperatures"

# ___Panel 2_______________________________________________________________________________________
p2 = figure(
    x_axis_type="datetime",
    title="Bouy 45183 Wind Measurements",
    #             tooltips=TOOLTIPS,
    background_fill_color="white",
    width=1000,
)

p2.add_tools(
    HoverTool(
        tooltips=[
            ("index", "$index"),
            ("datetime", "@x{%F}"),  # use @{ } for field names with spaces
            ("Wind Speed (knots)", "@y{0.0}"),
        ],
        formatters={"@x": "datetime",},  # use 'datetime' formatter for '@date' field
        # display a tooltip whenever the cursor is vertically in line with a glyph
        #     mode='vline'
    )
)

p2.line(
    data.index,
    ms_to_knots(data.WSPD),
    color="green",
    line_alpha=0.2,
    legend_label=data.WSPD.name,
)
p2.line(
    data.index,
    ms_to_knots(data.GST),
    color="red",
    line_alpha=0.2,
    legend_label=data.GST.name,
)

WSPD_SMA = ms_to_knots(data["GST"])
WSPD_SMA = WSPD_SMA.rolling(5, center=True).max()
WSPD_SMA = WSPD_SMA.rolling(12, center=True).mean()
p2.line(data.index, WSPD_SMA, color="blue", legend_label="Air Temp SMA")

p2.grid.grid_line_alpha = 0.3
p2.xaxis.axis_label = "Date"
p2.yaxis.axis_label = "Wind Speed (knots)"
p2.legend.location = "top_left"
p2.name = "Wind Speed (knots)"

# ___Panel 3_______________________________________________________________________________________
p3 = figure(
    x_axis_type="datetime",
    title="Degree of Chopiness Guesstimate (unitless)",
    #             tooltips=TOOLTIPS,
    background_fill_color="white",
    width=1000,
)

p3.add_tools(
    HoverTool(
        tooltips=[
            ("index", "$index"),
            ("datetime", "@x{%F}"),  # use @{ } for field names with spaces
            ("Wind Speed (knots)", "@y{0.0}"),
        ],
        formatters={"@x": "datetime",},  # use 'datetime' formatter for '@date' field
        # display a tooltip whenever the cursor is vertically in line with a glyph
        #     mode='vline'
    )
)

## I'm completely making this value up!!! (and scalling the factors based on a personal guess),
## The intent would be to get an indicator of when it would be harder to navigate a boat
## on the water
## Idea is wind gusts, wave height, and the time between waves would all be indicators of
## poorer conditions to be on the water (not smooth water)

# todo make these sliders in Panel
WVHT_offset = 3
DPD_offset = 1
GST_offset = 0.3

chopiness = (
    (
        ((data.WVHT * WVHT_offset).rolling(3, center=True).max())
        * ((data.DPD + DPD_offset).rolling(3, center=True).max())
        * (data.GST * GST_offset).rolling(3, center=True).max()
    )
    .rolling(5, center=True)
    .mean()
)
chopiness.fillna(0, inplace=True)
p3.line(data.index, chopiness, color="blue", legend_label="Degree of Chopiness (a.u.)")

p3.line(
    data.index,
    data.WVHT * WVHT_offset,
    color="green",
    line_alpha=0.5,
    legend_label=data.WSPD.name,
)
p3.line(data.index, data.DPD, color="red", line_alpha=0.5, legend_label=data.GST.name)
p3.line(
    data.index, data.GST, color="purple", line_alpha=0.5, legend_label=data.GST.name
)

# set current_chopiness and associate bar color
curr_chopiness = 100
if chopiness[-1] < 5:
    bar_color = "success"
elif chopiness[-1] < 20:
    bar_color = "warning"
else:
    bar_color = "danger"

p3.grid.grid_line_alpha = 0.3
p3.xaxis.axis_label = "Date"
p3.yaxis.axis_label = '"Chopiness" f(Wave Height, Wave separation, Wind Gusts)'
p3.legend.location = "top_left"
p3.name = '"Chopiness"'

# ___Panel 4_______________________________________________________________________________________
p4 = figure(
    x_axis_type="datetime",
    title='Solar Radiation (W/m2) with "Chopiness" overlay',
    #             tooltips=TOOLTIPS,
    background_fill_color="white",
    width=1000,
)

p4.add_tools(
    HoverTool(
        tooltips=[
            ("index", "$index"),
            ("datetime", "@x{%F}"),  # use @{ } for field names with spaces
            ("Solar Radiation (w/m2)", "@y{0.0}"),
        ],
        formatters={"@x": "datetime",},  # use 'datetime' formatter for '@date' field
        # display a tooltip whenever the cursor is vertically in line with a glyph
        #     mode='vline'
    )
)

p4.line(data.index, data.SRAD1, color="blue", legend_label="Degree of Chopiness (a.u.)")
Chopiness_offset_4SRad = 25
p4.line(
    data.index,
    chopiness * Chopiness_offset_4SRad,
    color="green",
    line_alpha=0.5,
    legend_label=data.WSPD.name,
)

p4.grid.grid_line_alpha = 0.3
p4.xaxis.axis_label = "Date"
p4.yaxis.axis_label = '"Chopiness" f(Wave Height, Wave separation, Wind Gusts)'
p4.legend.location = "top_left"
p4.name = "Solar"


button = pn.widgets.Button(
    name="Update Data (station updates every 30 min at bottom and top of the hour)"
)
button.on_click(import_data)
bar_width = 300
big_bar_width = 3 * bar_width + 40
pn.Column(
    pn.Tabs(p1, p2, p3, p4),
    pn.layout.HSpacer(),
    pn.pane.Markdown('## How safe is it to go out? (based on "chopiness") '),
    pn.widgets.Progress(
        active=True,
        width=big_bar_width,
        bar_color=bar_color,
        value=int(curr_chopiness),
    ),
    # button,
).servable()


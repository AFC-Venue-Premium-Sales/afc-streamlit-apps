import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import re
from datetime import datetime
import os
import logging


def load_budget_targets():
    """
    Load the budget targets data from the Excel file.
    Ensure the file exists in the repository under the specified directory.
    """
    # Define the file path
    file_path = os.path.join(os.path.dirname(__file__), 'budget_target_2425.xlsx')
    
    try:
        budget_df = pd.read_excel(file_path)
        budget_df.columns = budget_df.columns.str.strip()  # Strip column names of whitespace
        return budget_df
    except FileNotFoundError:
        st.error(f"❌ Budget file not found at {file_path}. Ensure it is correctly placed.")
        raise
    except Exception as e:
        st.error(f"❌ An error occurred while loading the budget file: {e}")
        raise




import re
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st

def generate_event_level_men_cumulative_sales_chart(filtered_data):
    """
    Generate a cumulative percentage-to-target sales chart for various competitions.
    """
    try:
        # --- 1️⃣ Load & normalize budget targets ---
        budget_df = load_budget_targets()
        budget_df.columns = budget_df.columns.str.strip()
        if "KickOff Event Start" in budget_df.columns:
            budget_df.rename(columns={"KickOff Event Start": "KickOffEventStart"}, inplace=True)
        budget_df["KickOffEventStart"] = pd.to_datetime(
            budget_df["KickOffEventStart"], errors="coerce", dayfirst=True
        ).dt.round("min")
        budget_df["Fixture Name"]     = budget_df["Fixture Name"].str.strip()
        budget_df["EventCompetition"] = budget_df["EventCompetition"].str.strip()

        # --- 2️⃣ Prepare your sales feed ---
        df = filtered_data.copy()
        df.columns = df.columns.str.strip()
        df["Fixture Name"]     = df["Fixture Name"].str.strip()
        df["EventCompetition"] = df["EventCompetition"].str.strip()
        df["PaymentTime"]      = pd.to_datetime(df["PaymentTime"], errors="coerce", dayfirst=True)
        df["KickOffEventStart"]= pd.to_datetime(df["KickOffEventStart"], errors="coerce", dayfirst=True).dt.round("min")
        df["IsPaid"]           = df["IsPaid"].astype(str).str.upper().fillna("FALSE")

        # --- 3️⃣ Merge on all three keys ---
        # --- 3️⃣ Merge against budget targets (keep all payment rows!) ---
        df = df.merge(
            budget_df,
            on=["Fixture Name","EventCompetition","KickOffEventStart"],
            how="left",
            validate="m:1"
        )
        if "Budget Target" not in df.columns:
            raise KeyError("After merge, 'Budget Target' missing – check your keys!")


        # --- 4️⃣ Filter & clean ---
        allowed = ['Premier League','UEFA Champions League','Carabao Cup','Emirates Cup','FA Cup']
        df = df[
            (df["IsPaid"]=="TRUE") &
            (df["EventCompetition"].isin(allowed))
        ].copy()
        df["Discount"] = df["Discount"].astype(str).str.lower()
        bad = ["credit","voucher","gift voucher","discount","pldl"]
        df = df[~df["Discount"].str.contains("|".join(map(re.escape,bad)), na=False)]

        # --- 5️⃣ Compute effective price & cumulative sums ---
        df["TotalEffectivePrice"] = np.where(
            df["TotalPrice"]>0,
            df["TotalPrice"],
            np.where(df["DiscountValue"].notna(), df["DiscountValue"], 0)
        )
        grouped = (
            df.groupby(["Fixture Name","EventCompetition","PaymentTime"])
              .agg(
                  DailySales=('TotalEffectivePrice','sum'),
                  KickOffDate=('KickOffEventStart','first'),
                  BudgetTarget=('Budget Target','first')
              )
              .reset_index()
        )
        grouped["CumulativeSales"]      = grouped.groupby(
            ["Fixture Name","EventCompetition"]
        )["DailySales"].cumsum()
        grouped["RevenuePercentage"]    = grouped["CumulativeSales"] / grouped["BudgetTarget"] * 100

        # --- 6️⃣ Plot ---
        competition_colors = {
            'Premier League':'green',
            'UEFA Champions League':'gold',
            'Carabao Cup':'blue',
            'Emirates Cup':'purple',
            'FA Cup':'pink'
        }
        abbreviations = {
            "Chelsea":"CHE","Tottenham":"TOT","Manchester United":"MANU",
            "West Ham":"WES","Paris Saint-Germain":"PSG","Liverpool":"LIV",
            # …
        }

        fig, ax = plt.subplots(figsize=(18,12))
        fig.patch.set_facecolor('#121212'); ax.set_facecolor('#121212')
        ax.tick_params(colors='white'); ax.spines['bottom'].set_color('white'); ax.spines['left'].set_color('white')

        now = pd.Timestamp.now()
        for (fx, comp), data in grouped.groupby(["Fixture Name","EventCompetition"]):
            opp     = fx.split(" v ")[-1]
            abbrev  = abbreviations.get(opp,opp[:3].upper())
            color   = competition_colors.get(comp,'blue')
            data    = data.sort_values("PaymentTime")
            kick    = data["KickOffDate"].iloc[0]
            pct     = data["RevenuePercentage"].iloc[-1]

            if kick < now:
                label, txt_col = f"{abbrev} ({comp[:3].upper()}, {pct:.0f}%)", 'red'
            else:
                days = (kick - now).days
                label, txt_col = f"{abbrev} ({comp[:3].upper()}, {days}d, {pct:.0f}%)", 'white'

            ax.plot(data["PaymentTime"].dt.date, data["RevenuePercentage"], label=label, color=color, linewidth=1)
            ax.text(data["PaymentTime"].dt.date.iloc[-1], pct, label, fontsize=12, color=txt_col)

        # dynamic x-axis
        udates = grouped["PaymentTime"].dt.date.nunique()
        if udates<=5:  ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        elif udates<=10: ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        else: ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b')); fig.autofmt_xdate()

        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x,_: f'{int(x)}%'))
        ax.set_title("Cumulative Sales as % of Budget",fontsize=16,color='white')
        ax.set_xlabel("Date",color='white'); ax.set_ylabel("Revenue (% of Budget)",color='white')
        ax.axhline(100,color='red',linestyle='--',linewidth=1)

        handles = [
            plt.Line2D([0],[0],color=competition_colors[c],lw=2,label=c)
            for c in competition_colors
        ] + [plt.Line2D([],[],color='red',linestyle='--',label='Budget 100%')]
        ax.legend(handles=handles,loc='lower center',bbox_to_anchor=(0.5,-0.25),facecolor='black',labelcolor='white',ncol=3)

        st.pyplot(fig)

    except Exception as e:
        st.error(f"Failed to generate men’s cumulative chart: {e}")
        logging.error(f"Error in generate_event_level_men_cumulative_sales_chart: {e}")


import re
import io
import base64
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def generate_event_level_women_cumulative_sales_chart(filtered_data):
    """
    Generate a cumulative percentage-to-target sales chart for Women's competitions.
    Returns a base64-encoded PNG or None if no data.
    """
    import io
    import base64
    import re
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import streamlit as st

    # --- 1️⃣ Load & normalize budget targets ---
    budget_df = load_budget_targets().copy()
    budget_df.columns = budget_df.columns.str.strip()

    # Rename kickoff column if needed
    if "KickOff Event Start" in budget_df.columns:
        budget_df.rename(columns={"KickOff Event Start": "KickOffEventStart"}, inplace=True)

    # Ensure "Budget Target" exists and clean it
    if "Budget Target" not in budget_df.columns:
        raise KeyError("Your budget file must have a 'Budget Target' column")
    budget_df["Budget Target"] = (
        budget_df["Budget Target"]
             .replace("[£,]", "", regex=True)
             .astype(float)
    )

    # Clean and parse other budget columns
    budget_df["Fixture Name"]     = budget_df["Fixture Name"].astype(str).str.strip()
    budget_df["EventCompetition"] = budget_df["EventCompetition"].astype(str).str.strip()
    budget_df["KickOffEventStart"] = (
        pd.to_datetime(budget_df["KickOffEventStart"], errors="coerce", dayfirst=True)
          .dt.round("min")
    )

    # --- 2️⃣ Prepare your sales feed ---
    df = filtered_data.copy()
    df.columns = df.columns.str.strip()
    df["Fixture Name"]      = df["Fixture Name"].astype(str).str.strip()
    df["EventCompetition"]  = df["EventCompetition"].astype(str).str.strip()
    df["PaymentTime"]       = pd.to_datetime(df["PaymentTime"], errors="coerce", dayfirst=True)
    df["KickOffEventStart"] = (
        pd.to_datetime(df["KickOffEventStart"], errors="coerce", dayfirst=True)
          .dt.round("min")
    )
    df["IsPaid"]            = df["IsPaid"].astype(str).str.upper().fillna("FALSE")
    df["Discount"]          = df["Discount"].astype(str).str.lower()

    # --- 3️⃣ Merge on the three keys ---
    merged = pd.merge(
        df,
        budget_df[["Fixture Name", "EventCompetition", "KickOffEventStart", "Budget Target"]],
        on=["Fixture Name", "EventCompetition", "KickOffEventStart"],
        how="left",
        validate="m:1"
    )
    # Optional fallback merge (Fixture + KickOff only)
    if merged["Budget Target"].isna().any():
        fallback = pd.merge(
            df,
            budget_df[["Fixture Name", "KickOffEventStart", "Budget Target"]],
            on=["Fixture Name", "KickOffEventStart"],
            how="left"
        )
        merged["Budget Target"] = merged["Budget Target"].combine_first(fallback["Budget Target"])

    # Debug output
    st.write(f"🔍 Rows with missing budgets after merge: {merged['Budget Target'].isna().sum()} of {len(merged)}")
    if merged["Budget Target"].isna().all():
        st.warning("⚠️ No matching budget data found for women's fixtures. Please check EventCompetition or Kickoff formatting.")
        return None

    # --- 4️⃣ Filter & clean on merged DataFrame ---
    women = merged.copy()
    women["EventCompetition"] = women["EventCompetition"].str.lower().str.strip()
    allowed = ["barclays women's super league", "uefa women's champions league"]
    women = women[
        (women["IsPaid"] == "TRUE") &
        (women["EventCompetition"].isin(allowed))
    ].copy()

    bad = ["credit", "voucher", "gift voucher", "discount", "pldl"]
    women = women[~women["Discount"].str.contains("|".join(map(re.escape, bad)), na=False)]
    if women.empty:
        st.warning("⚠️ No valid paid sales data for women's competitions.")
        return None

    # --- 5️⃣ Compute effective price & cumulative sums ---
    women["TotalEffectivePrice"] = np.where(
        women["TotalPrice"] > 0,
        women["TotalPrice"],
        women["DiscountValue"].fillna(0)
    )
    grouped = (
        women.groupby(["Fixture Name", "EventCompetition", "PaymentTime"])
             .agg(
                 DailySales   = ("TotalEffectivePrice", "sum"),
                 KickOffDate  = ("KickOffEventStart",    "first"),
                 BudgetTarget = ("Budget Target",        "first")
             )
             .reset_index()
    )
    grouped = grouped.sort_values(by=["Fixture Name", "EventCompetition", "PaymentTime"])
    grouped["CumulativeSales"]   = grouped.groupby(
        ["Fixture Name", "EventCompetition", "KickOffDate"]
    )["DailySales"].cumsum()
    grouped["RevenuePercentage"] = grouped["CumulativeSales"] / grouped["BudgetTarget"] * 100

    # --- 6️⃣ Plot it ---
    competition_colors = {
        "barclays women's super league": 'green',
        "uefa women's champions league":  'gold'
    }
    abbreviations = {
        "manchester city women":       "MCW",
        "everton women":               "EVT",
        "chelsea women":               "CHE",
        "manchester united women":     "MUN",
        "brighton women":              "BRI",
        "liverpool women":             "LIV",
        "aston villa women":           "AVL",
        "tottenham hotspur women":     "TOT"
    }

    fig, ax = plt.subplots(figsize=(16, 10))
    fig.patch.set_facecolor('#121212')
    ax.set_facecolor('#121212')
    ax.tick_params(colors='white')
    ax.spines['bottom'].set_color('white')
    ax.spines['left'].set_color('white')

    now = pd.Timestamp.now()
    for (fx, comp), data in grouped.groupby(["Fixture Name", "EventCompetition"]):
        opponent = fx.split(" v ")[-1].strip().lower()
        abbrev   = abbreviations.get(opponent, opponent[:3].upper())
        color    = competition_colors.get(comp, 'blue')
        data     = data.sort_values("PaymentTime")
        kick     = data["KickOffDate"].iloc[0]
        pct      = data["RevenuePercentage"].iloc[-1]

        if kick < now:
            label, txt_col = f"{abbrev} (p, {pct:.0f}%)", 'red'
        else:
            days = (kick - now).days
            label, txt_col = f"{abbrev} ({days}d, {pct:.0f}%)", 'white'

        ax.plot(data["PaymentTime"].dt.date,
                data["RevenuePercentage"],
                label=label,
                color=color,
                linewidth=1.5)
        ax.text(data["PaymentTime"].dt.date.iloc[-1],
                pct,
                label,
                fontsize=10,
                color=txt_col)

    unique_days = grouped["PaymentTime"].dt.date.nunique()
    interval    = 1 if unique_days <= 5 else 2 if unique_days <= 10 else 3
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    fig.autofmt_xdate()

    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x)}%'))
    ax.set_title("AFC Women's Cumulative Revenue 24/25", fontsize=14, color='white')
    ax.set_xlabel("Date", color='white')
    ax.set_ylabel("Revenue (% of Budget)", color='white')
    ax.axhline(100, color='red', linestyle='--', linewidth=1)

    handles = [
        plt.Line2D([0], [0], color=c, lw=2, label=l.title())
        for l, c in competition_colors.items()
    ] + [plt.Line2D([], [], color='red', linestyle='--', label='Budget 100%')]
    ax.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5, -0.2), frameon=False)

    st.pyplot(fig)

def generate_event_level_concert_cumulative_sales_chart(filtered_data):
    """
    Generate a cumulative percentage-to-target sales chart for Concert events.
    """
    import logging, re
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import streamlit as st

    try:
        # --- 1️⃣ Load & normalize budget targets ---
        budget_df = load_budget_targets().copy()
        budget_df.columns = budget_df.columns.str.strip()
        if "KickOff Event Start" in budget_df.columns:
            budget_df.rename(columns={"KickOff Event Start": "KickOffEventStart"}, inplace=True)
        budget_df["KickOffEventStart"] = pd.to_datetime(
            budget_df["KickOffEventStart"], errors="coerce", dayfirst=True
        ).dt.round("min")
        budget_df["Fixture Name"] = budget_df["Fixture Name"].astype(str).str.strip()
        # normalize competition for merge
        budget_df["EventCompetition"] = budget_df.get("EventCompetition", "").astype(str).str.strip()
        if "Budget Target" not in budget_df.columns:
            raise KeyError("Your budget file must have a 'Budget Target' column")
        budget_df["Budget Target"] = (
            budget_df["Budget Target"].replace("[£,]", "", regex=True).astype(float)
        )

        # --- 2️⃣ Prepare and filter sales data ---
        df = filtered_data.copy()
        df.columns = df.columns.str.strip()
        df["Fixture Name"]      = df["Fixture Name"].astype(str).str.strip()
        df["PaymentTime"]       = pd.to_datetime(
            df["PaymentTime"], errors="coerce", dayfirst=True
        )
        df["KickOffEventStart"] = pd.to_datetime(
            df["KickOffEventStart"], errors="coerce", dayfirst=True
        ).dt.round("min")
        df["IsPaid"]            = df["IsPaid"].astype(str).str.upper().fillna("FALSE")
        # filter to concert category then set EventCompetition for merge
        df["EventCategory"]     = df.get("EventCategory", pd.Series()).astype(str).str.strip().str.lower()
        df = df[(df["IsPaid"] == "TRUE") & (df["EventCategory"] == "concert")].copy()
        if df.empty:
            st.warning("⚠️ No paid concert sales to show.")
            return
        # override competition to match budget's 'Concert'
        df["EventCompetition"] = "Concert"
        df = df.drop_duplicates(subset=["Fixture Name", "KickOffEventStart", "EventCompetition"])

        # --- 3️⃣ Merge on all three keys ---
        merged = pd.merge(
            df,
            budget_df[["Fixture Name", "EventCompetition", "KickOffEventStart", "Budget Target"]],
            on=["Fixture Name", "EventCompetition", "KickOffEventStart"],
            how="left",
            validate="m:1"
        )
        missing = merged["Budget Target"].isna().sum()
        if missing:
            st.warning(f"⚠️ {missing} concert rows missing budgets.")

        # --- 4️⃣ Compute effective price & cumulative sums ---
        merged["TotalEffectivePrice"] = np.where(
            merged["TotalPrice"] > 0,
            merged["TotalPrice"],
            merged["DiscountValue"].fillna(0)
        )
        grouped = (
            merged.groupby(["Fixture Name", "PaymentTime"])  
                  .agg(
                      DailySales   = ("TotalEffectivePrice", "sum"),
                      KickOffDate  = ("KickOffEventStart", "first"),
                      BudgetTarget = ("Budget Target", "first"),
                  )
                  .reset_index()
        )
        grouped["CumulativeSales"]   = grouped.groupby("Fixture Name")["DailySales"].cumsum()
        grouped["RevenuePercentage"] = grouped["CumulativeSales"] / grouped["BudgetTarget"] * 100

        # --- 5️⃣ Plot ---
        fixture_colors = {
            "Robbie Williams Live 2025 (Friday)":   'cyan',
            "Robbie Williams Live 2025 (Saturday)": 'magenta'
        }
        fig, ax = plt.subplots(figsize=(16, 10))
        fig.patch.set_facecolor('#121212')
        ax.set_facecolor('#121212')
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')

        now = pd.Timestamp.now()
        for fx, data in grouped.groupby("Fixture Name"):
            color = fixture_colors.get(fx, 'blue')
            data = data.sort_values("PaymentTime")
            kick = data["KickOffDate"].iloc[0]
            pct  = data["RevenuePercentage"].iloc[-1]
            if kick < now:
                label, txt_col = f"{fx} (p, {pct:.0f}%)", 'red'
            else:
                days = (kick - now).days
                label, txt_col = f"{fx} ({days}d, {pct:.0f}%)", 'white'
            ax.plot(data["PaymentTime"].dt.date, data["RevenuePercentage"], label=label, color=color, linewidth=1.5)
            ax.text(data["PaymentTime"].dt.date.iloc[-1], pct, label, fontsize=10, color=txt_col)

        ax.set_title("Concert Cumulative Revenue 24/25", fontsize=12, color='white')
        ax.set_xlabel("Date", color='white')
        ax.set_ylabel("Revenue (% of Budget Target)", color='white')
        ax.axhline(100, color='red', linestyle='--', linewidth=1)

        dates = grouped["PaymentTime"].dt.date
        ax.set_xlim(dates.min(), dates.max())
        span = (dates.max() - dates.min()).days
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2 if span <= 30 else 10))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate()
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x)}%'))

        handles = (
            [plt.Line2D([0], [0], color=fixture_colors.get(fx, 'blue'), lw=2, label=fx)
             for fx in grouped["Fixture Name"].unique()]
            + [plt.Line2D([], [], color='red', linestyle='--', label='Budget Target (100%)')]
        )
        ax.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5, -0.25), frameon=False)

        st.pyplot(fig)

    except Exception as e:
        st.error(f"Failed to generate the concert cumulative chart: {e}")
        logging.error(f"Error in generate_event_level_concert_cumulative_sales_chart: {e}")

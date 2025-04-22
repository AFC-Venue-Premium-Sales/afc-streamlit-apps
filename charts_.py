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
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st

def generate_event_level_men_cumulative_sales_chart(filtered_data):
    """
    Generate a cumulative percentage-to-target sales chart for various competitions.
    Uses KickOffEventStart (rounded to the minute) to align each curve exactly to its fixture,
    and drops duplicates so that a match only appears once (e.g. PSG group vs. PSG semi).
    """
    # 1️⃣ Load and normalize budget targets
    budget_df = load_budget_targets()
    budget_df['KickOffEventStart'] = (
        pd.to_datetime(budget_df['KickOffEventStart'], errors='coerce')
          .dt.round('min')
    )
    budget_df.columns = budget_df.columns.str.strip()

    # 2️⃣ Clean and merge sales data
    filtered_data = filtered_data.copy()
    filtered_data.columns = filtered_data.columns.str.strip()
    filtered_data['EventCompetition'] = filtered_data['EventCompetition'].str.strip()
    filtered_data['Fixture Name'] = filtered_data['Fixture Name'].str.strip()
    # round sale KO to the minute
    filtered_data['KickOffEventStart'] = (
        pd.to_datetime(filtered_data['KickOffEventStart'], errors='coerce')
          .dt.round('min')
    )
    # now drop any duplicate fixtures (same name, competition & KO) so each only charts once
    filtered_data = filtered_data.drop_duplicates(
        subset=['Fixture Name','EventCompetition','KickOffEventStart'],
        keep='first'
    )

    # merge in Budget Target keyed on all three fields
    filtered_data = filtered_data.merge(
        budget_df,
        on=['Fixture Name','EventCompetition','KickOffEventStart'],
        how='left'
    )

    # 3️⃣ Ensure datetimes and paid status
    filtered_data['PaymentTime'] = pd.to_datetime(filtered_data['PaymentTime'], errors='coerce')
    if 'Budget Target' not in filtered_data.columns:
        raise ValueError("The 'Budget Target' column is missing after merge.")
    filtered_data['IsPaid'] = filtered_data['IsPaid'].astype(str).fillna('FALSE').str.upper()

    # 4️⃣ Filter only paid sales and allowed competitions
    allowed = ['Premier League','UEFA Champions League','Carabao Cup','Emirates Cup','FA Cup']
    filtered_data = filtered_data[
        (filtered_data['IsPaid'] == 'TRUE') &
        (filtered_data['EventCompetition'].isin(allowed))
    ].copy()

    # 5️⃣ Exclude discount types
    filtered_data['Discount'] = filtered_data['Discount'].astype(str).str.lower().str.strip()
    bad = ["credit","voucher","gift voucher","discount","pldl"]
    mask = ~filtered_data['Discount'].str.contains('|'.join(map(re.escape,bad)), na=False)
    filtered_data = filtered_data[mask]

    # 6️⃣ Compute effective price
    filtered_data['TotalEffectivePrice'] = np.where(
        filtered_data['TotalPrice'] > 0,
        filtered_data['TotalPrice'],
        np.where(filtered_data['DiscountValue'].notna(), filtered_data['DiscountValue'], 0)
    )

    # 7️⃣ Aggregate by fixture + payment time
    grouped = (
        filtered_data
        .groupby(['Fixture Name','EventCompetition','PaymentTime'])
        .agg(
            DailySales=('TotalEffectivePrice','sum'),
            KickOffDate=('KickOffEventStart','first'),
            BudgetTarget=('Budget Target','first')
        )
        .reset_index()
        .sort_values(['Fixture Name','EventCompetition','PaymentTime'])
    )

    # 8️⃣ Compute cumulative and % of budget
    grouped['CumulativeSales'] = grouped.groupby(
        ['Fixture Name','EventCompetition']
    )['DailySales'].cumsum()
    grouped['RevenuePercentage'] = (
        grouped['CumulativeSales'] / grouped['BudgetTarget'] * 100
    )

    # 9️⃣ Setup plot
    competition_colors = {
        'Premier League':'green','UEFA Champions League':'gold',
        'Carabao Cup':'blue','Emirates Cup':'purple','FA Cup':'pink'
    }
    abbreviations = {
        "Chelsea":"CHE","Tottenham":"TOT","Manchester United":"MANU",
        "West Ham":"WES","Paris Saint-Germain":"PSG","Liverpool":"LIV",
        "Brighton":"BRI","Leicester":"LEI","Wolves":"WOL","Everton":"EVE",
        "Nottingham Forest":"NFO","Aston Villa":"AST",
        "Shakhtar Donetsk":"SHA","Dinamo Zagreb":"DIN","Monaco":"MON","Manchester City":"MCI"
    }

    fig, ax = plt.subplots(figsize=(18,12))
    fig.patch.set_facecolor('#121212'); ax.set_facecolor('#121212')
    ax.tick_params(colors='white'); ax.spines['bottom'].set_color('white'); ax.spines['left'].set_color('white')

    #  🔟 Plot each fixture
    now = pd.Timestamp.now()
    for (fx, comp), d in grouped.groupby(['Fixture Name','EventCompetition']):
        opp = fx.split(' v ')[-1]
        abbr = abbreviations.get(opp, opp[:3].upper())
        color = competition_colors.get(comp,'blue')
        d = d.sort_values('PaymentTime')

        kick = d['KickOffDate'].iloc[0]
        pct = d['RevenuePercentage'].iloc[-1]
        if kick < now:
            label = f"{abbr} ({comp[:3].upper()}, {pct:.0f}%)"
            txt_col = 'red'
        else:
            days = (kick - now).days
            label = f"{abbr} ({comp[:3].upper()}, {days}d, {pct:.0f}%)"
            txt_col = 'white'

        ax.plot(d['PaymentTime'].dt.date, d['RevenuePercentage'], label=label, color=color, linewidth=1)
        ax.text(d['PaymentTime'].dt.date.iloc[-1], pct, label, color=txt_col, fontsize=12)

    # 1️⃣1️⃣ Dynamic x–ticks
    unique = grouped['PaymentTime'].dt.date.nunique()
    if unique <= 5:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    elif unique <= 10:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    else:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    fig.autofmt_xdate(rotation=45, ha='right')

    # 1️⃣2️⃣ Y–axis, legend & styling
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x)}%'))
    handles = [
        plt.Line2D([0],[0],color='green',lw=2,label='Premier League'),
        plt.Line2D([0],[0],color='gold',lw=2,label='Champions League'),
        plt.Line2D([0],[0],color='blue',lw=2,label='Carabao Cup'),
        plt.Line2D([0],[0],color='purple',lw=2,label='Emirates Cup'),
        plt.Line2D([0],[0],color='pink',lw=2,label='FA Cup'),
        plt.Line2D([],[],color='red',linestyle='--',linewidth=2,label='Budget Target (100%)')
    ]
    ax.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5,-0.25),
              fontsize=10, frameon=False, facecolor='black', labelcolor='white', ncol=3)
    ax.set_title("Cumulative Sales as % of Budget", color='white', fontsize=16)
    ax.set_xlabel("Date", color='white', fontsize=14)
    ax.set_ylabel("Revenue (% of Budget Target)", color='white', fontsize=14)
    ax.axhline(100, color='red', linestyle='--', linewidth=1)
    plt.tight_layout()

    # 1️⃣3️⃣ Render in Streamlit
    st.pyplot(fig)




import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st

def generate_event_level_women_cumulative_sales_chart(filtered_data):
    """
    Generate a cumulative percentage-to-target sales chart for Women's competitions.
    Ensures each fixture (name + competition + exact KO minute) only appears once,
    merges on all three keys to pick up the correct budget, and plots cumulative % of target.
    """
    # 1️⃣ Load and prepare budget targets, rounding KO to the minute
    budget_df = load_budget_targets()
    budget_df['KickOffEventStart'] = (
        pd.to_datetime(budget_df['KickOffEventStart'], errors='coerce')
          .dt.round('min')
    )
    budget_df.columns = budget_df.columns.str.strip()
    budget_df['Fixture Name'] = budget_df['Fixture Name'].str.strip()
    budget_df['EventCompetition'] = budget_df['EventCompetition'].str.strip()

    # 2️⃣ Clean incoming sales data
    df = filtered_data.copy()
    df.columns = df.columns.str.strip()
    df['Fixture Name'] = df['Fixture Name'].str.strip()
    df['EventCompetition'] = df['EventCompetition'].str.strip()
    # round KO in the sales feed as well
    df['KickOffEventStart'] = (
        pd.to_datetime(df['KickOffEventStart'], errors='coerce')
          .dt.round('min')
    )
    # drop duplicate rows so each fixture only once
    df = df.drop_duplicates(
        subset=['Fixture Name','EventCompetition','KickOffEventStart'],
        keep='first'
    )

    # 3️⃣ Merge budget into the sales frame on all three keys
    df = df.merge(
        budget_df,
        on=['Fixture Name','EventCompetition','KickOffEventStart'],
        how='left'
    )

    # sanity check
    if 'Budget Target' not in df.columns:
        raise ValueError("Missing 'Budget Target' after merge. Check your keys.")

    # 4️⃣ Convert timestamps and paid flag
    df['PaymentTime'] = pd.to_datetime(df['PaymentTime'], errors='coerce')
    df['IsPaid'] = df['IsPaid'].astype(str).fillna('FALSE').str.upper()

    # 5️⃣ Filter only TRUE payments and women's comps
    allowed = ["Barclays Women's Super League","UEFA Women's Champions League"]
    df = df[
        (df['IsPaid']=='TRUE') &
        (df['EventCompetition'].isin(allowed))
    ].copy()

    # 6️⃣ Exclude unwanted discounts
    df['Discount'] = df['Discount'].astype(str).str.lower().str.strip()
    bad = ["credit","voucher","gift voucher","discount","pldl"]
    mask = ~df['Discount'].str.contains('|'.join(map(re.escape,bad)), na=False)
    df = df[mask]

    # 7️⃣ Compute effective price
    df['TotalEffectivePrice'] = np.where(
        df['TotalPrice']>0,
        df['TotalPrice'],
        np.where(df['DiscountValue'].notna(), df['DiscountValue'], 0)
    )

    # 8️⃣ Group by fixture + payment time
    grouped = (
        df.groupby(['Fixture Name','EventCompetition','PaymentTime'])
          .agg(
              DailySales=('TotalEffectivePrice','sum'),
              KickOffDate=('KickOffEventStart','first'),
              BudgetTarget=('Budget Target','first')
          )
          .reset_index()
          .sort_values(['Fixture Name','PaymentTime'])
    )

    # 9️⃣ Cumulative sums and percentages
    grouped['CumulativeSales'] = grouped.groupby(
        ['Fixture Name','EventCompetition']
    )['DailySales'].cumsum()
    grouped['RevenuePercentage'] = (
        grouped['CumulativeSales']/grouped['BudgetTarget']*100
    )

    # 🔟 Plot setup
    competition_colors = {
        "Barclays Women's Super League": 'green',
        "UEFA Women's Champions League": 'gold'
    }
    abbreviations = {
        "Manchester City Women":"MCW","Everton Women":"EVT","Chelsea Women":"CHE",
        "Vålerenga Women":"VAL","Brighton Women":"BRI","Juventus Women":"JUV",
        "Aston Villa Women":"AST","FC Bayern Munich Women":"BAY",
        "Tottenham Hotspur Women":"TOT","Liverpool Women":"LIVW"
    }

    fig, ax = plt.subplots(figsize=(16,10))
    fig.patch.set_facecolor('#121212'); ax.set_facecolor('#121212')
    ax.tick_params(colors='white'); ax.spines['bottom'].set_color('white'); ax.spines['left'].set_color('white')

    now = pd.Timestamp.now()
    for (fx, comp), d in grouped.groupby(['Fixture Name','EventCompetition']):
        opp = fx.split(' v ')[-1]
        abbr = abbreviations.get(opp, opp[:3].upper())
        color = competition_colors.get(comp,'blue')
        d = d.sort_values('PaymentTime')

        kick = d['KickOffDate'].iloc[0]
        pct = d['RevenuePercentage'].iloc[-1]
        if kick < now:
            label = f"{abbr} (p, {pct:.0f}%)"
            txt_col = 'red'
        else:
            days = (kick-now).days
            label = f"{abbr} ({days}d, {pct:.0f}%)"
            txt_col = 'white'

        ax.plot(d['PaymentTime'].dt.date, d['RevenuePercentage'], color=color, linewidth=1.5, label=label)
        ax.text(d['PaymentTime'].dt.date.iloc[-1], pct, label, color=txt_col, fontsize=10)

    # 1️⃣1️⃣ Dynamic x‑axis ticks
    unique = grouped['PaymentTime'].dt.date.nunique()
    if unique<=5:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    elif unique<=10:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    else:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    fig.autofmt_xdate(rotation=45, ha='right')

    # 1️⃣2️⃣ Final styling
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x,_: f'{int(x)}%'))
    ax.axhline(100, color='red', linestyle='--', linewidth=1)
    handles = [
        plt.Line2D([0],[0],color='green',lw=2,label="WSL"),
        plt.Line2D([0],[0],color='gold',lw=2,label="UWCL"),
        plt.Line2D([],[],color='red',linestyle='--',linewidth=2,label='Budget Target (100%)')
    ]
    ax.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5,-0.2), frameon=False, fontsize=10)
    ax.set_title("AFC Women's Cumulative Revenue 24/25", color='white', fontsize=14)
    ax.set_xlabel("Date", color='white', fontsize=12)
    ax.set_ylabel("Revenue (% of Budget Target)", color='white', fontsize=12)
    plt.tight_layout()

    # 1️⃣3️⃣ Render in Streamlit
    st.pyplot(fig)


    
    
    
    
import re
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st

def generate_event_level_concert_cumulative_sales_chart(filtered_data):
    """
    Generate a cumulative percentage-to-target sales chart for Concert events.
    """
    try:
        # --- 1️⃣ Load & normalize budget targets ---
        budget_df = load_budget_targets()
        # strip whitespace
        budget_df.columns = budget_df.columns.str.strip()
        # if your file calls it something else, rename here:
        if "KickOff Event Start" in budget_df.columns:
            budget_df.rename(columns={"KickOff Event Start": "KickOffEventStart"}, inplace=True)

        budget_df["KickOffEventStart"] = pd.to_datetime(
            budget_df["KickOffEventStart"], errors="coerce", dayfirst=True
        ).dt.round("min")

        # clean keys
        budget_df["Fixture Name"]     = budget_df["Fixture Name"].str.strip()
        budget_df["EventCompetition"] = budget_df["EventCompetition"].str.strip()

        # --- 2️⃣ Prepare your sales feed ---
        df = filtered_data.copy()
        df.columns = df.columns.str.strip()  # strip whitespace
        df["Fixture Name"]     = df["Fixture Name"].str.strip()
        df["EventCompetition"] = df["EventCompetition"].str.strip()
        df["EventCategory"]    = df["EventCategory"].str.strip()

        df["KickOffEventStart"] = pd.to_datetime(
            df["KickOffEventStart"], errors="coerce", dayfirst=True
        ).dt.round("min")

        # drop any accidental duplicates so merge works 1:1
        df = df.drop_duplicates(
            subset=["Fixture Name", "EventCompetition", "KickOffEventStart"], keep="first"
        )

        # --- 3️⃣ Merge on all three keys ---
        df = df.merge(
            budget_df,
            on=["Fixture Name", "EventCompetition", "KickOffEventStart"],
            how="left",
            validate="m:1"
        )

        if "Budget Target" not in df.columns:
            raise KeyError("After merge, 'Budget Target' not found – check your keys!")

        # --- 4️⃣ Parse PaymentTime + filter for paid concerts ---
        df["PaymentTime"] = pd.to_datetime(
            df["PaymentTime"], errors="coerce", dayfirst=True
        )
        df["IsPaid"] = df["IsPaid"].astype(str).str.upper().fillna("FALSE")

        df = df[
            (df["IsPaid"] == "TRUE") &
            (df["EventCategory"].str.lower() == "concert")
        ].copy()

        # --- 5️⃣ Exclude unwanted discounts ---
        df["Discount"] = df["Discount"].astype(str).str.lower()
        bad = ["credit", "voucher", "gift voucher", "discount", "pldl"]
        df = df[~df["Discount"].str.contains("|".join(map(re.escape, bad)), na=False)]

        # --- 6️⃣ Compute your effective price ---
        df["TotalEffectivePrice"] = np.where(
            df["TotalPrice"] > 0,
            df["TotalPrice"],
            np.where(df["DiscountValue"].notna(), df["DiscountValue"], 0)
        )

        # --- 7️⃣ Group & cumulative sums ---
        grouped = (
            df.groupby(["Fixture Name", "EventCompetition", "PaymentTime"])
              .agg(
                  DailySales=('TotalEffectivePrice', 'sum'),
                  KickOffDate=('KickOffEventStart', 'first'),
                  BudgetTarget=('Budget Target', 'first')
              )
              .reset_index()
        )
        grouped["CumulativeSales"] = grouped.groupby(
            ["Fixture Name", "EventCompetition"]
        )["DailySales"].cumsum()
        grouped["RevenuePercentage"] = (
            grouped["CumulativeSales"] / grouped["BudgetTarget"] * 100
        )

        # --- 8️⃣ Plotting ---
        fixture_colors = {
            "Robbie Williams Live 2025 (Friday)": 'cyan',
            "Robbie Williams Live 2025 - Saturday": 'magenta'
        }

        fig, ax = plt.subplots(figsize=(16, 10))
        fig.patch.set_facecolor('#121212')
        ax.set_facecolor('#121212')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
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
                label, txt_col = f"{fx} ({days} days, {pct:.0f}%)", 'white'

            ax.plot(
                data["PaymentTime"].dt.date,
                data["RevenuePercentage"],
                label=label, color=color, linewidth=1.5
            )
            ax.text(
                data["PaymentTime"].dt.date.iloc[-1],
                pct, label, fontsize=10, color=txt_col
            )

        ax.set_title("Concert Cumulative Revenue 24/25", fontsize=12, color='white')
        ax.set_xlabel("Date", fontsize=12, color='white')
        ax.set_ylabel("Revenue (% of Budget Target)", fontsize=12, color='white')
        ax.axhline(y=100, color='red', linestyle='--', linewidth=1)

        # dynamic x‑axis
        min_d = grouped["PaymentTime"].min().date()
        max_d = grouped["PaymentTime"].max().date()
        ax.set_xlim(min_d, max_d)
        span = (max_d - min_d).days
        interval = 2 if span <= 30 else 10
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate()
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x)}%'))

        handles = [
            plt.Line2D([0],[0],color='cyan',      lw=2, label="Robbie Williams Live - Friday"),
            plt.Line2D([0],[0],color='magenta',  lw=2, label="Robbie Williams Live - Saturday"),
            plt.Line2D([],[],  color='red', linestyle='--', linewidth=2, label='Budget Target (100%)'),
        ]
        ax.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5, -0.25),
                  fontsize=10, frameon=False)

        st.pyplot(fig)

    except Exception as e:
        st.error(f"Failed to generate the concert cumulative chart: {e}")
        logging.error(f"Error in generate_event_level_concert_cumulative_sales_chart: {e}")




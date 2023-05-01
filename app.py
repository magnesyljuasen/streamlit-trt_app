import streamlit as st
from PIL import Image
import requests
from streamlit_lottie import st_lottie
import streamlit_authenticator as stauth
import yaml
from datetime import datetime
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder
from streamlit_extras.chart_container import chart_container
from trt import trt
#import hydralit_components as hc
#import time
from docx import Document
from docx.shared import Inches
from docx.enum.style import WD_STYLE_TYPE
import io
import datetime

st.set_page_config(
    page_title="Termisk responstest",
    page_icon="♨️",
    initial_sidebar_state='collapsed'
)

#with hc.HyLoader('', hc.Loaders.standard_loaders,index=[0]):
#    time.sleep(1)

with open("styles/main.css") as f:
    st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)

with open('src/login/config.yaml') as file:
    config = yaml.load(file, Loader=stauth.SafeLoader)

authenticator = stauth.Authenticate(config['credentials'],config['cookie']['name'],config['cookie']['key'],config['cookie']['expiry_days'])
name, authentication_status, username = authenticator.login('Innlogging', 'main')

if authentication_status == False:
    st.error('Ugyldig brukernavn/passord')
elif authentication_status == None:
    c1, c2, c3 = st.columns(3)
    image = Image.open('src/data/img/logo.png')
    st.image(image)
elif authentication_status:
    with st.sidebar:
        authenticator.logout('Logg ut', 'sidebar')
    #--
    st.button("Refresh")
    st.title("En-to-tre TRT")
    st.markdown("---")
    st.header("1️⃣ Inndata")
    project_name = st.text_input("Navn på prosjektet")
    well_placement = st.selectbox("Plassering av brønn", options=["Plasser i kart", "Skriv inn koordinater", "Skriv inn adresse"])
    c1, c2 = st.columns(2)
    if well_placement == "Skriv inn koordinater":
        with c1:
            lat = st.number_input("ØV-koordinat")
        with c2:
            long = st.number_input("NS-koordinat")
    well_id_granada = st.text_input("Brønn ID, GRANADA")
    contact_person = st.text_input("Kontaktperson")
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["Temperaturprofil", "Brønn og kollektor", "Testdata"])
    with tab1:
        df = pd.DataFrame({
            "Dybde [m]" : list(np.arange(0,310,5).ravel()),
            "Temperatur før [°C]" : list(np.zeros(62).ravel()),
            "Temperatur etter [°C]" : list(np.zeros(62).ravel())
            })
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_default_column(editable=True)
        grid_table = AgGrid(
            df,
            height=400,
            gridOptions=gb.build(),
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True,
            key="temperaturprofil",
        )
        grid_table_df = pd.DataFrame(grid_table['data'])
        st.line_chart(data = grid_table_df, y = ["Temperatur før [°C]", "Temperatur etter [°C]"])
    with tab2:
        colletor_type = st.selectbox("Kollektortype", options=["Enkel-U 45 mm", "Enkel-U 40 mm", "Dobbel-U 32 mm"])
        collector_material = st.selectbox("Kollektormateriale", options=["Glatt", "Turbo"])
        collector_length = st.number_input("Kollektorlengde [m]", min_value = 0, value = 300, max_value = 500, step = 10)
        collector_fluid = st.selectbox("Kollektorvæske", options=["HX24", "HX35", "Kilfrost GEO"])
        diameter_casing = st.number_input("Diameter fôringsrør [mm]", value = 139)
        diameter_borehole = st.number_input("Borehullsdiameter [mm]", value = 115)
        groundwater_table = st.number_input("Grunnvannstand [m]")
    with tab3:
        testdata_file = st.file_uploader("Last opp testdata")
        if not testdata_file:
            st.stop()
    st.markdown("---")
    st.header("2️⃣ Analyse av termisk responstest")
    df = pd.read_csv(testdata_file, sep = ',', skiprows = 3)
    df = df.iloc[:,[0,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,25,26,28]]
    df = df.rename(columns={
        'Unnamed: 0':'Tidspunkt',
        'Smp.3' :'Panel pipe length',
        'Smp.4' : 'RA_temp(1), Tr_bPump',
        'Smp.5' : 'RA_temp(2), Tr_aPump',
        'Smp.6' : 'RA_temp(3), Theat',
        'Smp.7' : 'RA_temp(4), T_in',
        'Smp.8' : 'RA_temp(5), T_air',
        'Smp.9' : 'Flow',
        'Smp.10' : 'Pump speed',
        'Smp.11' : 'Panel heat',
        'Smp.12' : 'Test_Run',
        'Smp.13' : 'Test_Done',
        'Smp.14' : 'Purge',
        'Smp.15' : 'Purge_Done',
        'Smp.16' : 'Heating',
        'Smp.17' : 'Heating_Done',
        'Smp.18' : 'Cooling',
        'Smp.19' : 'Cooling_Done',
        'Smp.20' : 'Heat_Enabled',
        'Smp.21' : 'Pump_Enabled',
        'Smp.23' : 'Pause_Mode',
        'Smp.24' : 'Mains_Fail',
        'Smp.26' : 'E_Stop',
        })
    matching_rows = df.loc[df['Test_Done'] == -1].index
    test_namelist = []
    test_startrowlist = []
    test_endrowlist = []
    for i in range(1, len(matching_rows)):
        start = matching_rows[i-1] + 10
        stop = matching_rows[i]
        test_df = df.iloc[start:stop]
        if len(test_df) > 1000:
            date_start = test_df['Tidspunkt'][start].split()[0]     
            date_stop = test_df['Tidspunkt'][stop-1].split()[0]
            timestamp_start = f"{date_start.split('-')[2]}/{date_start.split('-')[1]}"
            timestamp_stop = f"{date_stop.split('-')[2]}/{date_stop.split('-')[1]}"
            timestamp_str = f"{timestamp_start} til {timestamp_stop}"
            test_namelist.append(f"{timestamp_str}")
            test_startrowlist.append(start)
            test_endrowlist.append(stop)
    #--
    selected_test = st.selectbox("Velg test", options = test_namelist)
    selected_test_index = test_namelist.index(selected_test)
    selected_df = df.iloc[test_startrowlist[selected_test_index]:test_endrowlist[selected_test_index]]
    with chart_container(selected_df):
        st.line_chart(data = selected_df, y = ["RA_temp(1), Tr_bPump", "RA_temp(2), Tr_aPump"])
    with st.expander("Effektiv varmledningsevne"):
        st.write("Matematikk...")
        st.write("Figur...")
    with st.expander("Termisk borehullsmotstand"):
        st.write("Matematikk...")
        st.write("Figur...")
    with st.expander("Temperaturer"):
        st.write("Matematikk...")
        st.write("Figur...")
    #--
    thermal_conductivity = 3.5
    borehole_thermal_resistance = 0.08
    undisturbed_groundtemperature = 8
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Effektiv varmeledningsevne", value = f"{thermal_conductivity} W/m*K")
    with c2:
        st.metric("Termisk borehullsmotstand", value = f"{borehole_thermal_resistance} m*K/W")
    with c3:
        st.metric("Uforstyrret temperatur", value = f"{undisturbed_groundtemperature} °C")
    st.markdown("---")

    document = Document("src/data/docx/Rapportmal.docx")
    styles = document.styles
    style = styles.add_style('Citation', WD_STYLE_TYPE.PARAGRAPH)

    st.header("3️⃣ Til rapport (og database)")
    c1, c2 = st.columns(2)
    with st.form("Inndata"):
        with c1:
            TITTEL = st.text_input("Tittel", value = f"Termisk responstest - {project_name}")
            OPPDRAGSNAVN = st.text_input("Oppdragsnavn", value = f"Termisk responstest - {project_name}")
            OPPDRAGSGIVER = st.text_input("Oppdragsgiver", placeholder= "Båsum Boring")
            OPPDRAGSNUMMER = st.text_input("Oppdragsnummer", placeholder= "630962-01")
        with c2:
            FORFATTER = st.selectbox("Utarbeidet av", options = ["Johanne Strålberg", "Sofie Hartvigsen", "Magne Syljuåsen", "Henrik Holmberg", "Randi Kalskin Ramstad"])
            OPPDRAGSLEDER = st.selectbox("Oppdragsleder", options = ["Johanne Strålberg", "Sofie Hartvigsen", "Magne Syljuåsen", "Henrik Holmberg", "Randi Kalskin Ramstad"])
            KVALITETSSIKRER = st.selectbox("Kvalitetssikrer", options = ["Magne Syljuåsen", "Henrik Holmberg", "Randi Kalskin Ramstad", "Johanne Strålberg", "Sofie Hartvigsen"])
        st.form_submit_button("Gi input")

    document.paragraphs[1].text = f"Oppdragsgiver:      {OPPDRAGSGIVER}"
    document.paragraphs[2].text = f"Oppdragsgiver:      {OPPDRAGSGIVER}"
    document.paragraphs[3].text = f"Tittel på rapport:      {OPPDRAGSNAVN}"
    document.paragraphs[4].text = f"Tittel på rapport:      {OPPDRAGSNAVN}"
    st.write("---")

    #--
    bio = io.BytesIO()
    document.save(bio)
    if document:
        st.download_button(
            label="Last ned rapport!",
            data=bio.getvalue(),
            file_name="Rapport.docx",
            mime="docx")

    
            
            
    
    
    
    
    



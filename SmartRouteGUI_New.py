import streamlit as st
import pandas as pd
import numpy as np
import base64, os, argparse
import streamlit.components.v1 as components
import gmplot, googlemaps
import collections, sys, subprocess
from fpdf import FPDF
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from datetime import datetime

st.set_page_config(page_title="Smart Route",layout='wide')
st.title("Smart Route")

# Default data to load 

df = pd.read_csv('./SmartRoute_Data.csv')
start = 0
num_vehicles = 10

#Layout design

# input_panel = st.sidebar()
gmap, gdata = st.columns([2, 1])
download, inputs = st.columns([1, 1]) 

# Load defaults

download, inputs = st.columns([1, 1])

with st.sidebar:
    st.sidebar.title(":blue[Options]")
    uploaded_file = st.file_uploader("\n:blue[Upload your input file here...]", type=['csv'])
    if uploaded_file is not None:
        file_details = {"FileName":uploaded_file.name,"FileType":uploaded_file.type}
        try:
            with open(os.path.join(".",uploaded_file.name),"wb") as f: #Save file to remote
                f.write(uploaded_file.getbuffer())         
            st.success('File uploaded!', icon="✅")
        except:
            st.error('File error', icon="🚨")
        # file = st.file_uploader("\n:blue[Please choose a file]")
        df = pd.read_csv(uploaded_file)
        df.to_csv('./SmartRoute_Data.csv', index=False)
        start = st.slider("\n:blue[Choose starting station]", 0, df.shape[0]-1)
        num_vehicles = st.slider("\n:blue[No. of vehicles]", 1, 10, 1)
        if st.sidebar.button("Click to Recalibrate"):
            with st.spinner('Wait for it...'):
                results = subprocess.run([f"{sys.executable}", "SmartRoute.py", str(num_vehicles), str(start), 'SmartRoute_Data.csv'])
                if results.returncode == 0:
                    st.success('Route details recalculated!!')
                else:
                    st.error('Recalibration failed!')

with gdata:
    st.header("_Route Input Data_")
    st.write("\n", df)

with gmap:
    st.header("_Google Route Map_")
    with open("./GoogleRouteMap.html",'r') as f: 
        html_data = f.read()
        HtmlFile = open('./GoogleRouteMap.html', 'r')
        raw_html = HtmlFile.read().encode("utf-8")
        raw_html = base64.b64encode(raw_html).decode()
        components.iframe(f"data:text/html;base64,{raw_html}", height=750)

with download:
    my_expander = st.expander("", expanded=True)
    with my_expander:
        st.write("You can find more details in :blue[RouteDetails.pdf]")

        with open("RouteDetails.pdf", "rb") as pdf_file:
            PDFbyte = pdf_file.read()

        st.download_button(label="Click to Download file",
                            data=PDFbyte,
                            file_name="RouteDetails.pdf",
                            mime='application/octet-stream')
# with inputs:
#     my_expander = st.expander("Options Choosen", expanded=True)
#     with my_expander:
#         st.write(":blue[_Starting Point_]: ", df.iloc[start])
#         st.write(":blue[_No. of vehicles_]: ", num_vehicles)
#         st.write(":blue[Start ID]: ", start)
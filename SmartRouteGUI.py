import streamlit as st
import pandas as pd
import numpy as np
import base64, os
import streamlit.components.v1 as components
import gmplot, googlemaps
import collections
from fpdf import FPDF
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from datetime import datetime

st.set_page_config(page_title="Smart Route",layout='wide')
st.title("Smart Route")

df = pd.read_csv('./SmartRoute_Data.csv')
start = 0
num_vehicles = 10

gmap, gdata = st.columns([3, 1])

class SmartRoute:
    def __init__(self, inputFile, num_vehicles=10, start=0) -> None:
        self.num_vehicles = num_vehicles
        self.start = start
        self.api_key = "AIzaSyCV8epBs51Sa5AwVvqTE4pdZzD84337XQA" # Key in your API Key
        # self.api_key = "" # Key in your API Key
        self.inputFile = inputFile
        self.gmaps = googlemaps.Client(key=self.api_key)
        self.flag = False

    def distance_callback(self, from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return dist_matrix[from_node][to_node]

    def read_file(self) -> tuple:
        lat_long_file = pd.read_csv(self.inputFile)[["Latitude", "Longitude"]][:5]
        source = lat_long_file.iloc[0].to_numpy()
        coords = lat_long_file[["Latitude", "Longitude"]].to_numpy()
        return (source, coords, lat_long_file)
    
    def __get_dist_time_values__(self, pt1, pt2):
        elements = self.gmaps.distance_matrix(pt1, pt2, mode="driving")["rows"][0][
            "elements"
        ][0]
        d = elements["distance"]["value"] / 1000  # in Kilometer
        t = round(elements["duration"]["value"] / (60 * 60), 1)  # in Hours
        return d, t
    
    def create_distance_time_matrix(self, lat_long):
        tmp1 = 0
        tmp2 = 1
        n = lat_long.shape[0]
        dist_matrix = np.zeros((n, n))
        time_matrix = np.zeros((n, n))
        val = lat_long.values
        for i, (v1, v2) in enumerate(val[tmp1:]):
            try:
                d, t = zip(
                    *[
                        self.__get_dist_time_values__((v1, v2), (v3, v4))
                        for v3, v4 in val[tmp2 + tmp1 :]
                    ]
                )
                d = np.insert(d, 0, 0)
                t = np.insert(t, 0, 0)
            except:
                d = 0
                t = 0
            dist_matrix[i, i:] = d
            dist_matrix[i:, i] = d
            time_matrix[i, i:] = t
            time_matrix[i:, i] = t
            tmp2 = 1
            tmp1 += 1
        return dist_matrix, time_matrix
    
    def get_routes(self, solution):
        """Get vehicle routes from a solution and store them in an array."""
        # Get vehicle routes and store them in a two dimensional array whose
        # i,j entry is the jth location visited by vehicle i along its route.
        routes = []
        single_route_dist = {}
        for route_nbr in range(routing.vehicles()):
            index = routing.Start(route_nbr)
            route = [manager.IndexToNode(index)]
            route_distance = 0
            while not routing.IsEnd(index):
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route.append(manager.IndexToNode(index))
                route_distance += routing.GetArcCostForVehicle(
                    previous_index, index, route_nbr
                )
                single_route_dist[route_nbr] = route_distance
            if (np.size(route) - 2) != 0:
                routes.append(route)
            else:
                self.flag = True
        # dist = dist_travelled(routing, solution)
        return routes, single_route_dist

    def genGoogleMap(self, source, coords, routes):
        gmap = gmplot.GoogleMapPlotter(source[0], source[1], 13, apikey=self.api_key)
        waypoints = [coords[i] for i in routes]
        for i in range(len(waypoints)):
            gmap.directions(
                (source[0], source[1]),
                (source[0], source[1]),
                waypoints=waypoints[i],
                units="metric",
            )

        gmap.draw("GoogleRouteMap.html")
        return

    def createPDF(self, single_route_dist):
        route_data_details = collections.defaultdict(dict)
        for i, route in enumerate(routes):
            route_data_details[i]["Route"] = route
            route_data_details[i]["Drops"] = len(route) - 2
            route_data_details[i]["Distance"] = single_route_dist[i]
            time = 0
            for j in range(np.size(route) - 1):
                time += time_matrix[route[j]][route[j + 1]]
            route_data_details[i]["Time"] = round(time, 1)
        pdf = FPDF("P", "mm", "A4")
        pdf.add_page()
        now = datetime.now()
        myStr = now.strftime("%d-%b-%Y %H:%M:%S")
        pdf.set_font("Times", style="B", size=4)
        pdf.cell(200, 10, txt=myStr, border=0, ln=1, align="L")
        pdf.set_font("Courier", style="BU", size=16)
        pdf.cell(200, 10, txt="Route Plan Details", border=0, ln=1, align="C")
        pdf.cell(200, 10, txt="", border=0, ln=1, align="C")
        pdf.set_font("Arial", style="BU", size=10)
        pdf.cell(200, 10, txt="Summary Report:", border=0, ln=1, align="L")
        pdf.cell(200, 10, txt="", border=0, ln=1, align="L")
        drops_max = max(
            [route_data_details[i]["Drops"] for i in range(np.size(route_data_details))]
        )
        if self.flag:
            pdf.set_font("Arial", style="", size=8)
            myStr = "Suggested no. of vehicles: " + str(np.size(route_data_details))
            pdf.cell(200, 10, txt=myStr, border=0, ln=1, align="L")
        for k, v in route_data_details.items():
            myStr = (
                "Vehicle ID: "
                + str(k + 1)
                + " travelled a distance of "
                + str(v["Distance"])
                + " km and made "
                + str(v["Drops"])
                + " drops"
                + " taking "
                + str(v["Time"])
                + " hrs to complete the trip."
            )
            pdf.cell(200, 10, txt=myStr, border=0, ln=1, align="L")
        pdf.cell(200, 10, txt="", border=0, ln=1, align="L")
        myStr = (
            "Max  distance travelled: "
            + str(max(single_route_dist.values()))
            + " km by Vehicle IDs: "
            + str(
                [
                    k + 1
                    for k, v in single_route_dist.items()
                    if v == max(single_route_dist.values())
                ]
            )
        )
        pdf.cell(200, 10, txt=myStr, border=0, ln=1, align="L")
        myStr = (
            "Max drops made: "
            + str(drops_max)
            + " by Vehicle IDs: "
            + str(
                [
                    i + 1
                    for i in range(np.size(route_data_details))
                    if route_data_details[i]["Drops"] == drops_max
                ]
            )
        )
        pdf.cell(200, 10, txt=myStr, border=0, ln=1, align="L")
        myStr = (
            "Total distance covered: " + str(sum(single_route_dist.values())) + " km"
        )
        pdf.cell(200, 10, txt=myStr, border=0, ln=1, align="L")
        myStr = "Total drops made: " + str(
            sum(
                [route_data_details[i]["Drops"] for i in range(np.size(route_data_details))]
            )
        )
        pdf.cell(200, 10, txt=myStr, border=0, ln=1, align="L")
        pdf.add_page()
        pdf.set_font("Arial", style="BU", size=10)
        pdf.cell(200, 10, txt="Route Details:", border=0, ln=1, align="L")
        pdf.cell(200, 10, txt="", border=0, ln=1, align="L")
        for k in range(np.size(route_data_details)):
            pdf.set_font("Arial", style="B", size=8)
            myStr = "Vehicle ID: " + str(k + 1) + " route plan"
            pdf.cell(200, 10, txt=myStr, border=0, ln=1, align="L")
            loc = coords[route_data_details[k]["Route"]]
            plan = [
                sr.gmaps.reverse_geocode((i[0], i[1]))[0]["formatted_address"]
                for i in loc
            ]
            pdf.set_font("Arial", style="", size=8)
            r = [
                dist_matrix[route_data_details[k]["Route"][j]][
                    route_data_details[k]["Route"][j + 1]
                ]
                for j in range(np.size(route_data_details[k]["Route"]) - 1)
            ]
            r.insert(0, 0)
            t = [
                time_matrix[route_data_details[k]["Route"][j]][
                    route_data_details[k]["Route"][j + 1]
                ]
                for j in range(np.size(route_data_details[k]["Route"]) - 1)
            ]
            t.insert(0, 0)
            for n, (i, j, x) in enumerate(zip(plan, r, t)):
                myStr = (
                    str(n + 1)
                    + " - "
                    + str(i)
                    + " (Distance: "
                    + str(j)
                    + " km"
                    + " Time: "
                    + str(x)
                    + " hrs)"
                )
                pdf.cell(200, 10, txt=myStr, border=0, ln=1, align="L")
                # pdf.multi_cell(200, 10, txt = myStr)
            pdf.cell(200, 10, txt="", border=0, ln=1, align="L")
            myStr = (
                "Distance travelled: " + str(route_data_details[k]["Distance"]) + " km"
            )
            pdf.cell(200, 10, txt=myStr, border=0, ln=1, align="L")
            myStr = "Time of travel: " + str(route_data_details[k]["Time"]) + " hrs"
            pdf.cell(200, 10, txt=myStr, border=0, ln=1, align="L")
            pdf.cell(200, 10, txt="", border=0, ln=1, align="L")
            # pdf.add_page()
        pdf.output("RouteDetails.pdf", "F")

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
        start = st.slider("\n:blue[Choose starting station]", 1, df.shape[0], 1)
        num_vehicles = st.slider("\n:blue[No. of vehicles]", 1, 10, 1)
        if st.sidebar.button("Click to Recalibrate"):
            # st.write('Hello!')
            sr = SmartRoute(
                inputFile='./' + uploaded_file.name,
                num_vehicles=num_vehicles,
                start=start,
            )
            source, coords, lat_long = sr.read_file()
            dist_matrix, time_matrix = sr.create_distance_time_matrix(lat_long)
            manager = pywrapcp.RoutingIndexManager(dist_matrix.shape[0], num_vehicles, start)
            routing = pywrapcp.RoutingModel(manager)
            transit_callback_index = routing.RegisterTransitCallback(sr.distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            dimension_name = "Distance"
            routing.AddDimension(
                transit_callback_index,
                90,  # Slack of 90 min; 0 means no slack
                10000,  # vehicle maximum travel distance
                True,  # start cumul to zero
                dimension_name,
            )
            distance_dimension = routing.GetDimensionOrDie(dimension_name)
            distance_dimension.SetGlobalSpanCostCoefficient(100)
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
            search_parameters.time_limit.seconds = 30
            search_parameters.log_search = True
            data = {}
            data["distance_matrix"] = dist_matrix
            data["num_vehicles"] = num_vehicles
            data["depot"] = start
            solution = routing.SolveWithParameters(search_parameters)
            if solution:
                routes, single_route_dist = sr.get_routes(solution)
                single_route_dist = {k: v for k, v in single_route_dist.items() if v != 0}
                single_route_dist = {
                    i: v for i, v in enumerate(single_route_dist.values())
                }  # Reset the keys
                sr.genGoogleMap(source, coords, routes)
                sr.createPDF(single_route_dist)
        

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

download, inputs = st.columns([1, 1])

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
with inputs:
    my_expander = st.expander("Options Choosen", expanded=True)
    with my_expander:
        st.write(":blue[_Starting Point_]: ", df.iloc[start-1])
        st.write(":blue[_No. of vehicles_]: ", num_vehicles)


# st.write("\n", start-1)

# map.line_chart(data1)

# data.subheader("A narrow column with the data")
# data.write(data1)

# my_expander = st.expander("", expanded=True)
# with my_expander:
#     with open("/home/rvcsekar/Python_Projects/SmartRoute/GoogleRouteMap.html",'r') as f: 
#         html_data = f.read()
#     HtmlFile = open('/home/rvcsekar/Python_Projects/SmartRoute/GoogleRouteMap.html', 'r')
#     raw_html = HtmlFile.read().encode("utf-8")
#     raw_html = base64.b64encode(raw_html).decode()
#     components.iframe(f"data:text/html;base64,{raw_html}")

# # with st.container():
# #     with open("/home/rvcsekar/Python_Projects/SmartRoute/GoogleRouteMap.html",'r') as f: 
# #         html_data = f.read()
# #     HtmlFile = open('/home/rvcsekar/Python_Projects/SmartRoute/GoogleRouteMap.html', 'r')
# #     raw_html = HtmlFile.read().encode("utf-8")
# #     raw_html = base64.b64encode(raw_html).decode()
# #     components.iframe(f"data:text/html;base64,{raw_html}", width=1000)

# with st.sidebar:
#     st.sidebar.title(":blue[Options]")
#     file = st.file_uploader("\n:blue[Please choose a file]")
#     df = pd.read_csv(file, index_col=[0])
#     len = df.shape[0]
#     start = st.slider("\n:blue[Choose starting station]", 1, len)
#     num_vehicles = st.slider("\n:blue[No. of vehicles]", 1, 10)
    
    

   
# # st.write("\n", df)
# # st.write("\n", start-1)
    
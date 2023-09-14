import numpy as np
import pandas as pd
import gmplot, googlemaps
import collections
from fpdf import FPDF
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from datetime import datetime

class SmartRoute:
    def __init__(self, inputFile, num_vehicles=10, start=0) -> None:
        self.num_vehicles = num_vehicles
        self.start = start
        self.api_key = "AIzaSyCV8epBs51Sa5AwVvqTE4pdZzD84337XQA"
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
        lat_long_file = pd.read_csv(self.inputFile)[["Latitude", "Longitude"]][:10]
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
        n = len(lat_long)
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
            if len(route) - 2 != 0:
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
            for j in range(len(route) - 1):
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
            [route_data_details[i]["Drops"] for i in range(len(route_data_details))]
        )
        if self.flag:
            pdf.set_font("Arial", style="", size=8)
            myStr = "Suggested no. of vehicles: " + str(len(route_data_details))
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
                    for i in range(len(route_data_details))
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
                [route_data_details[i]["Drops"] for i in range(len(route_data_details))]
            )
        )
        pdf.cell(200, 10, txt=myStr, border=0, ln=1, align="L")
        pdf.add_page()
        pdf.set_font("Arial", style="BU", size=10)
        pdf.cell(200, 10, txt="Route Details:", border=0, ln=1, align="L")
        pdf.cell(200, 10, txt="", border=0, ln=1, align="L")
        for k in range(len(route_data_details)):
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
                for j in range(len(route_data_details[k]["Route"]) - 1)
            ]
            r.insert(0, 0)
            t = [
                time_matrix[route_data_details[k]["Route"][j]][
                    route_data_details[k]["Route"][j + 1]
                ]
                for j in range(len(route_data_details[k]["Route"]) - 1)
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


if __name__ == "__main__":
    num_vehicles = 10
    start = 0
    sr = SmartRoute(
        inputFile="/home/rvcsekar/Code_Development/MyGitRepository/SmartRoute/SmartRoute_Data.csv",
        num_vehicles=num_vehicles,
        start=start,
    )
    source, coords, lat_long = sr.read_file()
    dist_matrix, time_matrix = sr.create_distance_time_matrix(lat_long)
    manager = pywrapcp.RoutingIndexManager(len(dist_matrix), num_vehicles, start)
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
    else:
        print("No solution found !")


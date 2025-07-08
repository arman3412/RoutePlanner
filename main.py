from datetime import datetime, timedelta, time
from itertools import permutations
from tkinter import ttk, messagebox
import tkinter as tk
import googlemaps
import requests
from config import API_KEY

gmaps = googlemaps.Client(API_KEY)

# Gets the distance matrix given the addresses and the intended travel mode
def get_routes_data_as_distance_matrix(addresses: dict[str, tuple], travel_mode: str) -> list[list[tuple[int, int]]]:
    url = 'https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix'
    # Define the origins and destinations as per the API format
    origins = []
    geoceded_addresses = [address_values[0] for address_values in addresses.values()]
    # Create origin/destination in proper format for request
    for geocode_result in geoceded_addresses:
        if geocode_result:
            lat_lng = geocode_result[0]["geometry"]["location"] # Convert geocoded location into lattitude and longitude
            waypoint = {
                "waypoint": {
                    "location": {
                        "latLng": {
                            "latitude": lat_lng["lat"],
                            "longitude": lat_lng["lng"]
                        }
                    }
                }
            }
            origins.append(waypoint)
    # Headers for request
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': API_KEY,
        'X-Goog-FieldMask': 'originIndex,destinationIndex,duration,distanceMeters,status,condition'
    }

    # Prepare the payload for the request
    payload = {
        "origins": origins,
        "destinations": origins,
        "travelMode": travel_mode,  
        "routingPreference": "TRAFFIC_AWARE"
    }

    routes_data = requests.post(url, headers=headers, json=payload).json() # Requests route information between each location from google maps

    distance_matrix = [[None for _ in range(len(addresses))] for _ in range(len(addresses))] # Initialize a 2d list with the amount of addresses as the size

    for entry in routes_data:
        origin = entry["originIndex"] # Gives origin index that data should be in e.g. 1
        destination = entry["destinationIndex"] # Gives destination index that data should be in e.g. 3

        distance = entry.get("distanceMeters", 0) # Gives distance as number e.g. 88391, default to 0
        duration = int(entry.get("duration", "0s")[:-1]) # Converts duration from string to integer

        distance_matrix[origin][destination] = (distance, duration)
    
    return distance_matrix

# Gets every possible path given a set of addresses, their distance matrix, and whether 
# we are looking for minimizing distance or time
# Returns dict(list : tuple)
def get_paths(distance_matrix: list[list[tuple[int, int]]], 
              addresses: dict[str, tuple], 
              using_time: bool, 
              same_ending: bool, 
              starting_time) -> dict[tuple[str, ...], float]:
    index = 1 if using_time else 0 # Access time (index 1) if using time, else access distance (index 0)
    paths = {}  # Stores paths and their corresponding travel metric
    address_names = list(addresses.keys())
    address_values = list(addresses.values())
    num_locations = len(address_names)  # Total number of locations including start & end
    
    if same_ending:
        ending_index = 0 # Access the starting location for the ending location
        intermediate_indices = range(1, num_locations) 
    else:
        ending_index = -1 # Access the last location for the ending location
        intermediate_indices = range(1, num_locations - 1)

    # Generate all possible permutations of the intermediate locations e.g. perm = (2, 1, 3)
    for perm in permutations(intermediate_indices):
        if using_time:
            travel_metric = timedelta(seconds=0)
        else:
            travel_metric = 0 # Reset travel metric
        prev = 0  # Start at the first location
        path_name = [address_names[0]]
        time = starting_time
        on_time = True

        for loc in perm:  # Visit intermediate locations in this order
            closing_time = address_values[loc][2]
            staying_time = address_values[loc][1]
            if closing_time: # Handle case that the place doesn't have a closing time
                time += timedelta(seconds=distance_matrix[prev][loc][1]) # Add time it takes to get from prev to loc
                time += staying_time  # Access time_staying
                if time.time() > closing_time: # Access closing_time
                    on_time = False

            path_name.append(address_names[loc])
            if using_time:
                travel_metric += timedelta(seconds=distance_matrix[prev][loc][index])
            else:
                travel_metric += distance_matrix[prev][loc][index]
            prev = loc
        if using_time:
            travel_metric += timedelta(seconds=distance_matrix[prev][ending_index][index])  # Final step to end location
        else:
            travel_metric += distance_matrix[prev][ending_index][index]
        # Construct path name, only add if we are on time to each place
        if on_time:
            path_name.append(address_names[ending_index])
            paths[tuple(path_name)] = travel_metric, time

    return paths

def find_shortest_path(paths: dict[tuple[str, ...], float]) -> tuple[tuple[str, ...], float]:
    sorted_paths = sorted(paths.items(), key=lambda x: x[1]) # Sorts paths by value instead of key
    return sorted_paths[0] # Gets first key and value of dictionary as a tuple


class RoutePlannerGUI:
    # Create GUI
    def __init__(self, root):
        self.root = root
        root.title("Route Planner")
        
        # Main frame for all inputs
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Starting location
        ttk.Label(self.main_frame, text="Enter your starting location:").grid(row=0, column=0, sticky="w")
        self.start_entry = ttk.Entry(self.main_frame, width=50)
        self.start_entry.grid(row=0, column=1, pady=2)
        
        # Intermediate locations (4 sets)
        self.intermediate_entries = []
        ordinal_numbers = ["second", "third", "fourth", "fifth"]
        for i in range(4):
            base_row = 1 + i * 3
            ttk.Label(self.main_frame, text=f"Enter your {ordinal_numbers[i]} location:").grid(row=base_row, column=0, sticky="w")
            loc_entry = ttk.Entry(self.main_frame, width=50)
            loc_entry.grid(row=base_row, column=1, pady=2)
            
            ttk.Label(self.main_frame, text="What time does this place close? (HH:MM) Leave blank if it doesn't close:").grid(row=base_row+1, column=0, sticky="w")
            close_entry = ttk.Entry(self.main_frame, width=20)
            close_entry.grid(row=base_row+1, column=1, sticky="w", pady=2)
            
            ttk.Label(self.main_frame, text="How long will you be staying? (HH:MM)").grid(row=base_row+2, column=0, sticky="w")
            stay_entry = ttk.Entry(self.main_frame, width=20)
            stay_entry.grid(row=base_row+2, column=1, sticky="w", pady=2)
            
            self.intermediate_entries.append((loc_entry, close_entry, stay_entry))
        
        # Ending location
        ttk.Label(self.main_frame, text="Enter your ending location:").grid(row=14, column=0, sticky="w")
        self.end_entry = ttk.Entry(self.main_frame, width=50)
        self.end_entry.grid(row=14, column=1, pady=2)
        
        # Checkbox: if ending location is same as starting
        self.same_ending = tk.BooleanVar(value=False)
        self.same_check = ttk.Checkbutton(self.main_frame, text="Check if you want your ending location to be the same as your starting location", 
                                          variable=self.same_ending, command=self.toggle_end_entry)
        self.same_check.grid(row=15, column=1, sticky="w", pady=2)
        
        # Travel Method
        ttk.Label(self.main_frame, text="Enter your travel method:").grid(row=16, column=0, sticky="w")
        self.travel_method = tk.StringVar(value="DRIVE")  # Deafault travel method is drive
        self.method_dropdown = ttk.OptionMenu(self.main_frame, self.travel_method, "DRIVE", "BICYCLE", "DRIVE", "TRANSIT", "WALK")
        self.method_dropdown.grid(row=16, column=1, sticky="w", pady=2)
        
        # Minimization Choice
        ttk.Label(self.main_frame, text="Would you like your route to minimize distance or time?").grid(row=17, column=0, sticky="w")
        self.minimize_choice = tk.StringVar(value="2")
        rb_distance = ttk.Radiobutton(self.main_frame, text="Minimize Distance", variable=self.minimize_choice, value="1")
        rb_time = ttk.Radiobutton(self.main_frame, text="Minimize Time", variable=self.minimize_choice, value="2")
        rb_distance.grid(row=17, column=1, sticky="w")
        rb_time.grid(row=17, column=1, padx=150, sticky="w")
        
        # Starting Time
        ttk.Label(self.main_frame, text="What time do you want your route to begin (HH:MM)? Enter 0 if you want it to start now:").grid(row=18, column=0, sticky="w")
        self.start_time_entry = ttk.Entry(self.main_frame, width=20)
        self.start_time_entry.insert(0, "0")
        self.start_time_entry.grid(row=18, column=1, sticky="w", pady=2)
        
        # Calculate Route Button
        self.calc_button = ttk.Button(self.main_frame, text="Calculate Route", command=self.calculate_route)
        self.calc_button.grid(row=19, column=0, columnspan=2, pady=10)
        
        # Output area
        self.output_text = tk.Text(root, height=10, width=80)
        self.output_text.grid(row=1, column=0, pady=10)
    
    def toggle_end_entry(self):
        if self.same_ending.get():
            self.end_entry.delete(0, tk.END)
            self.end_entry.config(state="disabled")
        else:
            self.end_entry.config(state="normal")
    
    def calculate_route(self):
        # Gather inputs
    
        # Starting location
        start_loc = self.start_entry.get().strip()
        if not start_loc:
            messagebox.showerror("Error", "Enter your starting location.")
            return
        
        # Build addresses dictionary
        addresses = {}
        # Get starting geocode and add to dictionary
        geocode_start = gmaps.geocode(start_loc)
        if not geocode_start:
            messagebox.showerror("Error", f"Starting location '{start_loc}' is invalid.")
            return
        addresses[start_loc] = (geocode_start, timedelta(seconds=0), None)
        
        # Intermediate locations, location, closing time and staying time
        for (loc_entry, close_entry, stay_entry) in self.intermediate_entries:
            loc = loc_entry.get().strip() 
            if loc: 
                geocode_loc = gmaps.geocode(loc)
                if not geocode_loc:
                    messagebox.showerror("Error", f"Intermediate location '{loc}' is invalid.")
                    return
                # Process closing time
                close_str = close_entry.get().strip()
                if close_str == "0" or close_str == "":
                    closing_time = None
                else:
                    try:
                        closing_time = datetime.strptime(close_str + ":00", "%H:%M:%S").time() # Datetime need seconds as well
                    except ValueError:
                        messagebox.showerror("Error", f"Invalid closing time for '{loc}'.")
                        return
                # Process staying time
                stay_str = stay_entry.get().strip()
                if stay_str == "0" or stay_str == "":
                    stay_time = timedelta(seconds=0)
                else:
                    try:
                        stay_str += ":00" # Add seconds
                        h, m, s = map(int, stay_str.split(":"))
                        stay_time = timedelta(hours=h, minutes=m, seconds=s)
                    except ValueError:
                        messagebox.showerror("Error", f"Invalid staying duration for '{loc}'.")
                        return
                addresses[loc] = (geocode_loc, stay_time, closing_time) 
        
        # Ending location
        if self.same_ending.get():
            end_loc = start_loc
            same_ending = True
        else:
            end_loc = self.end_entry.get().strip()
            if not end_loc:
                messagebox.showerror("Error", "Enter your ending location")
                return
            same_ending = False
        geocode_end = gmaps.geocode(end_loc)
        if not geocode_end:
            messagebox.showerror("Error", f"Ending location '{end_loc}' is invalid.")
            return
        addresses[end_loc] = (geocode_end, timedelta(seconds=0), None)
        
        # Travel method DRIVE, BICYCLE, etc.
        travel_mode = self.travel_method.get() 
        # Minimization: 1 for Distance, 2 for Time
        using_time = (self.minimize_choice.get() == "2")
        
        # Starting time
        start_time_input = self.start_time_entry.get().strip()
        if start_time_input == "0":
            start_time = datetime.now()
        else:
            try:
                start_time = datetime.strptime(start_time_input + ":00", "%H:%M:%S").time()
                start_time = datetime.combine(datetime.today(), start_time)
            except ValueError:
                messagebox.showerror("Error", "Invalid start time. Use HH:MM")
                return
        
        try:
            distance_matrix = get_routes_data_as_distance_matrix(addresses, travel_mode)
            paths = get_paths(distance_matrix, addresses, using_time, same_ending, start_time)
            if not paths:
                messagebox.showinfo("Result", "No valid path found within the time constraints.")
                return
            (shortest_path, (travel_metric, arrival_time)) = find_shortest_path(paths)
            
            # Format travel metric
            if using_time:
                readable_metric = str(travel_metric)
            else:
                readable_metric = f"{travel_metric/1609.34:.2f} miles"
            
            # Build output message using original prompts
            message = f"Your path goes from {shortest_path[0]}"
            for addr in shortest_path[1:]:
                message += f" to {addr}"
            message += f"\nIt takes {readable_metric} to travel and ends at {arrival_time.strftime('%H:%M:%S')}"
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert(tk.END, message)
        # Print any exceptions that might come in this code
        except Exception as e:
            messagebox.showerror("Error", str(e))

# Start the program
if __name__ == "__main__":
    root = tk.Tk() 
    app = RoutePlannerGUI(root)
    root.mainloop()
